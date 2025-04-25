# Dockerfile

# Stage 1: Build template Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
COPY examples/web-chatbot/frontend/ .
RUN npm install
RUN npm run build

# Stage 2: Build Backend
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS backend-builder
# Install core SDK
#COPY ../../pyproject.toml ../../uv.lock ../../src /flare-ai-kit/
COPY /pyproject.toml /uv.lock /src /README.md /flare-ai-kit/
WORKDIR /flare-ai-kit
RUN uv sync --frozen
RUN ls -l /flare-ai-kit/.venv/bin/ 
# Install web chatbot
#COPY examples/web-chatbot /web-chatbot
#WORKDIR /web-chatbot
#RUN uv sync --frozen
#RUN ls -l /web-chatbot/.venv/bin/ && test -f /web-chatbot/.venv/bin/start-backend && echo "start-backend found in /web-chatbot/.venv/bin" || (echo "start-backend NOT found in /web-chatbot/.venv/bin" && exit 1)

#RUN ls /app/.venv/lib/python3.12/site-packages/ | grep -E 'flare_ai_kit_web_chatbot|flare-ai-kit-web-chatbot'
#RUN ls /web-chatbot/.venv/ 
#RUN ls /web-chatbot/.venv/lib/
#RUN ls /web-chatbot/.venv/lib/python3.12/
#RUN ls /web-chatbot/.venv/lib/python3.12/site-packages/

# Fix shebang start-backend
# This is needed because when uv sync creates the start-backend script it adds a shebang with a path to 
# the python interpreter for the current venv. However, this path is incorrect when the venv is copied 
# in stage 3 of this Dockerfile.
#RUN sed -i '1s|^.*$|#!/app/.venv/bin/python|' /web-chatbot/.venv/bin/start-backend


ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Stage 3: Final Image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install nginx
RUN apt-get update && apt-get install -y nginx supervisor curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
#COPY --from=backend-builder /web-chatbot/.venv ./.venv
#RUN ls -l /app/.venv/bin/ && test -f /app/.venv/bin/start-backend && echo "start-backend found in /app/.venv/bin" || (echo "start-backend NOT found in /app/.venv/bin" && exit 1)
#RUN cat /app/.venv/bin/start-backend
#COPY --from=backend-builder /web-chatbot/backend ./backend
#COPY --from=backend-builder /web-chatbot/pyproject.toml .
#COPY --from=backend-builder /web-chatbot/README.md .
#COPY --from=backend-builder /flare-ai-kit .
COPY examples/web-chatbot/debug-start-backend.sh ./debug-start-backend.sh

RUN ls
COPY examples/web-chatbot .
COPY --from=backend-builder /flare-ai-kit /flare-ai-kit
RUN ls
RUN uv sync --frozen
RUN ls /app/.venv/bin

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy frontend files
COPY --from=frontend-builder /frontend/build /usr/share/nginx/html
#COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html


# Copy nginx configuration
COPY examples/web-chatbot/nginx.conf /etc/nginx/sites-enabled/default

# Copy Let's Encrypt TLS certificate and key
#COPY fullchain.pem /app/fullchain.pem
#COPY privkey.pem /app/privkey.pem

# Setup supervisor configuration
COPY examples/web-chatbot/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Allow workload operator to override environment variables
LABEL "tee.launch_policy.allow_env_override"="GEMINI_API_KEY,GEMINI_MODEL,WEB3_PROVIDER_URL,WEB3_EXPLORER_URL,SIMULATE_ATTESTATION"
LABEL "tee.launch_policy.log_redirect"="always"

EXPOSE 80
EXPOSE 443

# Start supervisor (which will start both nginx and the backend)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]