FROM python:3.9-slim
LABEL authors="Maksym"

WORKDIR /app

# Копіюємо requirements і встановлюємо
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код
COPY . .

# Cloud Run вимагає порт 8080
ENV PORT=8080

# Запуск
CMD streamlit run app.py --server.port 8080 --server.address 0.0.0.0