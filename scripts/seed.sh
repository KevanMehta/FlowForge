#!/usr/bin/env sh
set -e
docker compose exec backend python -m app.seed.seed
