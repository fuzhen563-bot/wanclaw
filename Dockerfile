# WanClaw - SME AI Assistant System
# Dockerfile for production deployment

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY ./wanclaw/backend/im_adapter/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir psutil openpyxl aiofiles && \
    pip install --no-cache-dir \
    redis>=5.0.0 \
    celery>=5.3.0 \
    langchain>=0.1.0 \
    langchain-core>=0.1.0 \
    pyautogui>=0.9.54 \
    opencv-python>=4.8.0 \
    pytesseract>=0.3.10 \
    playwright>=1.40.0

# Install playwright browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/data/logs /app/data/backups /app/data/config /app/data/workspace

# Create non-root user
RUN useradd -m -u 1000 wanclaw && \
    chown -R wanclaw:wanclaw /app

USER wanclaw

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

# Default command
CMD ["python", "-m", "wanclaw.backend.im_adapter.main"]