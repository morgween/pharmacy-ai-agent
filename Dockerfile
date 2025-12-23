# Multi-stage build for optimal image size

# Stage 1: Python dependencies
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install system dependencies for compiling wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final backend image
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=backend-builder /root/.local /root/.local

# Copy application code
COPY backend/ ./backend/
COPY data/ ./data/
COPY open_ai_tool_schemas/ ./open_ai_tool_schemas/
COPY .env.example .env

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

# Run application
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
