FROM python:3.12-slim
ARG REVISION=development
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 KOKBOT_REVISION=$REVISION
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home kokbot
COPY --chmod=755 backend ./backend
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=3)"
CMD ["uvicorn", "backend.handoff:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
