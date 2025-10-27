# Configuration

## Overview

This document explains every configuration option from the provided config file, describes their purpose, gives
recommended values and safe defaults, shows how to override them in Docker environment variables, and lists operational
and security best practices. Use this guide to understand, validate, and tune the runtime behavior of the chatbot stack.

## How configuration is loaded and secrets strategy

* The application reads an INI-style config file with sections such as `[core]`, `[db]`, `[redis]`, etc.
* Environment variables should be used for runtime overrides and secrets injection; prefer orchestrator secrets or
  Docker/Kubernetes secret mechanisms rather than committing secrets into the config file.
* Common pattern to override config via environment variables is to use the same names in uppercase with section prefix,
  for example `WESCHATBOT__DB__SQL_ALCHEMY_CONN` to override `db.sql_alchemy_conn`. Confirm the application config
  loader mapping used in code and adapt variable names accordingly.
* Keep a minimal `.env` in development and never store production credentials in source control.

## Section by section reference

### core

* **upload_file_folder** - path where user file uploads are stored. Current value: `/srv/weschatbot/uploads`.
    * Recommendation: mount this path to a Docker volume `weschatbot_uploads_volume` and ensure the container user has
      read/write permission.
    * Note: do not expose raw upload folder via web server; serve files through the application with proper
      authentication.
* **converted_file_folder** - path to store converted documents (PDF → chunked text, embeddings output). Current value:
  `/srv/weschatbot/converted`.
    * Recommendation: mount to `weschatbot_converted_volume`. Clean up old converted files periodically if storage is
      limited.
* `milvus_collection_name` - name used for the Milvus collection storing document vectors. Current: `westaco_documents`.
    * Recommendation: use a stable name per environment, e.g., `westaco_documents_prod` vs `westaco_documents_staging`.
      Changing the name resets index visibility to the app.

### logging

* **level** - logging level. Current: `INFO`.
    * Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
    * Recommendation: use INFO in production, enable DEBUG for troubleshooting. Avoid DEBUG in production due to
      sensitive data in logs.
* **format** - log format string. Current format includes timestamp with ms, filename, line number, logger name, level,
  and message.
    * Recommendation: keep structured logging for easier parsing. Consider JSON logging in production to integrate with
      ELK/Loki.

### management

* **flask_secret_key** - secret key used by management UI (Flask sessions or signing). Current placeholder: `xxx`.
    * Recommendation: set a strong secret via environment secret manager. Rotate if leaked.

### db

* **sql_alchemy_conn** - synchronous SQLAlchemy connection URI. Current:
  `mysql://root:Adcef#1234@127.0.0.1:3306/chatbot`.
    * Recommendation: use a dedicated DB user with least privilege; do not use root in production. Example:
      `mysql+pymysql://appuser:strongpass@westaco-mysql:3306/chatbot`.
* **async_sql_alchemy_conn** - async connection URI used by async components. Current:
  `mysql+aiomysql://root:Adcef#1234@127.0.0.1:3306/chatbot`.
    * Recommendation: ensure async driver package aiomysql is installed and URI scheme matches driver.
* **echo** - SQLAlchemy SQL echo flag. Current: `false`.
    * Recommendation: `false` in production; `true` temporarily for debugging queries.
* **pool_size** - size of DB connection pool. Current: `10`.
    * Recommendation: tune based on app concurrency, workers, and available DB connections. In containerized
      multi-replica deployments, account for total DB connections across replicas.
* **max_overflow** - additional connections allowed beyond pool_size. Current: `20`.
* **pool_timeout** - seconds to wait for a connection from pool. Current: `30`.
* **pool_recycle** - recycle connections older than this many seconds. Current: `1800`.
    * Recommendation: prevents stale connections with some managed DBs.
* **pool_pre_ping** - boolean to enable pre-ping health check on connections. Current: `true`.
    * Recommendation: keep `true` to avoid returning broken connections.
* **isolation_level** - transaction isolation level. Current: `READ COMMITTED`.
    * Recommendation: keep default unless specific transactional semantics are required.

### jwt

* **secret_key** - key used to sign JWTs. Current placeholder: `xxx`.
    * Recommendation: provide a long random secret via secret manager. Rotate periodically if required.
* **security_algorithm** - signing algorithm. Current: `HS256`.
    * Recommendation: `HS256` is common for symmetric secrets. For asymmetric signing use `RS256` with private/public
      key pair.

### milvus

* **host** - Milvus host. Current: `localhost`.
* **port** - Milvus port. Current: `19530`.
    * Recommendation: in container environment set host to Milvus container name, e.g., `milvus` or `milvus-standalone`.
      Ensure network connectivity and firewall rules allow this port.

### redis

* **host** - Redis host. Current: `localhost`.
* **port** - Redis port. Current: `6379`.
    * Recommendation: use container name `westaco-redis` in Docker network or a managed Redis endpoint. If enabling
      authentication, update broker URLs and use ACLs.

### celery

* **app_name** - Celery application name. Current: `weschatbot`.
* **broker_url** - Celery broker. Current: `redis://localhost:6379/0`.
    * Recommendation: set broker to `redis://westaco-redis:6379/2` to match production Docker network example; use
      dedicated DB indices for broker and backend.
* **backend_url** - result backend. Current: `redis://localhost:6379/1`.
* **worker_concurrency** - concurrency per worker process. Current: `1`.
    * Recommendation: tune according to CPU/GPU and task type. For I/O heavy tasks increase concurrency, for CPU/GPU
      heavy tasks keep concurrency low.
* **worker_pool** - pool type. Current: `threads`.
    * Options: `prefork`, `threads`, `solo`. Choose `threads` for light-weight tasks that release GIL or `prefork` for
      CPU isolation.
* **worker_log_level** - logging level. Current: `INFO`.
* **task_queues** - queue names used by Celery. Current: `convert,index`.
    * Recommendation: define separate queues for heavy tasks (embed, convert) and assign dedicated workers.

### ollama

* **port** - Ollama server port. Current: `11434`.
* **host** - Ollama host. Current: `localhost`.
* **model** - name of model served by Ollama. Current: `qwen3:14b`.
    * Recommendation: set to actual Ollama endpoint or disable section if not used.

### vllm

* **model** - model identifier. Current: `AlphaGaO/Qwen3-14B-GPTQ`.
    * Recommendation: ensure model files or accessible model registry and GPU resources are compatible.
* **base_url** - vLLM server base URL. Current: `http://westaco-chatbot-vllm:9292`.
    * Recommendation: point to vllm container service name used in Docker network.

### embedding_model

* **model** - model identifier used for embedding. Current: `Qwen/Qwen3-Embedding-0.6B`.
* **vllm_model** - model used by vLLM for embedding. Current: `Qwen/Qwen3-Embedding-0.6B`.
* **vllm_embedding_url** - embedding endpoint URL. Current: `http://westaco-chatbot-vllm-embed:9290`.
* **mode** - vllm indicates embedding is produced using vLLM endpoint.
    * Recommendation: verify embedding API contract and vector sizes to match Milvus index metric and schema.

### retrieval

* **metrics** - similarity metric for retrieval. Current: `COSINE`.
    * Options: `COSINE`, `L2`, `IP`. Choose based on embedding normalization and Milvus index type.
* **search_limit** - number of top results returned per query. Current: `5`.
    * Recommendation: tune between latency and recall; typical values are **3–10**.

## Environment variable mapping examples

* Use the environment variable naming convention used in your deployment scripts. Example mappings used in Docker run
  commands:
    * `WESCHATBOT__DB__SQL_ALCHEMY_CONN` => `db.sql_alchemy_conn`
    * `WESCHATBOT__REDIS__HOST` => `redis.host`
    * `WESCHATBOT__VLLM__BASE_URL` => `vllm.base_url`
    * `WESCHATBOT__CELERY__BROKER_URL` => `celery.broker_url`
* Example Docker run snippet showing overrides:
    * `-e WESCHATBOT__DB__SQL_ALCHEMY_CONN=mysql://appuser:pass@westaco-mysql:3306/chatbot`
    * `-e WESCHATBOT__REDIS__HOST=westaco-redis`
    * `-e WESCHATBOT__JWT__SECRET_KEY=<secure-secret>`
    * `--env-file .env` to bulk load environment variables from a local file that is not committed.

## Security and hardening recommendations

* Never store secrets in plaintext in repo. Use orchestrator secrets, Docker secrets, or HashiCorp Vault.
* Replace root DB usage with a limited user. Use least privilege principle.
* Use strong secrets for flask_secret_key and jwt.secret_key. Rotate secrets periodically.
* Limit exposed ports on hosts. Use a reverse proxy with TLS termination for public endpoints.
* Enable authentication or network restrictions on Milvus if accessible beyond internal network.
* Ensure images are scanned and base images are up-to-date to mitigate CVEs.

## Operational tips and tuning

* DB connection tuning
    * Calculate max DB connections as `pool_size` + `max_overflow` per application instance; aggregate across replicas
      to avoid exceeding MySQL max_connections.
    * Use `pool_pre_ping = true` to reduce stale connection errors.
* Celery scaling
    * Separate queues for CPU/GPU heavy tasks and run dedicated workers with appropriate concurrency and pool.
    * Use different Redis DB indices for broker and backend to avoid interference.
* Milvus and embeddings
    * Match `retrieval.metrics` to the embedding type. Normalize embeddings when using COSINE metric.
    * Monitor Milvus memory and storage; plan compaction and index rebuilds during maintenance windows.
* vLLM and GPU usage
    * Tune `gpu-memory-utilization` in vLLM service to avoid OOM. Spread model replicas across hosts if needed.
    * Keep a smaller model as fallback for low-latency responses.
* File storage
    * Periodically purge old uploads and converted files or implement lifecycle policies.
    * Ensure backup strategy for important converted artifacts if required.

## Example modifications for production

* Replace local hosts with container names or service discovery endpoints:
    * `db.sql_alchemy_conn = mysql://appuser:strongpass@westaco-mysql:3306/chatbot`
    * `redis.host = westaco-redis`
    * `milvus.host = milvus`
    * `vllm.base_url = http://westaco-chatbot-vllm:9292`
* Use dedicated Redis DB indices for Celery:
    * `celery.broker_url = redis://westaco-redis:6379/2`
    * `celery.backend_url = redis://westaco-redis:6379/3`
* Increase worker sizing for production loads:
    * `celery.worker_concurrency = 4` for moderate parallel tasks, adjust down for GPU-bound tasks.

## Troubleshooting checklist for configuration related issues

* Application cannot connect to MySQL
    * Verify host and port in sql_alchemy_conn. Test with mysql client from another container. Check MySQL logs.
* Celery cannot connect to broker
    * Verify celery.broker_url host and DB index. Confirm westaco-redis is reachable on Docker network.
* Embeddings mismatch or retrieval poor quality
    * Confirm embedding model and Milvus metric match. Verify embedding vector dimension and normalization.
* Files not accessible or permission errors
    * Check volume mounts and container user UID/GID. Run chown in entrypoint if necessary.
* JWT or session failures
    * Ensure jwt.secret_key and flask_secret_key are present and identical across stateless replicas if required.

## Final checklist before deployment

* [ ] Replace placeholder secrets with managed secrets.
* [ ] Use non-root DB user and verify DB permissions.
* [ ] Verify all hostnames in config match container names or service discovery.
* [ ] Mount volumes and validate read/write permissions.
* [ ] Run alembic upgrade head after DB readiness.
* [ ] Validate vLLM and embedding endpoints respond with expected schema.
* [ ] Configure monitoring and logs for each component.