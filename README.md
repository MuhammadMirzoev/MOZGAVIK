# Учебный помощник AI — Читалка + Игра по тексту

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-green.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](#license)

Веб-приложение для работы с учебными и художественными материалами:

- **Чанки** — просмотр глав/фрагментов.
- **Конспект** — ключевые тезисы.
- **Q&A** — вопросы/ответы.
- **Визуал (Игра)** — генерация **полноценной 2D-игры** по отрывку (HTML5 Canvas + JS) через внешний API.

> На главной уже есть **три книги**, которые **были загружены ранее** и сохранены для **быстрого доступа**. Их можно сразу открыть без загрузки файла.

---

## Содержание

- [Особенности](#особенности)
- [Архитектура](#архитектура)
- [Требования](#требования)
- [Установка и запуск (локально)](#установка-и-запуск-локально)
- [Переменные окружения](#переменные-окружения)
- [Структура проекта](#структура-проекта)
- [Как пользоваться](#как-пользоваться)
- [API](#api)
- [Примеры запросов](#примеры-запросов)
- [Сэмплы (быстрый доступ)](#сэмплы-быстрый-доступ)
- [Деплой](#деплой)
  - [Docker](#docker)
  - [docker-compose](#docker-compose)
  - [Nginx (reverse proxy)](#nginx-reverse-proxy)
  - [systemd](#systemd)
- [Тонкая настройка](#тонкая-настройка)
- [Траблшутинг](#траблшутинг)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Безопасность](#безопасность)
- [Лицензия](#лицензия)

---

## Особенности

- **Единый SPA-интерфейс**: `#/home`, `#/doc/chunks`, `#/doc/conspect`, `#/doc/qa`, `#/doc/visual`.
- **Эксклюзивные вкладки**: при переключении предыдущая вкладка *полностью очищается* (игра во «Визуал» *жёстко сбрасывается* и освобождает ресурсы).
- **Полноэкранная игра** во вкладке «Визуал» (большой iframe ~75vh, можно поднять).
- **Быстрый доступ к трём книгам** (ранее загруженные примеры).
- **Загрузка своих файлов** (PDF/EPUB/FB2/TXT). Для MVP текст режется на 2 фрагмента.
- **Генерация игры** через внешний API (см. переменные окружения).

---

## Архитектура

- **Backend**: FastAPI + Uvicorn.
- **Frontend**: чистый HTML/CSS/JS (`index.html`) с hash-роутингом.
- **Парсинг**:
  - PDF — PyMuPDF (если установлен).
  - TXT/EPUB/FB2 — как простой текст (MVP).
- **Данные**:
  - `samples/` — **ранее загруженные** книги, лежат локально и используются как «Недавние документы».

---

## Требования

- Python **3.10+**
- pip
- (опционально) virtualenv
- Для PDF: `pymupdf`

---

## Установка и запуск (локально)

```bash
# 1) создать окружение (опционально)
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2) зависимости
pip install fastapi uvicorn httpx pymupdf

# 3) токен для генерации игры
# Linux/Mac:
export APPROXINATION_TOKEN="ТВОЙ_ТОКЕН"
# Windows PowerShell:
#setx APPROXINATION_TOKEN "ТВОЙ_ТОКЕН"

# 4) запуск
python -m uvicorn app:app --reload --host 0.0.0.0 --port 5000
# Открыть http://localhost:5000
```

> Если видишь предупреждение `You must pass the application as an import string to enable 'reload' or 'workers'.` — запускай именно так: `uvicorn app:app --reload`.

---

## Переменные окружения

| Переменная            | Описание                                                           | Обяз. |
|-----------------------|--------------------------------------------------------------------|:-----:|
| `APPROXINATION_TOKEN` | API-токен для `https://approxination.com/v1/chat/completions`      |  ✅   |
| `HOST`                | Хост Uvicorn (по умолчанию `0.0.0.0`)                              |  ✅   |
| `PORT`                | Порт Uvicorn (по умолчанию `5000`)                                 |  ✅   |
| `NO_TIMEOUT`          | `1/true/on` — отключить таймаут HTTP-клиента                       |  ✅   |

---

## Структура проекта

```
.
├── app.py              # FastAPI backend, эндпоинты, выдача samples, генерация игры
├── index.html          # Frontend SPA (таб-интерфейс)
├── uploads/            # загруженные пользователем файлы и их data.json
├── samples/            # ранее загруженные книги (быстрый доступ, JSON)
├── README.md           # этот файл
└── docs/               # (опц.) скриншоты для README
```

---

## Как пользоваться

1. Открой `http://localhost:5000`.
2. На **главной**:
   - Перетащи свой файл или нажми «Выбрать файл».
   - Или кликни по одной из **трёх книг** в «Недавних документах» — это **ранее загруженные** книги для быстрого доступа.
3. В **документе**:
   - Левая часть — **Чтение** (листай страницы).
   - Правая часть — вкладки:
     - **Чанки** — показывает главы/фрагменты.
     - **Конспект** — ключевые тезисы (для примеров заранее созданы).
     - **Q&A** — вопросы/ответы (для примеров заранее созданы).
     - **Визуал** — форма параметров и кнопка «Запустить анализ» → открывается **игра** (большой iframe). Есть «Назад к настройкам» и «Скачать game.html».
4. Переключение вкладок всегда **очищает** предыдущую (игра выгружается).

---

## API

Базовый URL: `http://localhost:5000`

| Метод | Путь                         | Описание                                       |
|------:|------------------------------|------------------------------------------------|
| GET   | `/`                          | Отдаёт `index.html`                            |
| GET   | `/samples`                   | Список ранее загруженных книг (быстрый доступ) |
| GET   | `/samples/{slug}/data.json`  | JSON книги (заголовки, главы, конспект, QA)    |
| POST  | `/upload`                    | Загрузка файла (PDF/EPUB/FB2/TXT)              |
| GET   | `/files/{id}/{filename}`     | Файлы из `uploads/` по id                      |
| POST  | `/generate`                  | Генерация HTML-игры по отрывку                 |

### Форматы

**`/samples` (GET)**
```json
{
  "ok": true,
  "items": [
    {
      "slug": "night_tram",
      "title": "Ночной трамвай",
      "size": "1.1 MB",
      "meta": "литература • пример",
      "json_url": "/samples/night_tram/data.json"
    }
  ]
}
```

**`/samples/{slug}/data.json` (GET)**
```json
{
  "title": "Ночной трамвай",
  "size": "1.1 MB",
  "meta": "литература • пример",
  "chapters": [
    {"title":"Глава 1. ...","text":"..."},
    {"title":"Глава 2. ...","text":"..."},
    {"title":"Глава 3. ...","text":"..."}
  ],
  "conspect": ["Пункт 1", "Пункт 2"],
  "qa": [{"q":"Вопрос","a":"Ответ"}],
  "pages": ["стр. 1 ...", "стр. 2 ..."]
}
```

**`/upload` (POST, multipart/form-data)**  
Параметр: `file`  
Успех:
```json
{
  "ok": true,
  "doc_id": "a1b2c3d4",
  "filename": "my.pdf",
  "json_url": "/files/a1b2c3d4/data.json",
  "chapters_count": 2
}
```

**`/generate` (POST, JSON)**  
Тело:
```json
{
  "text": "Отрывок текста",
  "vibe": "neon",
  "palette": "dark",
  "difficulty": 60,
  "game_type": "quiz",
  "long_code": true,
  "audio": false,
  "procedural": true
}
```
Ответ:
```json
{
  "code": "<!DOCTYPE html>...полный HTML игры...",
  "trace_id": "c9f1a2b3"
}
```

---

## Сэмплы (быстрый доступ)

На главной доступны 3 книги **из ранее загруженных материалов** (сохранены локально для мгновенного открытия):

1. **Ночной трамвай** *(литература)* — 3 главы, содержит конспект и Q&A.
2. **Основы машинного обучения** *(ИИ)* — 3 главы, содержит конспект и Q&A.
3. **Осколки света** *(лор игры)* — 3 главы, содержит конспект и Q&A.

Файлы в `samples/` — это готовые JSON-структуры, используемые интерфейсом как «Недавние документы».

---

## Генерация игры — промпт

В `app.py` функция `build_prompt()` формирует промпт с параметрами `vibe`, `palette`, `difficulty`, `game_type`, `long_code`, `audio`, `procedural` и строгими требованиями к выходному **HTML+JS (Canvas)**: холст 1:1, счётчик, «Стоп», «Выход», подсказки, финальный экран «Играть снова», чистый один файл без внешних зависимостей, аккуратная типографика/анимации.

---

## Деплой

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app.py index.html README.md ./
RUN pip install --no-cache-dir fastapi uvicorn httpx pymupdf
ENV HOST=0.0.0.0 PORT=5000
EXPOSE 5000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
```

```bash
docker build -t reader-game .
docker run --rm -p 5000:5000   -e APPROXINATION_TOKEN="ТВОЙ_ТОКЕН"   -v $PWD/uploads:/app/uploads   -v $PWD/samples:/app/samples   reader-game
```

### docker-compose

```yaml
version: "3.9"
services:
  web:
    build: .
    ports: ["5000:5000"]
    environment:
      APPROXINATION_TOKEN: "${APPROXINATION_TOKEN}"
      HOST: "0.0.0.0"
      PORT: "5000"
    volumes:
      - ./uploads:/app/uploads
      - ./samples:/app/samples
    restart: unless-stopped
```

### Nginx (reverse proxy)

```nginx
server {
  listen 80;
  server_name example.com;

  location / {
    proxy_pass         http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade $http_upgrade;
    proxy_set_header   Connection "upgrade";
    proxy_set_header   Host $host;
    proxy_read_timeout 3600;
  }
}
```

### systemd

```ini
[Unit]
Description=Reader + Game (FastAPI)
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/reader-game
Environment="APPROXINATION_TOKEN=..."
ExecStart=/usr/bin/env uvicorn app:app --host 0.0.0.0 --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Тонкая настройка

- Прод-режим: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app`.
- Кеш статики через Nginx.
- Для больших PDF увеличьте лимиты в `_pdf_to_text_chunks`.
- Rate-limit/ретраи на внешний API `/generate`.
- Контроль размера загрузок (Nginx `client_max_body_size`).

---

## Траблшутинг

- **Reload/Workers warning** — запускай `uvicorn app:app --reload`.
- **415 при загрузке** — поддерживаются только PDF/EPUB/FB2/TXT.
- **PDF не обрабатывается** — установи `pymupdf`.
- **502/504 на `/generate`** — проверь токен/сеть/лимиты.
- **Игра маленького размера** — увеличь высоту `.viz-frame` (например, `90vh`).

---

## FAQ

**Можно ли автогенерировать конспект/Q&A для загруженных файлов?**  
Да, добавьте в `/upload` вызовы вашего LLM и заполните поля `conspect`/`qa`.

**Где менять параметры игры/промпт?**  
В `app.py`, функция `build_prompt()`.

**Можно ли сохранять итоговую игру?**  
Да, кнопка «Скачать game.html» во вкладке «Визуал».

---

## Roadmap

- [ ] LLM-конспект и Q&A для загруженных файлов.
- [ ] Улучшенный парсер EPUB/FB2 (оглавление/главы).
- [ ] Расширенные настройки игры и шаблоны.
- [ ] История сессий и сохранённые игры.
- [ ] i18n (RU/EN), E2E-тесты, CI/CD.

---

## Безопасность

- Не храните `APPROXINATION_TOKEN` в репозитории.
- В проде отключайте `--reload`, ставьте HTTPS и лимиты запросов.
- Минимизируйте логи с секретами (в проекте используется редактирование `Bearer ***`).

---

## Лицензия

MIT — см. файл `LICENSE`.
