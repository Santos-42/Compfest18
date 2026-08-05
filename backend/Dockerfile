FROM python:3.11-slim

WORKDIR /app

# System deps minimal (geos untuk OR-Tools tidak wajib; runtime-nya pure Python/C++ wheel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# -X utf8: pastikan print/log aman di container
CMD ["python", "-X", "utf8", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
