# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY . .

# Set environment variables for Google Cloud
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the Flask app
CMD ["python", "app.py"]
