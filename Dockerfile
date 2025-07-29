FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (including curl for Node.js setup)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p logs media staticfiles static

# Build Tailwind CSS BEFORE collecting static files
RUN python manage.py tailwind install --no-input
RUN python manage.py tailwind build

# NOW collect static files (including the built Tailwind CSS)
RUN python manage.py collectstatic --noinput

# Create a non-root user that matches your host user
ARG UID=1000
ARG GID=1000

RUN groupadd -g $GID appuser && \
    useradd -u $UID -g $GID -m appuser

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Default command (will be overridden by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]