# ### Build base image
# cd base_image
# docker build -t chatbot-base:0.0.1 .
# cd ..

# ### Build application image
# docker build -t westaco-chatbot:0.0.1 .

# #### Network
# docker network create -d bridge westaco_chatbot

# #### Start mysql
# docker run --platform linux/amd64 --network westaco_chatbot \
#   --name local-mysql \
#   -p 3306:3306 -p 33060:33060 \
#   -e MYSQL_ROOT_PASSWORD=Adcef#1234 \
#   -d mysql:8.0.40 \
#   --default-authentication-plugin=mysql_native_password


# #### Start milvus
# cd milvus
# docker compose up -d
# cd ..


### Ollama local Inference
docker run -d --name ollama \
  --network westaco_chatbot \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  ollama/ollama

docker exec ollama ollama pull llama3.2:1b


#### Start application
docker run -d -p 8000:8000 \
  --restart=always \
  --name westaco-chatbot-ui-v2 \
  --network westaco_chatbot \
  --env-file .env \
  --network milvus \
  westaco-chatbot:0.0.1 \
  weschatbot chatbot start