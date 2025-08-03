# Use an official Python runtime as a base image
FROM python:3.13.5-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt 

# Copy the rest of the application code into the container
# Copy application code
COPY app/ ./app/
COPY pytest.ini .
COPY tests/ ./tests/

# Copy environment files
COPY .env ./.env

# Expose the application port
EXPOSE ${PORT}

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/docs || exit 1

# Set the command to run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]