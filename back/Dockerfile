FROM python:3.11-slim
WORKDIR /app
COPY back/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY back/app ./back/app
COPY scripts/train_mlp.py ./scripts/train_mlp.py
COPY data ./data
COPY artifacts ./artifacts
ENV PYTHONPATH=/app DATA_DIR=/app/data MLP_MODEL_PATH=/app/artifacts/mlp_recommender.joblib
EXPOSE 8000
CMD ["uvicorn", "back.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
