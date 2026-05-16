FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директории для логов и данных
RUN mkdir -p /app/logs /app/data

# Запускаем бота
CMD ["python", "-u", "bot.py"]
