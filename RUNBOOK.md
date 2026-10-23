# Production Reliability Runbook: All-in-One AI Assistant

**Target Scale:** 6,000 registered users, 600 peak concurrent chats (headroom to 1,000).  
**Architecture:** Nginx $\to$ Streamlit (Frontend) + FastAPI (Stateless API Backend) $\to$ PostgreSQL 16 + Redis 7.

---

## 1. Quick Deploy & Startup

### Local / Single-Server Deployment (Docker Compose)
```bash
# 1. Configure environment keys
cp .env.example .env
# Edit .env with your provider keys (GEMINI_API_KEYS, GROQ_API_KEYS, etc.)

# 2. Build and launch all services in detached mode
docker compose up -d --build

# 3. Verify health checks
curl -f http://localhost/health/ready
```

### Apply Database Migrations (Alembic)
```bash
# Run latest schema migrations
docker compose exec api alembic upgrade head
```

---

## 2. Horizontal Scaling

### Scale Backend API Instances
The FastAPI backend is 100% stateless; scale replicas dynamically behind the Nginx load balancer:
```bash
docker compose up -d --scale api=4 --no-recreate
```

### Scale Streamlit Frontend
Streamlit requires sticky sessions (`ip_hash` in `nginx.conf`) to preserve WebSocket connections:
```bash
docker compose up -d --scale web=3 --no-recreate
```

---

## 3. Incident Response & Troubleshooting

### Scenario A: AI Provider Outage / 429 Quota Exhaustion
* **Symptom:** Logs show `[CIRCUIT BREAKER] Circuit tripped to OPEN` or `429 RateLimit`.
* **Automatic Mitigation:**
  1. Circuit breaker trips to `OPEN` for 45s, immediately routing traffic to next fallback (Gemini $\to$ Groq $\to$ OpenAI $\to$ Ollama).
  2. If using multi-key rotation, the rate-limited key is isolated into 60s cooldown while other keys serve traffic.
* **Operator Action:**
  - Add fresh keys to `GEMINI_API_KEYS` in `.env` (comma-separated).
  - Reload environment without downtime: `docker compose up -d api`.

### Scenario B: Request Queue or Latency Spikes (p95 > 3s)
* **Check Active Connections:**
  ```bash
  docker compose exec redis redis-cli info clients
  docker compose exec postgres psql -U postgres -d chatbot_db -c "SELECT count(*) FROM pg_stat_activity;"
  ```
* **Mitigation:**
  1. Increase backend worker replicas: `docker compose up -d --scale api=6`.
  2. Verify if heavy tools (code execution / EDA) are saturating CPU; inspect sandbox logs.

### Scenario C: High Memory / OOM Protection
* **Check Memory Usage:**
  ```bash
  docker stats --no-stream
  ```
* **Mitigation:**
  - Python code execution runs in an isolated subprocess with a 6-second hard timeout.
  - Large file uploads are capped at 25MB (`MAX_UPLOAD_SIZE_MB=25`).
  - Clear temporary artifacts:
    ```bash
    find ./outputs ./artifacts -type f -mtime +1 -delete
    ```

---

## 4. Zero-Downtime Rollback Procedure

If a deployed revision introduces regressions:
```bash
# 1. Revert to previous git commit tag
git checkout <previous-stable-tag>

# 2. Roll back database migration if necessary
docker compose exec api alembic downgrade -1

# 3. Rebuild and restart API containers with zero dropped requests
docker compose up -d --build --no-deps api
```

---

## 5. Automated Health & Monitoring Endpoints

| Endpoint | Target | Expected Status |
| :--- | :--- | :--- |
| `GET /health/live` | Process Liveness | `200 OK {"status": "alive"}` |
| `GET /health/ready` | DB, Redis, and Provider Readiness | `200 OK {"status": "healthy"}` |
| `GET /docs` | OpenAPI Documentation | Swagger UI |
