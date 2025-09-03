# Use an official Python runtime as a base image
FROM python:3.10.8-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir -r requirements.txt 


# Expose the application port (container listens on 8000 by default)
EXPOSE 8000
