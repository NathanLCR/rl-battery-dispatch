# GréineQ Docker — Web Twin (FastAPI)

Publishes the **web app** (not Streamlit) at the same host URL / port you already use
(e.g. [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/)).

| Inside container | Host default | App |
|------------------|--------------|-----|
| **8000** | **8501** (`GREINEQ_PORT`) | FastAPI Web Twin |

Local dev without Docker still uses `run_web.ps1` → **8080**.

## Prerequisites

- Docker + Docker Compose
- On the host (not in git):
  - `data/merged_30min_v2.csv`
  - `data/day_split.json`
  - `results/models/` with **540 / 1620** `forecast_exp` Q-tables

## Publish (same URL as before)

From the **repository root** on the server:

```bash
git pull origin main

# Stop old Streamlit container if it is still running
docker compose -f Dockerfile/docker-compose.yml down

# Build and start Web Twin
docker compose -f Dockerfile/docker-compose.yml up -d --build
```

Open the same URL you used before (host port **8501** by default, or whatever nginx already proxies).

### With nginx on port 80

```bash
docker compose -f Dockerfile/docker-compose.yml --profile with-nginx up -d --build
```

## Check it is up

```bash
curl http://127.0.0.1:8501/api/health
# → {"ok":true,"service":"greineq-web"}
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `GREINEQ_PORT` | `8501` | Host port → container **8000** |
| `NGINX_HTTP_PORT` | `80` | nginx (with-nginx profile) |

## Volumes

| Host | Container | Purpose |
|------|-----------|---------|
| `data/` | `/app/data` | Merged CSV + day split (required) |
| `results/` | `/app/results` | Q-tables (required for Twin / Play) |
| `artifacts/` | `/app/artifacts` | Optional cache |

## Rebuild / stop

```bash
docker compose -f Dockerfile/docker-compose.yml down
docker compose -f Dockerfile/docker-compose.yml up -d --build
```
