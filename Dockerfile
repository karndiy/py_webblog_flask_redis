# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install system dependencies and Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Expose port 5000 for Flask
EXPOSE 5000

# Set environment variable to ensure Flask runs in production mode
ENV FLASK_ENV=production

# Command to run the app
CMD ["python", "run.py"]