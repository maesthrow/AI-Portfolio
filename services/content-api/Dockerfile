FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# системные зависимости при необходимости
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

# сначала копируем только манифест, чтобы кеш слоёв лучше работал
COPY pyproject.toml ./
# если есть poetry.lock / uv.lock — тоже можно скопировать
COPY uv.lock ./

# ставим зависимости проекта (PEP 621)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# затем копируем код
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
