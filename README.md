# SPA + Генератор игры (интеграция во вкладку «Визуал»)

## Файлы
- `index.html` — ваш исходный фронтенд (SPA) **без изменений во внешнем виде**, во вкладке **Визуал** добавлены контролы и предпросмотр игры.
- `app.py` — Flask-сервер: раздаёт SPA и эндпоинт `POST /generate`.

## Запуск
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export APPROXINATION_TOKEN="ВАШ_ТОКЕН"   # Windows (PowerShell): setx APPROXINATION_TOKEN "ВАШ_ТОКЕН"
python app.py
```
Открой: http://localhost:5000

## Использование
1. Открой вкладку **Документ → Визуал**.
2. Вставь текст, выбери настройки (`vibe`, `palette`, `difficulty`, `long_code`, `audio`, `procedural`, `game_type`).
3. Нажми «Создать игру». Результат появится в iframe, можно скачать **game.html**.
