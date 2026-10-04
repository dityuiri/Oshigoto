#!/usr/bin/env bash
# おしごと dev server, LAN-accessible so you can open it from your phone.
cd "$(dirname "$0")"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8710 --reload
