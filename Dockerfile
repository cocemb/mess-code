FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY .env.example .env

# Create directories
RUN mkdir -p /app/firmware /app/logs

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "src.otbr_manager.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
