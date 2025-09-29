# Dockerfile (recommended)
FROM python:3.12-alpine

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system deps + nodejs & npm
RUN apk add --no-cache \
    gcc musl-dev libffi-dev openssl-dev libuv-dev \
    nodejs npm git

# Copy requirements and install globally
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Debug step (optional)
RUN python -c "import uvicorn; print('uvicorn ok')"

# Copy application code
COPY . /app

# Install node deps for template (if you need them at build time)
RUN npm install --prefix templates/next-basic || true

# Expose ports
EXPOSE 8081
EXPOSE 3000-3050

# Use uvicorn directly (recommended) or your run.py
# If your FastAPI app is in run.py and exposes `app`, you can use:
# CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
# Otherwise use run.py
CMD ["python", "run.py"]
