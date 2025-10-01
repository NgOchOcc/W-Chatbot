import json
from typing import List, Dict, Optional, Union
from enum import Enum
from dataclasses import dataclass
import asyncio

from fastapi import Depends, Form, FastAPI, WebSocket, Request, Cookie, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from fastapi_csrf_protect import CsrfProtect
from pymilvus import Collection, connections

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.schemas.chat import Message
from weschatbot.security.cookie_jwt_manager import FastAPICookieJwtManager
from weschatbot.security.exceptions import TokenInvalidError, TokenExpiredError
from weschatbot.services.chatbot_configuration_service import ChatbotConfigurationService
from weschatbot.schemas.embedding import  RetrievalConfig
from weschatbot.services.vllm_llm_service import VLLMService
from weschatbot.services.session_service import SessionService, NotPermissionError
from weschatbot.services.user_service import UserService
from weschatbot.utils.config import config
from weschatbot.www.chatbot_ui.csrfsettings import CsrfSettings



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
OLLAMA_BASE_URL = config['embedding_model']['base_url']
OLLAMA_EMBEDDING_MODEL = config['embedding_model']['ollama_model']
VLLM_MODEL = config['vllm']['model']
VLLM_BASE_URL = config['vllm']['base_url']


retrieval_config = RetrievalConfig(
    collection_name=KB_COLLECTION_NAME,
    milvus_host=config["milvus"]["host"],
    milvus_port=int(config["milvus"]["port"]),
    embedding_mode=EMBEDDING_MODE,
    embedding_model=EMBEDDING_MODEL,
    ollama_base_url=OLLAMA_BASE_URL,
    search_limit=config['retrieval']['search_limit'],
    metric_type=config['retrieval']['metric_type']
)

vllm_client = VLLMService(
    base_url=VLLM_BASE_URL,
    model=VLLM_MODEL
)

session_service = SessionService()
user_service = UserService()
chatbot_configuration = chatbot_configuration_service.get_configuration()
chatbot_pipeline = ChatbotPipeline(
    retrieval_config=retrieval_config,
    vllm_client=vllm_client,
    chatbot_config=chatbot_configuration
)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except TokenInvalidError:
        return RedirectResponse(app.url_path_for("login_get"), 302)
    except TokenExpiredError:
        return RedirectResponse(app.url_path_for("login_get"), 302)
    except Exception:
        return JSONResponse(
            {"detail": "Internal server error"},
            status_code=500,
        )


jwt_manager = FastAPICookieJwtManager(
    secret_key=config["jwt"]["secret_key"],
    security_algorithm=config["jwt"]["security_algorithm"]
)


def return_login_form(request: Request, csrf: CsrfProtect, error=None):
    token, _ = csrf.generate_csrf_tokens()
    resp = templates.TemplateResponse(
        "chatbot_ui/login.html",
        {"request": request, "csrf_token": token, "error": error},
    )
    csrf.set_csrf_cookie(token, resp)
    return resp


@app.get("/logout")
def logout(payload: dict = Depends(jwt_manager.required)):
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
        token = jwt_manager.create_access_token(exp_in_seconds=24 * 3600, payload=payload)
        url = app.url_path_for("get")
        response = RedirectResponse(url=url, status_code=302)
        jwt_manager.set_token_cookie(token=token, response=response)
        return response
    except InvalidUserError as e:
        return return_login_form(request, csrf, str(e))


@app.get("/")
async def get(request: Request, payload: dict = Depends(jwt_manager.required)):
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
        raise HTTPException(status_code=401, detail=str(e))


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
    try:
        while True:
            data = await websocket.receive_text()

            question = json.loads(data)["message"]
            chat_id = json.loads(data)["chat_id"]

            # Get current chat and conversation history
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

            except Exception as e:
                answer = f"An error occurred: {str(e)}"
                print(f"Error calling chatbot pipeline: {e}")

            res = {
                "text": f"{answer}"
            }

            messages = [
                Message(sender="user", receiver="bot", message=question),
                Message(sender="bot", receiver="user", message=answer),
            ]

            session_service.update_session(user_id, chat_id, messages)
            await websocket.send_text(json.dumps(res))
    except WebSocketDisconnect:
        print("Client disconnected")
