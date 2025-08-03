# Running the Application

## Development Server

To run the application in development mode with auto-reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Production Server

To run the application in production mode:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Using Docker

### Build and Run with Docker Compose

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8001`

### Run with Existing Docker Image

```bash
docker-compose up
```

## Environment Variables

The application uses the following environment variables (defined in `.env`):

- `PORT`: Server port (default: 8001)
- `LOG_LEVEL`: Logging level (default: INFO)
- `RELOAD`: Enable/disable auto-reload (default: true)
- `HF_HOME`: Hugging Face model cache directory

## API Documentation

Once the server is running, you can access:

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## Health Check

The application includes a health check endpoint at `http://localhost:8001/health`.
