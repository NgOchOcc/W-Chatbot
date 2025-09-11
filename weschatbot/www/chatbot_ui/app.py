import json
from typing import List, Dict

from fastapi import Depends, Form, FastAPI, WebSocket, Request, Cookie, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from fastapi_csrf_protect import CsrfProtect
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.models.collection import ChatbotConfiguration
from weschatbot.schemas.chat import Message
from weschatbot.security.cookie_jwt_manager import FastAPICookieJwtManager
from weschatbot.security.exceptions import TokenInvalidError, TokenExpiredError
from weschatbot.services.chatbot_configuration_service import ChatbotConfigurationService
from weschatbot.services.ollama_service import VLLMClient
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
kb_collection = Collection(KB_COLLECTION_NAME)
kb_collection.load()

# Initial embedding model
embedding_model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')

# vLLM configuration
VLLM_MODEL = config['vllm']['model']
VLLM_BASE_URL = config['vllm']['base_url']

vllm_client = VLLMClient(
    base_url=VLLM_BASE_URL,
    model=VLLM_MODEL
)
session_service = SessionService()
user_service = UserService()

chatbot_configuration = chatbot_configuration_service.get_configuration()


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


# @app.post("/chats/{chat_id}/clear")
# async def clear_chat_history(chat_id: str, payload: dict = Depends(jwt_manager.required)):
#     """Clear conversation history for particular session"""
#     user_id = int(payload.get("sub"))
#     chat = session_service.get_session(chat_id)
#     chat.messages = []
#     session_service.store_chat(chat)
#     return {"message": "Conversation history cleared"}


# @app.get("/chats/{chat_id}/history")
# async def get_chat_history(chat_id: str, payload: dict = Depends(jwt_manager.required)):
#     """Get conversation history for debugging"""
#     user_id = int(payload.get("sub"))
#     chat = session_service.get_session(chat_id)
#
#     history = []
#     for msg in chat.messages:
#         if msg.sender == "user":
#             history.append({"role": "user", "content": msg.message})
#         elif msg.sender == "bot":
#             history.append({"role": "assistant", "content": msg.message})
#
#     return {"chat_id": chat_id, "history": history, "message_count": len(history)}


def get_conversation_history_from_chat(chat) -> List[Dict[str, str]]:
    """Convert chat messages to conversation history format for vLLM"""
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

            query_emb = embedding_model.encode([question])[0].tolist()

            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            results = kb_collection.search(
                data=[query_emb],
                anns_field="embedding",
                param=search_params,
                limit=5,
                expr=None,
                output_fields=["text"]
            )

            relevant_texts = [
                hit.entity.get('text') or ""
                for hits in results
                for hit in hits
            ]

            context = "\n".join(text for text in relevant_texts if text.strip() != "")

            # Get current chat and conversation history
            chat = session_service.get_session(chat_id)
            conversation_history = get_conversation_history_from_chat(chat)
            answer = "Error: Could not get answer from Ollama."

            try:
                answer = await vllm_client.chat_with_context(
                    question=question,
                    context=context,
                    conversation_history=conversation_history
                )

                answer = answer.split('</think>')[-1]

            except Exception as e:
                answer = f"An error occurred: {str(e)}"
                print(f"Error calling Ollama: {e}")

            res = {
                "text": f"{answer}"
            }

            # Create message objects and update session
            messages = [
                Message(sender="user", receiver="bot", message=question),
                Message(sender="bot", receiver="user", message=answer),
            ]

            session_service.update_session(user_id, chat_id, messages)
            await websocket.send_text(json.dumps(res))
    except WebSocketDisconnect:
        print("Client disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
