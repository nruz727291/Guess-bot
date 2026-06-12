FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for Docker cache)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create logs directory
RUN mkdir -p logs

# Run the bot
CMD ["python", "main.py"]
