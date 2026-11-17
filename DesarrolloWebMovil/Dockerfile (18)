FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .
# No correr como root dentro del contenedor
RUN useradd --create-home cervecero
USER cervecero
EXPOSE 8003
CMD ["uvicorn", "auth_service:app", "--host", "0.0.0.0", "--port", "8003"]
