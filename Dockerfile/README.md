# GréineQ Docker deployment

Container setup used to publish the live dashboard at [https://greineq-agent.sudocod.com/](https://greineq-agent.sudocod.com/).

## Prerequisites

- Docker and Docker Compose
- `data/merged_30min_v2.csv` and `data/day_split.json` on the host (not in git)
- Optional: trained Q-table files under `results/models/` for RL policy replay

## Quick start (Streamlit only)

From the repository root:

```bash
docker compose -f Dockerfile/docker-compose.yml up -d --build
```

Open [http://localhost:8501](http://localhost:8501).

## With nginx reverse proxy

```bash
docker compose -f Dockerfile/docker-compose.yml --profile with-nginx up -d --build
```

Streamlit listens on port 8501 inside the stack; nginx exposes port 80 (override with `NGINX_HTTP_PORT`).

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GREINEQ_PORT` | `8501` | Host port mapped to Streamlit |
| `NGINX_HTTP_PORT` | `80` | Host port for nginx (with-nginx profile) |

## Runtime volumes

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `data/` | `/app/data` | Merged CSV and day split (read-only) |
| `artifacts/` | `/app/artifacts` | Demo GIF cache |
| `results/` | `/app/results` | Trained Q-table models (read-only) |

## Stop and rebuild

```bash
docker compose -f Dockerfile/docker-compose.yml down
docker compose -f Dockerfile/docker-compose.yml up -d --build
```
