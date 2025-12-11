FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY tailleader /app/tailleader
COPY tailleader/static /app/tailleader/static
ENV PYTHONUNBUFFERED=1
EXPOSE 8088
CMD ["python", "-m", "uvicorn", "tailleader.app:app", "--host", "0.0.0.0", "--port", "8088"]
