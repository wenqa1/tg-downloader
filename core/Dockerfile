FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create runtime directories
RUN mkdir -p /app/sessions /app/logs

# Run
CMD ["python", "src/main.py"]
