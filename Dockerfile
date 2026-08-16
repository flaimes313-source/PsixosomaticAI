FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ВАЖНО: запускаем как модуль, а не как файл
# Это автоматически добавит /app в PYTHONPATH и решит проблему импортов
CMD ["python", "-m", "app.main"]
