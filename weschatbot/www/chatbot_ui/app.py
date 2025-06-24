import json
import uuid

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from transformers import set_seed

from weschatbot.schemas.chat import Message
from weschatbot.services.session_service import SessionService
from weschatbot.utils.config import config

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

mock_chats = {
    "1": [
        {"sender": "user", "text": "Xin chào!"},
        {"sender": "bot", "text": "Chào bạn, tôi có thể giúp gì?"},
        {"sender": "user", "text": "Hôm nay thời tiết thế nào nhỉ?"},
        {"sender": "bot", "text": "Nắng đẹp và hơi nóng nhé 😄"},
    ]
}

session_service = SessionService()


@app.get("/")
async def get(request: Request):
    model = {
        "chat_id": None,
        "messages": None
    }
    all_sessions = session_service.get_sessions()
    return templates.TemplateResponse(
        "chatbot_ui/index.html",
        {
            "model": json.dumps(model),
            "request": request,
            "sessions": json.dumps(all_sessions),
        })


@app.get("/new_chat")
async def new_chat():
    chat_id, _ = session_service.create_session()
    url = app.url_path_for("get_chat", chat_id=chat_id)
    return RedirectResponse(url=url, status_code=302)


@app.get("/chats/{chat_id}")
async def get_chat(request: Request, chat_id: str):
    chat = session_service.get_session(chat_id)
    model = chat.to_dict()
    all_sessions = session_service.get_sessions()
    return templates.TemplateResponse(
        "chatbot_ui/index.html",
        {
            "model": json.dumps(model),
            "request": request,
            "sessions": json.dumps(all_sessions),
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
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

            session_service.update_session(chat_id, messages)

            await websocket.send_text(json.dumps(res))
    except WebSocketDisconnect:
        print("Client disconnected")
