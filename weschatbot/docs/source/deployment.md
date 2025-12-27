# Deployment Guide

## Overview and Preparation

* **Goal:** Deploy the full chatbot stack (UI, management, workers, VLLM, Milvus, MySQL, Redis) on Docker with an
  internal network, sequential startup, DB migrations, and GPU-enabled inference where applicable.
* **Host requirements:** Docker Engine, Docker Compose for Milvus, NVIDIA Container Toolkit for GPU support, sufficient
  CPU, RAM, and disk for models and Milvus.
* **Predeployment checklist**
    * Place sensitive runtime variables in a `.env` file or orchestrator secrets; never commit `.env` to version
      control.
    * Verify NVIDIA drivers and nvidia-smi on the host when using GPUs.
    * Confirm required ports are free: 3000, 5000, 9292, 9290, 3306, 6379, 9090, 33060 or adjust firewall/ingress
      accordingly.
    * Ensure storage capacity for uploads, converted files, and model cache.

## Step 1 Build Images

### Build base image

```shell
cd base_image
docker build -t chatbot-base:0.0.3 .
cd ..

```

* **Purpose:** keep shared system dependencies and tooling layers in a base image to speed downstream builds.

### Build application image

```shell
docker build -t westaco-chatbot:0.0.3 .
```

* **Recommendation:** use semantic version tags, multi-stage builds, and push images to a private registry for
  multi-host deployments.

### Validate image

```shell
docker run --rm westaco-chatbot:0.0.3 weschatbot --help
```

* Confirm entrypoint/CLI works and the image contains required runtime files.

## Step 2 Create Network and Volumes

### Create Docker network

```shell
docker network create -d bridge westaco_chatbot
```

* Enables containers to resolve each other by name.

### Create persistent volumes

```shell
docker volume create weschatbot_uploads_volume
docker volume create weschatbot_models_volume
docker volume create weschatbot_converted_volume
docker volume create weschatbot_datalab_models_volume
```

### Verify volume permissions

* After containers mount volumes, confirm read/write permissions. If needed, adjust UID/GID in Dockerfile or run a
  `chown` step in the container entrypoint.

## Step 3 Infrastructure Services

### Start MySQL

```shell
docker run --network westaco_chatbot --name westaco-mysql \
  -p 3306:3306 -p 33060:33060 \
  -e MYSQL_ROOT_PASSWORD=Adcef#1234 \
  -d mysql:8.0.40-debian --default-authentication-plugin=mysql_native_password
```

* **Security note:** replace plaintext password with a secret; use a non-root DB user for applications.

### Wait for MySQL readiness

* Monitor logs with `docker logs -f westaco-mysql` or use a retry loop to test TCP connection and authentication.

### Create application database

```shell
docker exec -it westaco-mysql mysql -u root -pAdcef#1234 -e "create database chatbot;"
```

### Apply database migrations

```shell
docker run --rm --network westaco_chatbot \
  --name westaco-init-db \
  -e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://root:Adcef#1234@westaco-mysql:3306/chatbot \
  westaco-chatbot:0.0.3 \
  alembic upgrade head
```

* If migrations fail, inspect SQL errors, Alembic versions, or schema lock issues and re-run after fixes.

### Start Redis

```shell
docker run --network westaco_chatbot --name westaco-redis -d redis
```

* If using Redis authentication or ACLs, configure broker/backend URLs accordingly.

### Start Milvus

```shell
cd milvus
docker compose up -d
```

* Ensure Milvus containers are healthy and any containers needing Milvus are connected to the appropriate network.

## Step 4 Start Services in Recommended Order

Follow this order to ensure dependencies are ready: VLLM services → management → workers → UI.

### Start VLLM chat completions service

```shell
docker run -d --gpus all -p 9292:9292 --restart=always \
  --name westaco-chatbot-vllm --network westaco_chatbot --env-file .env \
  -v weschatbot_models_volume:/root/.cache/huggingface \
  westaco-chatbot:0.0.3 \
  python -m vllm.entrypoints.openai.api_server \
  --model AlphaGaO/Qwen3-14B-GPTQ \
  --max-model-len 5500 --gpu-memory-utilization 0.75 --port 9292
```

* Verify health endpoint or send a basic request to confirm the service is up.

### Start VLLM embedding service

```shell
docker run -d --gpus all -p 9290:9290 --restart=always \
  --name westaco-chatbot-vllm-embed --network westaco_chatbot --env-file .env \
  -v weschatbot_models_volume:/root/.cache/huggingface \
  westaco-chatbot:0.0.3 \
  python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-Embedding-0.6B --max-model-len 2048 \
  --gpu-memory-utilization 0.2 --task embed --port 9290 --tensor-parallel-size 1 --enforce-eager
```

* Adjust GPU memory utilization and tensor parallel settings according to host capacity.

### Start management service

```shell
docker run -d -p 9090:5000 --restart=always --name westaco-chatbot-management \
  --network westaco_chatbot --env-file .env \
  -e WESCHATBOT__CELERY__BROKER_URL=redis://westaco-redis:6379/2 \
  -e WESCHATBOT__CELERY__BACKEND_URL=redis://westaco-redis:6379/3 \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_converted_volume:/srv/weschatbot/converted \
  westaco-chatbot:0.0.3 \
  weschatbot management start bind=0.0.0.0:5000 timeout=120 workers=4
```

* Test internal endpoints before exposing publicly.

### Start Celery worker(s)

```shell
docker run -d --gpus all --restart=always --name westaco-chatbot-worker \
  --network westaco_chatbot --env-file .env \
  -e WESCHATBOT__CELERY__BROKER_URL=redis://westaco-redis:6379/2 \
  -e WESCHATBOT__CELERY__BACKEND_URL=redis://westaco-redis:6379/3 \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_converted_volume:/srv/weschatbot/converted \
  -v weschatbot_datalab_models_volume:/root/.cache/datalab/models/ \
  westaco-chatbot:0.0.3 \
  weschatbot worker start
```

* Check worker logs for successful Celery connection and task consumption.

### Start Chatbot UI (Gunicorn with UvicornWorker)

```shell
docker run -d -p 3000:3000 --gpus all --restart=always \
  --name westaco-chatbot-ui --network westaco_chatbot --env-file .env \
  -e WESCHATBOT__VLLM__BASE_URL=http://westaco-chatbot-vllm:9292 \
  -v weschatbot_uploads_volume:/srv/weschatbot/uploads \
  -v weschatbot_converted_volume:/srv/weschatbot/converted \
  -v weschatbot_models_volume:/root/.cache/huggingface \
  westaco-chatbot:0.0.3 \
  weschatbot chatbot start bind=0.0.0.0:3000 worker_class=uvicorn.workers.UvicornWorker workers=4
```

* Confirm Gunicorn uses an ASGI-capable worker class and that endpoints respond.

## Step 5 Post-Start Health Checks

* Tail container logs:

```shell
docker logs -f westaco-chatbot-ui
docker logs -f westaco-chatbot-worker
docker logs -f westaco-chatbot-management
docker logs -f westaco-chatbot-vllm
```

* Verify HTTP health endpoints:
  * UI health: `http://localhost:3000/health` or app-specific path.
  * Management: `http://localhost:9090/health`.
  * VLLM: `http://localhost:9292/health`.
* Validate Celery: check worker logs or run a simple test task and monitor consumption.
* Confirm Milvus indices and connectivity from the application.

## Operational Guidelines
* **Migrations:** always run Alembic migrations after MySQL is ready and before starting services depending on schema.
* **Secrets management:** inject credentials via orchestrator secrets when available; avoid plaintext in files.
* **Restart policy:** use `--restart=always` for production containers; on Kubernetes use Deployments with readiness/liveness probes.
* **Logging:** centralize logs with ELK, Loki, or another platform; avoid relying on container logs only.
* **Monitoring:** collect metrics for MySQL, Redis, Milvus, GPU memory, and service latency with Prometheus/Grafana.
* **Backups:** schedule MySQL dumps and Milvus/Redis backup policies according to RTO/RPO.
* **Scaling**:
  * Scale workers by running more worker containers or via orchestrator replicas.
  * Tune Gunicorn `workers` and `worker_class` for the UI and management services.
  * VLLM scaling requires careful GPU planning; consider model sizes and memory utilization per host.

## Security and Network Recommendations
* Use a reverse proxy (nginx or ingress) to terminate TLS and route traffic; do not expose MySQL, Redis, or Milvus directly to the internet. 
* Implement network segmentation so only necessary containers can access internal services. 
* Create a dedicated DB user with least privilege for the application. 
* Keep base images up-to-date to reduce security risks.

## Common Troubleshooting
* **MySQL not ready:** check `docker logs`, increase wait timeout, and use a retry loop for migrations. 
* **Migration failures:** inspect error messages, check for conflicting Alembic revisions, and retry after fixes. 
* **VLLM OOM:** lower `--gpu-memory-utilization`, reduce batch size, or use a smaller model. 
* **Worker cannot connect to Redis:** confirm network, run `docker network inspect`, and test connectivity with `docker exec ping`. 
* **Model path permission issues:** ensure volume mounts and file ownership are correct; consider `chown` in entrypoint. 
* **FastAPI ASGI error:** run Gunicorn with `worker_class=uvicorn.workers.UvicornWorker` to avoid WSGI/ASGI mismatch.

## Pre Go-Live Checklist
* [ ] Images are tagged and pushed to registry if deploying multi-host.
* [ ] `.env` or secrets are configured securely.
* [ ] Alembic migrations applied successfully.
* [ ] Healthchecks for all services return OK.
* [ ] Monitoring and logging are enabled and tested.
* [ ] Backup procedures defined for MySQL and Milvus.
* [ ] Rollback plan prepared with previous image tags.
* [ ] Basic load test performed to validate worker sizing and VLLM throughput.
