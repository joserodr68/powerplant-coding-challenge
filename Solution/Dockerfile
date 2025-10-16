FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY main.py .

# Expose port 8888
EXPOSE 8888

CMD ["python", "main.py"]