import json
from typing import List, Dict

import httpx
import requests
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
from weschatbot.schemas.chat import Message
from weschatbot.security.cookie_jwt_manager import FastAPICookieJwtManager
from weschatbot.security.exceptions import TokenInvalidError, TokenExpiredError
from weschatbot.services.ollama_client import OllamaClient
from weschatbot.services.session_service import SessionService, NotPermissionError
from weschatbot.services.user_service import UserService
from weschatbot.utils.config import config
from weschatbot.www.chatbot_ui.csrfsettings import CsrfSettings


class ConversationManager:
    """Manage conversation history for each of user and session"""

    def __init__(self):
        self.conversations = {}

    def get_conversation_history(self, user_id: int, chat_id: str) -> List[Dict[str, str]]:
        """Get conversation history of user and particular session"""
        if user_id not in self.conversations:
            self.conversations[user_id] = {}

        if chat_id not in self.conversations[user_id]:
            self.conversations[user_id][chat_id] = []

        return self.conversations[user_id][chat_id]

    def add_message(self, user_id: int, chat_id: str, role: str, content: str):
        """Add message to conversation history"""
        if user_id not in self.conversations:
            self.conversations[user_id] = {}

        if chat_id not in self.conversations[user_id]:
            self.conversations[user_id][chat_id] = []

        self.conversations[user_id][chat_id].append({
            "role": role,
            "content": content
        })

    def clear_conversation(self, user_id: int, chat_id: str):
        """Clear conversation history for particular session"""
        if user_id in self.conversations and chat_id in self.conversations[user_id]:
            self.conversations[user_id][chat_id] = []

    def delete_user_conversation(self, user_id: int, chat_id: str):
        """Clear conversation of user and session"""
        if user_id in self.conversations and chat_id in self.conversations[user_id]:
            del self.conversations[user_id][chat_id]


@CsrfProtect.load_config
def get_csrf_config(*args, **kwargs):
    return CsrfSettings()


app = FastAPI()
app.mount("/static", StaticFiles(directory="weschatbot/www/static"), name="static")
templates = Jinja2Templates(directory="weschatbot/www/templates")

# Connect Milvus
connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

KB_COLLECTION_NAME = "doc_v2"
kb_collection = Collection(KB_COLLECTION_NAME)
kb_collection.load()

# Initial embedding model
embedding_model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')

# Initial Ollama client and conversation manager
ollama_client = OllamaClient(
    base_url=f"http://{config['ollama']['host']}:{config['ollama']['port']}"
)
conversation_manager = ConversationManager()

# Model name from config or default
OLLAMA_MODEL = config['ollama']['model']

session_service = SessionService()
user_service = UserService()


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
    model = {
        "chat_id": None,
        "messages": None
    }
    user_id = int(payload["sub"])
    all_sessions = session_service.get_sessions(user_id)
    return templates.TemplateResponse(
        "chatbot_ui/index.html",
        {
            "model": json.dumps(model),
            "request": request,
            "sessions": json.dumps(all_sessions),
            "username": payload["username"],
        })


@app.get("/new_chat")
async def new_chat(payload: dict = Depends(jwt_manager.required)):
    chat_id, _ = session_service.create_session()
    url = app.url_path_for("get_chat", chat_id=chat_id)
    return RedirectResponse(url=url, status_code=302)


@app.get("/chats/{chat_id}")
async def get_chat(request: Request, chat_id: str, payload: dict = Depends(jwt_manager.required)):
    all_sessions = session_service.get_sessions(int(payload.get("sub")))
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
async def delete_chat(request: Request, chat_id: str, payload: dict = Depends(jwt_manager.required)):
    user_id = int(payload.get("sub"))
    try:
        session_service.delete_session(user_id=user_id, chat_id=chat_id)
        # Clear conversation history
        conversation_manager.delete_user_conversation(user_id, chat_id)
    except NotPermissionError as e:
        raise HTTPException(status_code=401, detail=e)


@app.post("/chats/{chat_id}/clear")
async def clear_chat_history(chat_id: str, payload: dict = Depends(jwt_manager.required)):
    """Clear conversation history for particular session"""
    user_id = int(payload.get("sub"))
    conversation_manager.clear_conversation(user_id, chat_id)
    return {"message": "Conversation history cleared"}


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

            if not context:
                await websocket.send_text(json.dumps({"text": "Information is not found"}))
                continue

            prompt = f"""
You are a helpful and knowledgeable chatbot. Your primary function is to answer user queries based on the provided context.
Core Instructions
    - Context-Based Answering: You must first attempt to answer the user's query using only the information in the provided context.
    - Language Adaptation: Your response language must match the language of the user's query. Prioritize English and Romanian, defaulting to Romanian if the language cannot be identified.
    - Knowledge Fallback: If the provided context does not contain the information required to answer the query, or if no context is provided, use your general knowledge to formulate a helpful and accurate response.
    - Persona: Maintain the persona of a friendly and helpful chatbot. Feel free to answer common, general knowledge questions as a typical chatbot would.

Constraints
    - Do not mention the context. The user should not be aware that you are referencing an external context.
    - Prioritize clarity and directness. Provide concise answers without unnecessary fluff.

Example of a good response:
    Query: "What is the capital of France?"
    Context: (No context provided)
    Response: "The capital of France is Paris."

Example of a bad response:
    Query: "What is the capital of France?"
    Context: (No context provided)
    Response: "Based on my internal knowledge, the capital of France is Paris." (Breaks the "Do not mention the context" rule).
---
Context:
{context}
---

Question:
{question}
---

Answer:
"""
            print(f"Prompt sent to Ollama:\n{prompt}")
            answer = "Error: Could not get answer from Ollama."
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{ollama_client.base_url}/api/generate",
                        json={
                            "model": OLLAMA_MODEL,
                            "prompt": prompt,
                            "stream": False  # Set to stream text response
                        },
                        timeout=120.0
                    )
                    response.raise_for_status()
                    ollama_response = response.json()
                    answer = ollama_response.get("response", "No response from Ollama model.")
                    answer = answer.split('</think>')[-1]
            except httpx.HTTPStatusError as e:
                answer = f"Ollama API HTTP error: {e.response.status_code} - {e.response.text}"
                print(f"Ollama API HTTP error: {e}")
            except httpx.RequestError as e:
                raise e
                answer = f"Ollama API network error: {e}"
                print(f"Ollama API network error: {e}")
            except Exception as e:
                answer = f"An unexpected error occurred with Ollama: {e}"
                print(f"Unexpected error with Ollama: {e}")

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


# Endpoint for test Ollama connection
@app.get("/health/ollama")
async def check_ollama_health():
    """Check connection with Ollama"""
    try:
        response = requests.get(f"{ollama_client.base_url}/api/tags", timeout=5)
        response.raise_for_status()
        return {"status": "healthy", "models": response.json()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# Endpoint for test Ollama connection
@app.get("/health/ollama")
async def check_ollama_health():
    """Check connection with Ollama"""
    try:
        response = requests.post(
            f"{ollama_client.base_url}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False  # Set to stream text response
            },
            timeout=120.0
        )
        response.raise_for_status()
        return {"status": "healthy", "models": response.json()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
