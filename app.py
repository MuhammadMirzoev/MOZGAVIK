import os, re, json, uuid
from typing import Any, Dict, List, Tuple
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx

# ---- опционально: PyMuPDF для PDF ----
fitz = None
try:
    import fitz as _fitz  # PyMuPDF
    fitz = _fitz
except Exception:
    pass

# =========================
#  Внешний API (игра/чат)
# =========================
APPROXINATION_TOKEN = os.getenv("APPROXINATION_TOKEN", "379f5469-cb64-47ec-bab1-462ee3824c1b")
API_URL = "https://approxination.com/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {APPROXINATION_TOKEN}"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
SAMPLES_ROOT = os.path.join(BASE_DIR, "samples")
os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs(SAMPLES_ROOT, exist_ok=True)

ALLOWED_UPLOADS = {"pdf", "epub", "fb2", "txt"}
CHUNK_LIMIT = 2  # быстрый разбор для загруженных файлов

app = FastAPI(title="Reader + Game + GPT")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")


def redact(text: str) -> str:
    if not text: return text
    return re.sub(r'Bearer\s+[A-Za-z0-9\-\._]+', 'Bearer ***', str(text))[:4000]


def _allowed_file(name: str) -> bool:
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_UPLOADS


def _request_timeout():
    flag = str(os.getenv("NO_TIMEOUT", "")).strip().lower()
    return None if flag in ("1", "true", "yes", "on") else None


# =========================
#  Промпт игры (как ты просил)
# =========================
def build_prompt(book_text: str, opts: dict) -> str:
    """Constructs a styled, constrained prompt for the game generator."""
    vibe = opts.get("vibe", "neon")
    palette = opts.get("palette", "dark")
    difficulty = int(opts.get("difficulty", 60) or 60)
    game_type = opts.get("game_type", "quiz")  # ПОЛУЧАЕМ ТИП ИГРЫ
    long_code = bool(opts.get("long_code", True))
    audio = bool(opts.get("audio", False))
    procedural = bool(opts.get("procedural", True))

    target_length = "минимум 1000 строк кода" if long_code else "столько кода, сколько нужно без пустых строк"
    audio_line = "Добавь музыку и звуковые эффекты." if audio else "Звук не обязателен."
    proc_line = "Добавь процедурную генерацию уровней, если это уместно." if procedural else "Процедурную генерацию не добавляй."
    detail_hint = "Высокая насыщенность анимаций и эффектов." if difficulty >= 66 else ("Умеренные анимации." if difficulty >= 33 else "Минимальные анимации, приоритет — читаемость.")

    # ОПИСАНИЕ ТИПОВ ИГР
    game_type_descriptions = {
        "quiz": "Интерактивный квиз с вопросами по содержанию книги",
        "dialog": "Диалоговая игра с выбором реплик и развитием сюжета",
        "novel": "Визуальная новелла с повествованием и ключевыми выборами",
        "platformer": "Платформер с преодолением препятствий по мотивам сюжета",
        "arcade": "Динамичная аркада, отражающая ключевые события книги",
        "roguelike": "Рогалик с элементами исследования и постоянным развитием"
    }

    game_type_instruction = game_type_descriptions.get(game_type, "Интерактивный квиз с вопросами по содержанию книги")

    prompt = f"""
Ты — мастер создания **2D-игр** на **JavaScript + HTML5 Canvas**.
Тебе дан отрывок текста. По нему нужно сделать мини-игру, в которой механики помогают понять смысл текста.

🎨 Эстетика/вайб: **{vibe}**, палитра: **{palette}**. {detail_hint}
🎮 Тип игры: **{game_type_instruction}**.

Требования к игре:
1) Механика напрямую отражает идеи/сюжет/персонажей текста.
2) У игры есть цель и «финиш», где игрок явно усваивает ключевую мысль.
3) Интерфейс включает:
   - Счётчик очков
   - Кнопку «Стоп»
   - Кнопку «Выход»
   - Подсказки
   - Экран завершения с финальным счётом и кнопкой «Играть снова»
4) Соответствие холста формату **1:1**.
5) Текстовые блоки должны **вмещаться** в отведённые области и выглядеть опрятно (без переполнений).
6) Добавь плавные анимации, аккуратную типографику и сетку. {audio_line}
7) {proc_line}
8) Код — **чистый HTML + JS + Canvas**, чтобы сохранить как `game.html` и запустить в браузере.
9) Направление: доступность, отзывчивость управления, понятная структура.
10) Выдай {target_length}. Комментарии приветствуются, но без «воды».
11) Стиль игры: {game_type_instruction}

Важно:
- Если есть собираемые объекты — делай их достижимыми.
- Не ломай верстку: ничего не должно «ехать».
- Используй единый стиль интерфейса (кнопки, панели, оверлеи).
- Избегай внешних зависимостей, всё — в одном HTML.

____________________________________________________________

ТЕКСТ ДЛЯ ИГРЫ:
{book_text}

____________________________________________________________

Сгенерируй **чистый HTML** (без префиксов/объяснений), полностью готовый к сохранению как `game.html`.
"""
    return prompt


# =========================
#  Разбор текста
# =========================
def _pdf_to_text_chunks(pdf_path: str, max_chars: int = 16000) -> List[str]:
    if not fitz:
        raise RuntimeError("PyMuPDF не установлен (pip install pymupdf)")
    doc = fitz.open(pdf_path)
    buf, chunks, size = [], [], 0
    for page in doc:
        t = page.get_text("text")
        if size + len(t) > max_chars and size > 0:
            chunks.append("".join(buf)); buf, size = [t], len(t)
        else:
            buf.append(t); size += len(t)
    if buf: chunks.append("".join(buf))
    return chunks


def _simple_pages(text: str, page_chars: int = 1200) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    pages, buf, size = [], [], 0
    for p in paras:
        if size + len(p) > page_chars and size > 0:
            pages.append("\n\n".join(buf)); buf, size = [p], len(p)
        else:
            buf.append(p); size += len(p)
    if buf: pages.append("\n\n".join(buf))
    return pages


# =========================
#  Сэмплы (3 книги, по 3+ главы)
# =========================
SAMPLE_DOCS = {
    # 1) ЛИТЕРАТУРНАЯ
    "night_tram": {
        "title": "Ночной трамвай",
        "size": "1.1 MB",
        "meta": "литература • пример",
        "chapters": [
            {
                "title": "Глава 1. Последний рейс",
                "text": (
                    "Город выдохся и затих, когда трамвай с номером 7 сорвался с остановки. "
                    "В салоне остались только двое: водитель и пассажир с чемоданом, на котором выцвела наклейка 'Дом'. "
                    "Рельсы пели, как струны, и их пение говорило о развилках, которых не миновать."
                ),
                "sections": []
            },
            {
                "title": "Глава 2. Пассажиры памяти",
                "text": (
                    "На следующей остановке вошла женщина с письмом. Она не смотрела по сторонам, "
                    "только стискивала конверт. В окнах промелькнули дворы детства, и пассажир с чемоданом улыбнулся, "
                    "впервые заметив, что поездка ведёт не по улицам, а по воспоминаниям."
                ),
                "sections": []
            },
            {
                "title": "Глава 3. Разветвление путей",
                "text": (
                    "У парка рельсы раздвоились. Левая ветка обещала возвращение, правая — неизвестность. "
                    "Трамвай замедлил ход, ожидая решения. Пассажиры поднялись, как на перекличке, и каждый выбрал "
                    "свою сторону — но вагон мог идти только по одной."
                ),
                "sections": []
            },
        ],
        "conspect": [
            "Мотив пути и выбора, трамвай как метафора памяти",
            "Переход от внешнего города к внутренним ландшафтам героя",
            "Развилка как кульминация: возвращение vs неизвестность"
        ],
        "qa": []  # заменили на GPT-чат
    },

    # 2) ПРО ИИ
    "ml_basics": {
        "title": "Основы машинного обучения",
        "size": "1.8 MB",
        "meta": "ИИ • пример",
        "chapters": [
            {
                "title": "Глава 1. Парадигмы",
                "text": "Контролируемое, неконтролируемое и обучение с подкреплением — три базовые парадигмы ML. "
                        "Контролируемое использует размеченные данные; неконтролируемое ищет скрытую структуру; RL оптимизирует политику награды.",
                "sections": []
            },
            {
                "title": "Глава 2. Представление и модели",
                "text": "Линейные модели, деревья решений, ансамбли, нейросети. Баланс смещения и дисперсии. "
                        "Регуляризация (L2, dropout) и нормализация улучшают обобщающую способность.",
                "sections": []
            },
            {
                "title": "Глава 3. Оценка и валидация",
                "text": "Разделение на train/valid/test, кросс-валидация, метрики (Accuracy, Precision/Recall, ROC-AUC, F1). "
                        "Лик утечки, подбор гиперпараметров, мониторинг в проде.",
                "sections": []
            },
        ],
        "conspect": [
            "Три парадигмы ML и их задачи",
            "Выбор модели = компромисс bias/variance",
            "Оценка качества: валидные метрики и честная валидация",
            "Прод-мониторинг предотвращает деградацию"
        ],
        "qa": []
    },

    # 3) ЛОР ИГРЫ
    "light_shards": {
        "title": "Осколки света",
        "size": "1.3 MB",
        "meta": "игровой лор • пример",
        "chapters": [
            {
                "title": "Глава 1. Мир, разбитый на осколки",
                "text": "Когда Сердце Города треснуло, свет рассыпался по районам. "
                        "Каждый осколок хранит эмоцию — от радости до отчаяния — и меняет улицы вокруг.",
                "sections": []
            },
            {
                "title": "Глава 2. Путеводный маяк",
                "text": "По легенде, осколки можно собрать, следуя Эхо — звуку, который слышит только Искатель. "
                        "Но чем ближе к Сердцу, тем сильнее сопротивление ночи.",
                "sections": []
            },
            {
                "title": "Глава 3. Слияние",
                "text": "Все осколки сходятся в Кафедральной Площади. Слияние возвращает городу цвет, "
                        "но выбор Искателя определяет, какой эмоцией будет пульсировать центр.",
                "sections": []
            },
        ],
        "conspect": [
            "Мир меняется под влиянием эмоциональных осколков",
            "Искатель ориентируется по Эхо света",
            "Финальное Слияние задаёт траекторию города"
        ],
        "qa": []
    }
}

def _build_sample_data(cfg: Dict[str, Any]) -> Dict[str, Any]:
    chapters = cfg["chapters"]
    full_text = "\n\n".join((c.get("text") or "") for c in chapters)
    return {
        "title": cfg["title"],
        "size": cfg["size"],
        "meta": cfg["meta"],
        "chapters": chapters,
        "conspect": cfg.get("conspect", []),
        "qa": [],  # GPT вместо статичного Q&A
        "pages": _simple_pages(full_text, page_chars=1200),
    }

def ensure_samples():
    for slug, cfg in SAMPLE_DOCS.items():
        sd = os.path.join(SAMPLES_ROOT, slug)
        os.makedirs(sd, exist_ok=True)
        data_path = os.path.join(sd, "data.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(_build_sample_data(cfg), f, ensure_ascii=False, indent=2)

ensure_samples()


# =========================
#  ROUTES: страница/сэмплы/файлы
# =========================
@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(BASE_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/samples")
def list_samples():
    items = []
    for slug, cfg in SAMPLE_DOCS.items():
        items.append({
            "slug": slug,
            "title": cfg["title"],
            "size": cfg["size"],
            "meta": cfg["meta"],
            "json_url": f"/samples/{slug}/data.json"
        })
    return {"ok": True, "items": items}


@app.get("/samples/{slug}/data.json")
def serve_sample(slug: str):
    path = os.path.join(SAMPLES_ROOT, slug, "data.json")
    if not os.path.isfile(path):
        return JSONResponse({"error": "Файл не найден"}, status_code=404)
    return FileResponse(path, media_type="application/json")


@app.get("/files/{doc_id}/{filename}")
def files(doc_id: str, filename: str):
    path = os.path.join(UPLOAD_ROOT, doc_id, filename)
    if not os.path.isfile(path):
        return JSONResponse({"error": "Файл не найден"}, status_code=404)
    if filename.endswith(".json"):
        return FileResponse(path, media_type="application/json")
    return FileResponse(path)


# =========================
#  Upload
# =========================
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    name = file.filename or ""
    if not _allowed_file(name):
        return JSONResponse({"ok": False, "error": "Допустимы: PDF, EPUB, FB2, TXT"}, status_code=415)

    doc_id = str(uuid.uuid4())[:8]
    doc_dir = os.path.join(UPLOAD_ROOT, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    ext = name.rsplit(".", 1)[1].lower()
    path = os.path.join(doc_dir, name)
    raw_bytes = await file.read()
    with open(path, "wb") as out:
        out.write(raw_bytes)

    try:
        chapters: List[Dict[str, Any]] = []
        if ext == "pdf":
            if not fitz:
                raise RuntimeError("PyMuPDF не установлен (pip install pymupdf)")
            chunks = _pdf_to_text_chunks(path, max_chars=16000)[:CHUNK_LIMIT]
            for idx, ch in enumerate(chunks, 1):
                chapters.append({"title": f"Фрагмент {idx}", "text": ch, "sections": []})
        else:
            text = raw_bytes.decode("utf-8", errors="ignore")
            # делим пополам = 2 фрагмента для быстрого прототипа
            half = max(1, len(text)//2)
            chapters = [
                {"title": "Часть 1", "text": text[:half], "sections": []},
                {"title": "Часть 2", "text": text[half:], "sections": []},
            ]

        full_text = "\n\n".join((c.get("text") or "") for c in chapters)
        data = {
            "title": name,
            "size": f"{round(len(raw_bytes)/1024/1024,2)} MB",
            "meta": f"загружено • {len(chapters)} главы",
            "chapters": chapters,
            "conspect": [],  # GPT-вкладка вместо статичного Q&A
            "qa": [],
            "pages": _simple_pages(full_text, page_chars=1200),
            "doc_id": doc_id,
        }

        out_json = os.path.join(doc_dir, "data.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        return JSONResponse({"ok": False, "error": "Не удалось обработать документ", "details": redact(str(e)), "trace_id": doc_id}, status_code=500)

    return JSONResponse({
        "ok": True,
        "doc_id": doc_id,
        "filename": name,
        "json_url": f"/files/{doc_id}/data.json",
        "chapters_count": len(data.get("chapters", []))
    })


# =========================
#  Генерация игры
# =========================
@app.post("/generate")
async def generate_game(payload: Dict[str, Any]):
    trace_id = str(uuid.uuid4())[:8]
    book_text = (payload.get("text") or "").strip()
    if not book_text:
        return JSONResponse({"error": "Текст пустой", "trace_id": trace_id}, status_code=400)

    prompt = build_prompt(book_text, payload)
    try:
        async with httpx.AsyncClient(timeout=_request_timeout()) as client:
            r = await client.post(API_URL, headers=HEADERS, json={"messages":[{"role":"user","content":prompt}],"model":"solver"})
    except httpx.TimeoutException as e:
        return JSONResponse({"error":"Внешний API не ответил вовремя","details":redact(str(e)),"trace_id":trace_id,"source":"external_api"}, status_code=504)
    except httpx.HTTPError as e:
        return JSONResponse({"error":"Ошибка запроса к внешнему API","details":redact(str(e)),"trace_id":trace_id,"source":"external_api"}, status_code=502)

    text = r.text
    if r.status_code//100 != 2:
        return JSONResponse({"error":"Внешний API вернул ошибку","status":r.status_code,"details":redact(text),"trace_id":trace_id,"source":"external_api"}, status_code=502)

    try:
        data = r.json()
        game_code = data["choices"][0]["message"]["content"]
        if not game_code or "<html" not in game_code.lower():
            raise ValueError("Ответ не похож на HTML игры")
        return JSONResponse({"code": game_code, "trace_id": trace_id})
    except Exception as e:
        return JSONResponse({"error":"Не удалось разобрать ответ внешнего API","details":redact(text) or redact(str(e)),"trace_id":trace_id,"source":"parsing"}, status_code=500)


# =========================
#  GPT-чат по книге
# =========================
_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")

def _tokenize(s: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(s or "")]

def _score(text: str, query_words: List[str]) -> int:
    if not text: return 0
    words = _tokenize(text)
    # простая метрика: количество пересечений (уникальные термы)
    ws = set(words)
    return sum(1 for q in set(query_words) if q in ws)

def _select_context(doc: Dict[str, Any], question: str, max_chars: int = 6000) -> Tuple[str, List[str]]:
    """Вернём слитый контекст и список названий глав, которые попали в контекст."""
    chapters = doc.get("chapters") or []
    qwords = _tokenize(question)
    scored = []
    for ch in chapters:
        text = ch.get("text") or ""
        scored.append(( _score(text, qwords), ch.get("title") or "Без названия", text ))
    # отбираем топ-2 релевантных (или первые 2, если нули)
    scored.sort(key=lambda t: t[0], reverse=True)
    picked = scored[:2] if scored else []
    if not picked and chapters:
        picked = [(0, chapters[0].get("title","Глава 1"), chapters[0].get("text",""))]
    used_titles = [t[1] for t in picked]
    buf, size = [], 0
    for _, title, text in picked:
        chunk = f"### {title}\n{text.strip()}\n"
        if size + len(chunk) > max_chars: break
        buf.append(chunk); size += len(chunk)
    if not buf and chapters:
        # крайний случай — хотя бы первая глава
        buf.append(f"### {chapters[0].get('title','Глава 1')}\n{chapters[0].get('text','')}\n")
    return "\n".join(buf)[:max_chars], used_titles

@app.post("/chat")
async def chat_qa(payload: Dict[str, Any]):
    """
    Принимаем:
      {
        "question": "...",
        "history": [{"role":"user"|"assistant","content":"..."}],
        "doc": {"title":"...", "chapters":[{"title":"...","text":"..."}], "pages":[...]}
      }
    """
    trace_id = str(uuid.uuid4())[:8]
    question = (payload.get("question") or "").strip()
    history = payload.get("history") or []
    doc = payload.get("doc") or {}
    if not question:
        return JSONResponse({"error":"Вопрос пустой","trace_id":trace_id}, status_code=400)

    context, used = _select_context(doc, question, max_chars=6000)
    sys_main = {
        "role": "system",
        "content": (
            "Ты — ассистент по книге. Отвечай по-русски, кратко и по делу. "
            "Отвечай ТОЛЬКО на основе приведённого контекста. "
            "Если информации недостаточно, честно скажи, чего не хватает."
        )
    }
    sys_ctx = {
        "role": "system",
        "content": f"Контекст книги (фрагменты):\n---\n{context}\n---\nОтвечай только по этому контексту."
    }

    # ограничим историю до последних 6 сообщений
    safe_hist = []
    for m in history[-6:]:
        if m and m.get("role") in {"user", "assistant"} and isinstance(m.get("content"), str):
            safe_hist.append({"role": m["role"], "content": m["content"]})

    messages = [sys_main, sys_ctx] + safe_hist + [{"role":"user","content":question}]
    req = {"model":"solver", "messages": messages, "temperature": 0.2, "max_tokens": 700}

    try:
        async with httpx.AsyncClient(timeout=_request_timeout()) as client:
            r = await client.post(API_URL, headers=HEADERS, json=req)
    except httpx.TimeoutException as e:
        return JSONResponse({"error":"Внешний API не ответил вовремя","details":redact(str(e)),"trace_id":trace_id}, status_code=504)
    except httpx.HTTPError as e:
        return JSONResponse({"error":"Ошибка запроса к внешнему API","details":redact(str(e)),"trace_id":trace_id}, status_code=502)

    text = r.text
    if r.status_code//100 != 2:
        return JSONResponse({"error":"Внешний API вернул ошибку","status":r.status_code,"details":redact(text),"trace_id":trace_id}, status_code=502)

    try:
        data = r.json()
        answer = data["choices"][0]["message"]["content"]
        return JSONResponse({"answer": answer, "used": used, "trace_id": trace_id})
    except Exception as e:
        return JSONResponse({"error":"Не удалось разобрать ответ внешнего API","details":redact(text) or redact(str(e)),"trace_id":trace_id,"source":"parsing"}, status_code=500)


# =========================
#  Global error
# =========================
@app.exception_handler(Exception)
async def on_unhandled(request: Request, exc: Exception):
    trace_id = str(uuid.uuid4())[:8]
    return JSONResponse({"error":"Внутренняя ошибка","details":redact(str(exc)),"trace_id":trace_id,"source":"backend"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=os.getenv("HOST","127.0.0.1"), port=int(os.getenv("PORT","5000")), reload=True)
