FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose the Flask port
EXPOSE 5000

# Initialize the database during container build
RUN python app.py --setup

# Default command to run the application
CMD ["python", "app.py"]