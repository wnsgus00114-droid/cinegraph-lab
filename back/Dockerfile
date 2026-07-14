FROM python:3.11-slim
WORKDIR /app
COPY back/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY back/app ./back/app
COPY data ./data
ENV PYTHONPATH=/app DATA_DIR=/app/data
EXPOSE 8000
CMD ["uvicorn", "back.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

