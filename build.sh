#!/usr/bin/env bash
# Render build script — runs on every deploy.
set -e

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_admin
python manage.py seed_store
