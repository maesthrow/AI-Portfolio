FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

# сначала только манифест (uv.lock не нужен для pip)
COPY pyproject.toml ./

# ставим зависимости проекта из pyproject (без GigaChat!)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# 👉 ДОСТАВЛЯЕМ GigaChat поверх, игнорируя его зависимости
# чтобы не было конфликта с langchain-core, как у uv
RUN pip install --no-cache-dir --no-deps \
    "gigachat==0.1.43" \
    "langchain-gigachat==0.3.12"

# затем код
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
