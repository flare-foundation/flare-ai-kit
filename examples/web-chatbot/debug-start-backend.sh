#!/bin/bash
echo "================================================"
echo "Working directory: $(pwd)"
echo "PATH: $PATH"
echo "VIRTUAL_ENV: $VIRTUAL_ENV"
echo "Listing /app/.venv/bin/:"
ls -l /app/.venv/bin/
echo "Checking start-backend:"
if [ -f /app/.venv/bin/start-backend ]; then
    echo "start-backend exists"
    #cat /app/.venv/bin/test_script
    #echo "Executing /app/.venv/bin/test_script..."
    #exec /app/.venv/bin/test_script
    echo "Checking /app/.venv/lib/python3.12/site-packages/ for flare_ai_kit_web_chatbot:"
    ls /app/.venv/lib/python3.12/site-packages/ | grep -E 'flare_ai_kit_web_chatbot|flare-ai-kit-web-chatbot'
    cat /app/.venv/bin/start-backend
    echo "Executing /app/.venv/bin/start-backend..."
    exec /app/.venv/bin/start-backend
    echo "Executing start-backend..."
    exec start-backend
    echo "Executing py.test"
    exec /app/.venv/bin/py.test
else
    echo "start-backend NOT found"
    exit 1
fi