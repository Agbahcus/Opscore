# Northflank Deployment Guide

## Overview
This project is a Django app with a Dockerfile configured for Northflank.
It uses `gunicorn` and `whitenoise` to serve app and static files.

## Required Files
- `Dockerfile`
- `.dockerignore`
- `requirements.txt`
- `opscore/settings.py`

## Build Settings
In Northflank, create a new service using the Git repository or Dockerfile builder.
Use:
- Build context: `/`
- Dockerfile path: `Dockerfile`
- Internal port: `8000`

## Environment Variables
Set these in Northflank service configuration:
- `SECRET_KEY` (required)
- `DEBUG=false`
- `ALLOWED_HOSTS=*` or the Northflank hostname
- `SQLITE_PATH=/data/db.sqlite3` (optional)

> Note: SQLite is not recommended for production. Use PostgreSQL or another managed database if this is a production deployment.

## Optional Persistent Storage
If you want to keep SQLite data after redeploys, mount a volume at `/data` and set:
- `SQLITE_PATH=/data/db.sqlite3`

## Common Northflank Service Options
- `cpu`: 0.5 / 1 / 2
- `memory`: 512Mi / 1Gi
- `restart policy`: on failure

## Deploy Checklist
1. Push this repository to a Git provider accessible by Northflank.
2. Create a Northflank service and choose Docker build.
3. Configure environment variables.
4. Deploy.
5. Visit the service URL.

## Notes
- The image runs `python manage.py collectstatic --noinput` during build.
- If you need a production database, add `psycopg[binary]` and update `opscore/settings.py` to use PostgreSQL.
