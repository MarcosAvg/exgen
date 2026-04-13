#!/bin/bash
export PYTHONPATH="/app/share/exgen:$PYTHONPATH"
exec python3 /app/share/exgen/main.py "$@"
