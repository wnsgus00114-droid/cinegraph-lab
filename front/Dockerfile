FROM python:3.11-slim
WORKDIR /app
COPY front/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY front/app.py .
EXPOSE 8501
HEALTHCHECK CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health').raise_for_status()"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]

