FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libldap2-dev \
        libsasl2-dev \
        python3-dev \
        libpq-dev \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Run entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Create user and set up directories
RUN groupadd -g 12318 appgroup && \
    useradd -u 11692 -g appgroup -m appuser && \
    mkdir -p /app /app/celery /home/appuser/.cache && \
    chmod +x /docker-entrypoint.sh && \
    chown -R appuser:appgroup /app /app/celery /home/appuser /docker-entrypoint.sh


USER appuser
ENV HOME=/home/appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .


ENTRYPOINT ["/docker-entrypoint.sh"] 
