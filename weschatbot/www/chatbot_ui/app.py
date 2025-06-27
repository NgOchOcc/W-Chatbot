import json

from fastapi import Depends, Form, FastAPI, WebSocket, Request, Cookie, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from fastapi_csrf_protect import CsrfProtect
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from transformers import set_seed

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.schemas.chat import Message
from weschatbot.security.cookie_jwt_manager import FastAPICookieJwtManager
from weschatbot.security.exceptions import TokenInvalidError, TokenExpiredError
from weschatbot.services.session_service import SessionService
from weschatbot.services.user_service import UserService
from weschatbot.utils.config import config
from weschatbot.www.chatbot_ui.csrfsettings import CsrfSettings


@CsrfProtect.load_config
def get_csrf_config(*args, **kwargs):
    return CsrfSettings()


app = FastAPI()
app.mount("/static", StaticFiles(directory="weschatbot/www/static"), name="static")
templates = Jinja2Templates(directory="weschatbot/www/templates")

connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

KB_COLLECTION_NAME = "enterprise_kb"
kb_collection = Collection(KB_COLLECTION_NAME)
kb_collection.load()

embedding_model = SentenceTransformer('all-mpnet-base-v2')

generator = pipeline('text-generation', model='gpt2')

# qa_pipeline = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad")
qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")

set_seed(42)

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


jwt_manager = FastAPICookieJwtManager(secret_key=config["jwt"]["secret_key"],
                                      security_algorithm=config["jwt"]["security_algorithm"])


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

            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = kb_collection.search(
                data=[query_emb],
                anns_field="embedding",
                param=search_params,
                limit=3,
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

            qa_input = {
                "question": question,
                "context": context
            }

            prompt = f"Milvus context:\n{context}\n\nQuestion: {question}. Only get answer in context.\nAnswer:"
            print(prompt)

            try:
                answer_result = qa_pipeline(qa_input)
                answer = answer_result.get("answer", "Answer is not found")
            except Exception as e:
                answer = f"Error: {str(e)}"

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
