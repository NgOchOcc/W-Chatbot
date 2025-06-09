import json
from time import sleep

from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect
from pymilvus import Collection, connections
from sentence_transformers import SentenceTransformer
from transformers import pipeline, set_seed

app = FastAPI()
app.mount("/static", StaticFiles(directory="weschatbot/www/static"), name="static")
templates = Jinja2Templates(directory="weschatbot/www/templates")

connections.connect("default", host="localhost", port="19530")

KB_COLLECTION_NAME = "enterprise_kb"
kb_collection = Collection(KB_COLLECTION_NAME)
kb_collection.load()

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

generator = pipeline('text-generation', model='gpt2')
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

            context = "\n".join(relevant_texts)
            prompt = f"Milvus context:\n{context}\n\nQuestion: {question}. Only get answer in context.\nAnswer:"

            generated = generator(prompt, max_length=150, num_return_sequences=1)
            answer = generated[0]['generated_text'][len(prompt):].strip()

            res = {
                "text": f"{answer}"
            }

            await websocket.send_text(json.dumps(res))
    except WebSocketDisconnect:
        print("Client disconnected")
