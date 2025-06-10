import json

from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from transformers import set_seed

from weschatbot.utils.config import config

app = FastAPI()
app.mount("/static", StaticFiles(directory="weschatbot/www/static"), name="static")
templates = Jinja2Templates(directory="weschatbot/www/templates")

connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

KB_COLLECTION_NAME = "enterprise_kb"
kb_collection = Collection(KB_COLLECTION_NAME)
kb_collection.load()

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

generator = pipeline('text-generation', model='gpt2')

qa_pipeline = pipeline("question-answering", model="bert-large-uncased-whole-word-masking-finetuned-squad")

set_seed(42)


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("chatbot_ui/index.html", {
        "request": request,
        "title": "Westaco Chatbot",
        "message": "Welcome to Westaco Chatbot!"
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()

            question = data

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

            try:
                answer_result = qa_pipeline(qa_input)
                answer = answer_result.get("answer", "Answer is not found")
            except Exception as e:
                answer = f"Error: {str(e)}"

            res = {
                "text": f"{answer}"
            }

            await websocket.send_text(json.dumps(res))
    except WebSocketDisconnect:
        print("Client disconnected")
