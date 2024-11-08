# Stage 1: Builder
FROM python:3.11-slim-bullseye as builder

# Set working directory
WORKDIR /app

# Copy only the requirements file
COPY requirements.txt .

# Install build dependencies and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Final
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.local/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"


# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only necessary application code

COPY lib ./app/lib
COPY services/live ./app/services/live

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser


# Run the application with uvicorn
CMD ["uvicorn", "app.services.live.live-service:app", "--host", "0.0.0.0", "--port", "8002"]
