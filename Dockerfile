FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt . 2>/dev/null || true
RUN pip install --no-cache-dir httpx fastapi uvicorn websockets pydantic
COPY . .
CMD ["python", "main.py"]
