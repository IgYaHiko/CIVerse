FROM python:3.9-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY openenv.yaml .
COPY inference.py .

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=7860

# Expose port
EXPOSE 7860

# Run the Flask app
CMD ["python", "backend/app.py"]