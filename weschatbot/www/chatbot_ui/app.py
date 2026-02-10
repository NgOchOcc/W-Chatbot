import json
import logging
from typing import List, Dict

from fastapi import Depends, Form, FastAPI, WebSocket, Request, Cookie, status, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from fastapi_csrf_protect import CsrfProtect
from pymilvus import connections

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.schemas.chat import Message
from weschatbot.schemas.embedding import RetrievalConfig
from weschatbot.security.cookie_jwt_manager import FastAPICookieJwtManager
from weschatbot.security.exceptions import TokenInvalidError, TokenExpiredError
from weschatbot.services.active_status_service import ActiveStatusService
from weschatbot.services.chatbot_configuration_service import ChatbotConfigurationService
from weschatbot.services.chatbot_pipelines.ambiguity_handling_pipeline import ChatbotAmbiguityHandlingPipeline
from weschatbot.services.chatbot_pipelines.base_pipeline import ChatbotPipeline
from weschatbot.services.query_service import make_query_result, QueryService
from weschatbot.services.session_service import SessionService, NotPermissionError
from weschatbot.services.token_service import TokenService
from weschatbot.services.user_service import BcryptUserService
from weschatbot.services.vllm_llm_service import VLLMService
from weschatbot.utils.config import config
from weschatbot.utils.limiter import limiter
from weschatbot.utils.redis_config import redis_client
from weschatbot.www.chatbot_ui.csrfsettings import CsrfSettings

logger = logging.getLogger(__name__)


@CsrfProtect.load_config
def get_csrf_config(*args, **kwargs):
    return CsrfSettings()


app = FastAPI()
app.mount("/static", StaticFiles(directory="weschatbot/www/static"), name="static")
templates = Jinja2Templates(directory="weschatbot/www/templates")

# Connect Milvus
connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))
chatbot_configuration_service = ChatbotConfigurationService()

KB_COLLECTION_NAME = chatbot_configuration_service.get_collection_name()
EMBEDDING_MODE = config['embedding_model']['mode']
EMBEDDING_MODEL = config['embedding_model']['model']
VLLM_MODEL = config['vllm']['model']
VLLM_BASE_URL = config['vllm']['base_url']
VLLM_EMBEDDING_URL = config['embedding_model']['vllm_embedding_url']

retrieval_config = RetrievalConfig(
    collection_name=KB_COLLECTION_NAME,
    milvus_host=config["milvus"]["host"],
    milvus_port=int(config["milvus"]["port"]),
    embedding_mode=EMBEDDING_MODE,
    embedding_model=EMBEDDING_MODEL,
    vllm_base_url=VLLM_EMBEDDING_URL,
    search_limit=int(config['retrieval']['search_limit']),
    metric_type=config['retrieval']['metrics'],
    enable_hybrid_search=config['retrieval'].getboolean('enable_hybrid_search', fallback=True),
    vector_weight=float(config['retrieval'].get('vector_weight', fallback=0.5)),
    text_weight=float(config['retrieval'].get('text_weight', fallback=0.5))
)

vllm_client = VLLMService(
    base_url=VLLM_BASE_URL,
    model=VLLM_MODEL
)

session_service = SessionService()
user_service = BcryptUserService()
token_service = TokenService()

query_service = QueryService()

chatbot_configuration = chatbot_configuration_service.get_configuration()

enable_ambiguity = config["retrieval"]["enable_ambiguity"]

if enable_ambiguity:
    chatbot_pipeline = ChatbotAmbiguityHandlingPipeline(
        retrieval_config=retrieval_config,
        vllm_client=vllm_client,
        chatbot_config=chatbot_configuration
    )
else:
    chatbot_pipeline = ChatbotPipeline(
        retrieval_config=retrieval_config,
        vllm_client=vllm_client,
        chatbot_config=chatbot_configuration
    )


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except TokenInvalidError as e:
        logger.warning(e)
        return RedirectResponse(app.url_path_for("login_get"), 302)
    except TokenExpiredError as e:
        logger.warning(e)
        return RedirectResponse(app.url_path_for("login_get"), 302)
    except Exception as e:
        logger.exception(e)
        return JSONResponse(
            {"detail": "Internal server error"},
            status_code=500,
        )


jwt_manager = FastAPICookieJwtManager(
    secret_key=config["jwt"]["secret_key"],
    security_algorithm=config["jwt"]["security_algorithm"]
)


@app.exception_handler(TokenExpiredError)
async def token_expired_exception_handler(request: Request, exc: TokenExpiredError):
    login_url = app.url_path_for("login_get")
    return RedirectResponse(url=login_url, status_code=302)


@app.exception_handler(TokenInvalidError)
async def token_invalid_exception_handler(request: Request, exc: TokenInvalidError):
    login_url = app.url_path_for("login_get")
    return RedirectResponse(url=login_url, status_code=302)


def return_login_form(request: Request, csrf: CsrfProtect, error=None):
    token, _ = csrf.generate_csrf_tokens()
    resp = templates.TemplateResponse(
        "chatbot_ui/login.html",
        {"request": request, "csrf_token": token, "error": error},
    )
    csrf.set_csrf_cookie(token, resp)
    return resp


@app.get("/logout")
def logout():
    response = RedirectResponse(url=app.url_path_for("login_get"), status_code=303)
    jwt_manager.delete_token_cookie(response)
    return response


@app.get("/login")
def login_get(request: Request, csrf: CsrfProtect = Depends()):
    return return_login_form(request, csrf)


@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), csrf: CsrfProtect = Depends()):
    try:
        user = user_service.login_user(username, password)
        if user is None:
            raise InvalidUserError("username/password incorrect")
        payload = {
            "sub": str(user.id),
            "username": user.name
        }
        token = jwt_manager.create_access_token(exp_in_seconds=int(config["jwt"]["access_token_expires_in_seconds"]),
                                                payload=payload)
        refresh_token = jwt_manager.create_refresh_token(
            exp_in_seconds=int(config["jwt"]["refresh_token_expires_in_seconds"]), payload=payload)
        url = app.url_path_for("get")
        response = RedirectResponse(url=url, status_code=302)
        jwt_manager.set_token_cookie(token=token, response=response, refresh_token=refresh_token)
        refresh_token_expires_date = jwt_manager.get_exp(refresh_token)

        token_service.create_refresh_token_record(
            request=request,
            user=user,
            refresh_token=refresh_token,
            expires_at=refresh_token_expires_date
        )

        return response
    except InvalidUserError as e:
        logger.warning(e)
        return return_login_form(request, csrf, str(e))
    except Exception as e:
        logger.exception(e)
        return return_login_form(request, csrf, str(e))


@app.get("/")
async def get(request: Request, response: Response, payload: dict = Depends(jwt_manager.required)):
    url = app.url_path_for("new_chat")
    return RedirectResponse(url, status_code=302)


@app.get("/new_chat")
async def new_chat(payload: dict = Depends(jwt_manager.required)):
    chat_id, _ = session_service.create_session()
    url = app.url_path_for("get_chat", chat_id=chat_id)
    return RedirectResponse(url=url, status_code=302)


@app.get("/chats/{chat_id}")
async def get_chat(request: Request, chat_id: str, payload: dict = Depends(jwt_manager.required)):
    user_id = int(payload.get("sub"))
    all_sessions = session_service.get_sessions(user_id)
    valid_sessions = [x["uuid"] for x in all_sessions]
    if chat_id not in valid_sessions:
        chat = session_service.get_session(chat_id)
        if not chat or chat.in_db:
            return RedirectResponse(app.url_path_for("new_chat"), 302)
    chat = session_service.get_session(chat_id)
    model = chat.to_dict()

    return templates.TemplateResponse(
        "chatbot_ui/index.html",
        {
            "model": json.dumps(model),
            "request": request,
            "sessions": json.dumps(all_sessions),
            "username": payload["username"],
        }
    )


@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, payload: dict = Depends(jwt_manager.required)):
    user_id = int(payload.get("sub"))
    try:
        session_service.delete_session(user_id=user_id, chat_id=chat_id)
    except NotPermissionError as e:
        logger.warning(e)
        raise HTTPException(status_code=401, detail="Not enough permission")


def get_conversation_history_from_chat(chat) -> List[Dict[str, str]]:
    history = []
    for msg in chat.messages:
        if msg.sender == "user":
            history.append({"role": "user", "content": msg.message})
        elif msg.sender == "bot":
            history.append({"role": "assistant", "content": msg.message})
    return history


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             jwt_access_token: str | None = Cookie(default=None, alias="jwt_access_token")):
    if not jwt_access_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt_manager.verify_access_token(jwt_access_token)
        user_id = int(payload.get("sub"))
    except TokenExpiredError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except TokenInvalidError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    websocket.state.user = payload.get("sub")

    rd_client = redis_client(0)
    presence = ActiveStatusService(redis_client=rd_client)

    try:
        while True:
            data = await websocket.receive_text()

            limit_interval = chatbot_configuration.limit_interval_seconds
            limit = chatbot_configuration.limit

            async def limit_failing_callback():
                await websocket.send_text(json.dumps({
                    "text": f"You have reached the limitation {limit} questions/{limit_interval / 60} minute(s)."
                }))

            @limiter(user_id=user_id, interval=limit_interval, limit=limit, failing_callback=limit_failing_callback)
            @presence.active(user_id=user_id)
            async def process_message():
                question = json.loads(data)["message"]
                chat_id = json.loads(data)["chat_id"]

                chat = session_service.get_session(chat_id)
                conversation_history = get_conversation_history_from_chat(chat)

                answer = "Error: Could not get answer from chatbot."

                try:
                    result = await chatbot_pipeline.run(
                        query=question,
                        conversation_history=conversation_history,
                        filter_expr=None
                    )
                    answer = result["response"]

                    messages = [
                        Message(sender="user", receiver="bot", message=question),
                        Message(sender="bot", receiver="user", message=answer),
                    ]

                    inserted_message_id = [x[0] for x in filter(lambda x: x[1] == "user",
                                                                session_service.update_session(user_id, chat_id,
                                                                                               messages))]
                    if len(inserted_message_id) > 0:
                        message_id = inserted_message_id[-1]
                        collection_id = chatbot_configuration.collection_id
                        retrieved_docs = list(map(lambda x: make_query_result(*x, collection_id=collection_id),
                                                  enumerate(result["retrieved_docs"])))
                        query_service.add_query_result_for_message(list_query_results=retrieved_docs,
                                                                   message_id=message_id)

                except Exception as e:
                    answer = "An error occurred. Please try again!"
                    logger.exception(f"Error calling chatbot pipeline: {e}")

                res = {
                    "text": f"{answer}"
                }

                await websocket.send_text(json.dumps(res))

            await process_message()

    except WebSocketDisconnect:
        logger.info("Client disconnected")
