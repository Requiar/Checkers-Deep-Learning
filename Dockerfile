FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# We need the backend directory to be accessible for Python imports
COPY backend/ ./backend/

# Run the backend process on port 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
