from flask import Flask, request, jsonify, render_template_string
import requests
import traceback, uuid, re, os, pprint

app = Flask(__name__)

APPROXINATION_TOKEN = '379f5469-cb64-47ec-bab1-462ee3824c1b'

# =========================
#  External API settings
# =========================
API_URL = "https://approxination.com/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {APPROXINATION_TOKEN}"
}

# =========================
#  Utils
# =========================
def redact(text: str) -> str:
    """Mask tokens/secrets in logs and responses."""
    if not text:
        return text
    text = re.sub(r'Bearer\s+[A-Za-z0-9\-\._]+', 'Bearer ***', text)
    # Limit length to avoid flooding logs/response
    return text[:4000]

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
#  HTML Page (Neon-Dark UI)
# =========================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Генератор игр по тексту</title>
  <style>
    :root{
      --bg:#0d0f14; --panel:#141824; --muted:#7b8191; --brand:#6ee7ff; --brand-2:#8b5cf6; --border:#202536; --txt:#e6e7ee; --txt-2:#b8bcc9;
    }
    *{box-sizing:border-box}
    html,body{height:100%}
    body{
      margin:0; font-family:Inter,system-ui,Segoe UI,Roboto,Arial,sans-serif; background: radial-gradient(1200px 1200px at 120% -10%, rgba(110,231,255,.12), transparent 55%),
                radial-gradient(1000px 1000px at -20% 120%, rgba(139,92,246,.10), transparent 55%), var(--bg);
      color:var(--txt); display:flex; flex-direction:column;
    }
    header{
      padding:16px 22px; border-bottom:1px solid var(--border); backdrop-filter:saturate(150%) blur(6px);
      background:linear-gradient(180deg, rgba(20,24,36,.65), rgba(20,24,36,.35));
      display:flex; align-items:center; justify-content:space-between; gap:16px; position:sticky; top:0; z-index:10;
    }
    .logo{display:flex; align-items:center; gap:12px; font-weight:700; letter-spacing:.3px}
    .logo-badge{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--brand),var(--brand-2)); display:grid; place-items:center; color:#041016; font-weight:800}
    .sub{color:var(--txt-2); font-size:12px}
    .container{flex:1; display:grid; gap:18px; grid-template-columns: 420px 1fr; padding:18px}
    @media (max-width:1100px){ .container{grid-template-columns:1fr; } }
    .card{background:linear-gradient(0deg, rgba(255,255,255,.015), rgba(255,255,255,.03)); border:1px solid var(--border); border-radius:16px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,.25)}
    .card h3{margin:0; padding:14px 16px; border-bottom:1px solid var(--border); font-size:14px; letter-spacing:.3px; color:#cfd3e2}
    .card-body{padding:14px; display:flex; flex-direction:column; gap:12px}
    .drop{position:relative; border:1px dashed #2a3147; border-radius:12px; padding:10px; transition:.2s background;}
    .drop.dragover{background:rgba(110,231,255,.06); border-color:var(--brand)}
    textarea{
      width:100%; min-height:280px; resize:vertical; border:0; outline:none; background:#0b0e16; color:var(--txt);
      border-radius:10px; padding:12px; line-height:1.5; font-size:14px;
    }
    .muted{color:var(--muted); font-size:12px}
    .row{display:flex; gap:10px; flex-wrap:wrap}
    .row > *{flex:1}
    .chip{display:flex; align-items:center; justify-content:space-between; gap:8px; padding:10px 12px; border:1px solid var(--border); border-radius:10px; background:#0b0e16}
    select, input[type="range"], input[type="checkbox"]{width:100%}
    .range-label{display:flex; align-items:center; justify-content:space-between; font-size:12px; color:var(--txt-2)}
    .switch{display:flex; align-items:center; gap:8px; font-size:13px; color:var(--txt-2)}
    .actions{display:flex; gap:10px; flex-wrap:wrap}
    button{
      cursor:pointer; border:1px solid var(--border); background:linear-gradient(180deg,#12192a,#0c1220); color:var(--txt);
      padding:12px 14px; border-radius:12px; font-weight:600; letter-spacing:.2px; transition:.2s transform, .2s border-color, .2s background;
    }
    button:disabled{opacity:.6; cursor:not-allowed}
    .btn-primary{background:linear-gradient(135deg, rgba(110,231,255,.18), rgba(139,92,246,.18)); border-color:#2b344f}
    .btn-primary:hover{transform:translateY(-1px); border-color:#3e4971}
    .btn-ghost{background:transparent}
    .kbd{background:#0b0e16; border:1px solid var(--border); padding:2px 6px; border-radius:6px; font-size:11px; color:#cbd5e1}
    .preview-wrap{display:flex; flex-direction:column; gap:10px; height:100%}
    .helper{display:flex; align-items:center; justify-content:space-between; padding:0 2px}
    .frame{flex:1; border:1px solid var(--border); border-radius:14px; overflow:hidden; background:#fff; position:relative;}
    iframe{width:100%; height:100%; border:0}
    .loader{
      position:absolute; inset:0; display:none; align-items:center; justify-content:center; flex-direction:column; gap:10px;
      background:linear-gradient(0deg, rgba(13,15,20,.55), rgba(13,15,20,.55));
      color:#dbeafe; font-weight:600; font-size:14px;
    }
    .loader.show{display:flex}
    .spinner{width:38px;height:38px;border-radius:50%;border:3px solid rgba(255,255,255,.15); border-top-color:var(--brand); animation:spin 1s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .pill{padding:6px 10px; border:1px solid var(--border); border-radius:999px; font-size:12px; color:var(--txt-2)}
    .stat{display:flex; align-items:center; gap:8px; font-size:12px; color:var(--txt-2)}
    .stat b{color:#e2e8f0}
    .footer{padding:10px 16px; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; color:var(--muted); font-size:12px}
    /* Error box */
    #errorBox{display:none; border:1px solid #3a3f55; background:#0b0e16; color:#e2e8f0; border-radius:12px; padding:10px; font-size:13px;}
    #errorBox pre{white-space:pre-wrap; margin:8px 0 0 0; color:#cbd5e1;}
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <div class="logo-badge">GM</div>
      <div>Генератор игр <div class="sub">по текстам — красиво, быстро, мощно</div></div>
    </div>
    <div class="pill">Canvas • HTML • JS</div>
  </header>

  <main class="container">
    <!-- Left: Editor + Controls -->
    <section class="card">
      <h3>Текст книги</h3>
      <div class="card-body">
        <div id="dropZone" class="drop">
          <textarea id="bookText" placeholder="Вставь сюда отрывок. Можно перетащить .txt или .md файл на эту область…"></textarea>
        </div>
        <div class="helper">
          <span class="stat"><b id="wordCount">0</b> слов</span>
          <span class="muted">Совет: удерживай <span class="kbd">Ctrl</span> + <span class="kbd">V</span> для вставки больших текстов</span>
        </div>

        <div class="row">
          <div class="chip">
            <div style="font-size:12px;color:var(--txt-2);">Вайб</div>
            <select id="vibe">
              <option value="cinematic">Cinematic</option>
              <option value="arcade">Arcade</option>
              <option value="cozy">Cozy</option>
              <option value="neon" selected>Neon</option>
              <option value="retro">Retro</option>
            </select>
          </div>
          <div class="chip">
            <div style="font-size:12px;color:var(--txt-2);">Палитра</div>
            <select id="palette">
              <option value="dark" selected>Темная</option>
              <option value="light">Светлая</option>
              <option value="paper">Бумага</option>
              <option value="vapor">Vaporwave</option>
            </select>
          </div>
          <!-- НОВОЕ: тип игры -->
          <div class="chip">
            <div style="font-size:12px;color:var(--txt-2);">Тип игры</div>
            <select id="gameType">
              <option value="quiz" selected>Квиз</option>
              <option value="dialog">Диалог</option>
              <option value="novel">Новелла</option>
              <option value="platformer">Платформер</option>
              <option value="arcade">Аркада</option>
              <option value="roguelike">Рогалик</option>
            </select>
          </div>
        </div>

        <div class="chip">
          <div class="range-label">
            <span>Сложность дизайна/анимаций</span>
            <span id="difficultyVal">60%</span>
          </div>
          <input id="difficulty" type="range" min="0" max="100" value="60" />
        </div>

        <div class="row">
          <label class="switch chip" style="flex:1">
            <input id="longCode" type="checkbox" checked />
            <span>Длинный код (≈ 1000+ строк)</span>
          </label>
          <label class="switch chip" style="flex:1">
            <input id="withAudio" type="checkbox" />
            <span>Звук/музыка</span>
          </label>
          <label class="switch chip" style="flex:1">
            <input id="procedural" type="checkbox" checked />
            <span>Процедурная генерация</span>
          </label>
        </div>

        <div class="actions">
          <button id="generateBtn" class="btn-primary">Создать игру</button>
          <button id="clearBtn" class="btn-ghost">Очистить</button>
          <button id="sampleBtn" class="btn-ghost">Вставить пример</button>
        </div>
      </div>
      <div class="footer">
        <span>Генерация бережно относится к верстке текста (без «поехавших» блоков)</span>
        <span>v2 — «neon dark»</span>
      </div>
    </section>

    <!-- Right: Preview -->
    <section class="card">
      <h3>Игра</h3>
      <div class="card-body preview-wrap">
        <div class="helper">
          <span class="muted">Результат открывается в окне ниже</span>
          <div class="stat"><b>1:1</b> холст • <span class="muted">Canvas</span></div>
        </div>

        <div class="frame">
          <div id="loader" class="loader">
            <div class="spinner"></div>
            <div id="loaderText">Генерация игры…</div>
          </div>
          <iframe id="gameFrame"></iframe>
        </div>

        <!-- Visible error panel -->
        <div id="errorBox">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
            <b>Ошибка</b>
            <button id="hideErrBtn" class="btn-ghost" style="padding:6px 10px;">Скрыть</button>
          </div>
          <pre id="errorText"></pre>
        </div>

        <div class="row">
          <button id="downloadBtn" class="btn-primary" disabled>Скачать как game.html</button>
          <button id="resetFrameBtn" class="btn-ghost">Сбросить предпросмотр</button>
        </div>
      </div>
    </section>
  </main>

  <script>
    const txt = document.getElementById("bookText");
    const wordCount = document.getElementById("wordCount");
    const loader = document.getElementById("loader");
    const loaderText = document.getElementById("loaderText");
    const frame = document.getElementById("gameFrame");
    const drop = document.getElementById("dropZone");
    const downloadBtn = document.getElementById("downloadBtn");

    const vibe = document.getElementById("vibe");
    const palette = document.getElementById("palette");
    const difficulty = document.getElementById("difficulty");
    const difficultyVal = document.getElementById("difficultyVal");
    const longCode = document.getElementById("longCode");
    const withAudio = document.getElementById("withAudio");
    const procedural = document.getElementById("procedural");
    const gameType = document.getElementById("gameType"); // НОВОЕ

    const generateBtn = document.getElementById("generateBtn");
    const clearBtn = document.getElementById("clearBtn");
    const sampleBtn = document.getElementById("sampleBtn");
    const resetFrameBtn = document.getElementById("resetFrameBtn");

    const errBox = document.getElementById("errorBox");
    const errText = document.getElementById("errorText");
    document.getElementById("hideErrBtn").onclick = () => errBox.style.display = "none";

    function updateWordCount(){
      const words = txt.value.trim().split(/\\s+/).filter(Boolean);
      wordCount.textContent = words.length;
    }
    txt.addEventListener("input", updateWordCount);
    updateWordCount();

    difficulty.addEventListener("input", () => {
      difficultyVal.textContent = difficulty.value + "%";
    });

    // Drag & Drop
    ;["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => {
      e.preventDefault(); e.stopPropagation(); drop.classList.add("dragover");
    }));
    ;["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => {
      e.preventDefault(); e.stopPropagation(); drop.classList.remove("dragover");
    }));
    drop.addEventListener("drop", async (e) => {
      const file = e.dataTransfer.files?.[0];
      if(!file) return;
      if(!/\\.(txt|md|csv|log|rtf)$/i.test(file.name)){ alert("Поддерживаются .txt / .md / .rtf / .csv / .log"); return; }
      const text = await file.text();
      txt.value = text;
      updateWordCount();
    });

    // Управляем одним blob: URL для iframe, чтобы избежать утечек
    let currentBlobUrl = null;
    function setFrameSrcFromHTML(html){
      if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null; }
      const blob = new Blob([html], { type: "text/html" });
      const url = URL.createObjectURL(blob);
      currentBlobUrl = url;
      frame.src = url;
    }

    function showLoader(state, msg){
      loader.classList.toggle("show", state);
      if(msg) loaderText.textContent = msg;
    }

    function saveBlob(filename, content){
      const blob = new Blob([content], {type: "text/html"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    }

    function showError(data){
      const { status, error, details, trace_id, source } = (data || {});
      const parts = [];
      if (error)  parts.push(`Сообщение: ${error}`);
      if (status) parts.push(`HTTP статус: ${status}`);
      if (source) parts.push(`Источник: ${source}`);
      if (trace_id) parts.push(`trace_id: ${trace_id}`);
      if (details) parts.push(`Детали:\\n${(typeof details === 'string' ? details : JSON.stringify(details, null, 2))}`);
      errText.textContent = parts.join('\\n\\n');
      errBox.style.display = "block";
    }

    clearBtn.addEventListener("click", () => {
      txt.value = "";
      updateWordCount();
      if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null; }
      frame.removeAttribute("src");
      downloadBtn.disabled = true;
      errBox.style.display = "none";
    });

    resetFrameBtn.addEventListener("click", () => {
      if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null; }
      frame.removeAttribute("src");
    });

    sampleBtn.addEventListener("click", () => {
      txt.value = "Это отрывок с сильной визуальной метафорой: герой собирает рассыпанные воспоминания, каждое — как светящийся осколок. Когда все осколки собраны, перед ним открывается главная мысль — выбор важнее страха.";
      updateWordCount();
    });

    generateBtn.addEventListener("click", async () => {
      const text = txt.value.trim();
      if(!text){ alert("Вставьте текст из книги!"); return; }

      showLoader(true, "Генерация игры…");
      errBox.style.display = "none";
      downloadBtn.disabled = true;

      try{
        const response = await fetch("/generate", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({
            text,
            vibe: vibe.value,
            palette: palette.value,
            difficulty: Number(difficulty.value),
            long_code: !!longCode.checked,
            audio: !!withAudio.checked,
            procedural: !!procedural.checked,
            game_type: gameType.value
          })
        });

        const raw = await response.text();
        let payload = null;
        try { payload = raw ? JSON.parse(raw) : null; } catch(_){ /* non-JSON */ }

        if(!response.ok){
          showError(payload || { status: response.status, error: response.statusText, details: raw });
          return;
        }

        if(!payload || !payload.code){
          showError({ error: "Успешный ответ без поля code", details: raw });
          return;
        }

        setFrameSrcFromHTML(payload.code);

        // Проверка window.gameMeta в iframe (same-origin для blob:)
        frame.onload = () => {
          try {
            const meta = frame.contentWindow && frame.contentWindow.gameMeta;
            if (!meta) {
              showError({ error: "Проверка результата", details: "window.gameMeta не найден в iframe. Проверь контракт вывода в промпте." });
              return;
            }
            const required = ["hasStop","hasExit","hasHint","endScreen","isSquareCanvas","noExternalDeps"];
            const missing = required.filter(k => !(k in meta));
            const bad = [];
            if (meta.noExternalDeps === false) bad.push("noExternalDeps=false");
            if (missing.length || bad.length) {
              showError({
                error: "Чеклист не выполнен",
                details: "Отсутствуют поля: " + missing.join(", ") + (bad.length? ("\\nНекорректные значения: "+bad.join(", ")):"")
              });
            }
          } catch (e) {
            showError({ error: "Не удалось прочитать gameMeta", details: String(e) });
          }
        };

        downloadBtn.disabled = false;
        downloadBtn.onclick = () => saveBlob("game.html", payload.code);

      }catch(err){
        showError({ error: "Сетевая/JS ошибка на клиенте", details: String(err) });
      }finally{
        showLoader(false);
      }
    });
  </script>
</body>
</html>
"""

def _request_timeout():
    # Если NO_TIMEOUT=1|true|yes — вообще не ставим таймаут (ждём бесконечно)
    flag = str(os.getenv("NO_TIMEOUT", "")).strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return None  # requests будет ждать бесконечно
    # Иначе можно вернуть твои обычные значения (если захочешь)
    # return (10, 300)  # пример: (connect_timeout, read_timeout)
    return None  # по умолчанию тоже без таймаута

# =========================
#  Routes
# =========================
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/generate", methods=["POST"])
def generate_game():
    trace_id = str(uuid.uuid4())[:8]
    data = request.json or {}
    book_text = data.get("text", "") or ""

    if not book_text.strip():
        return jsonify({
            "error": "Текст пустой",
            "hint": "Передай непустой текст в поле text.",
            "trace_id": trace_id
        }), 400

    # Collect options for prompt
    opts = {
        "vibe": data.get("vibe"),
        "palette": data.get("palette"),
        "difficulty": data.get("difficulty"),
        "long_code": data.get("long_code"),
        "audio": data.get("audio"),
        "procedural": data.get("procedural"),
        "game_type": data.get("game_type"),  # НОВОЕ
    }

    prompt = build_prompt(book_text, opts)
    print("Промпт:")
    print(prompt)
    print()

    # Call external model API
    try:
        api_payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "solver"
        }
        r = requests.post(API_URL, headers=HEADERS, json=api_payload, timeout=_request_timeout())
    except requests.exceptions.Timeout as e:
        app.logger.exception("Timeout %s", trace_id)
        return jsonify({
            "error": "Внешний API не ответил вовремя",
            "hint": "Попробуй ещё раз или уменьшай объём текста.",
            "details": redact(str(e)),
            "trace_id": trace_id,
            "source": "external_api"
        }), 504
    except requests.exceptions.RequestException as e:
        app.logger.exception("HTTP error %s", trace_id)
        return jsonify({
            "error": "Ошибка запроса к внешнему API",
            "details": redact(str(e)),
            "trace_id": trace_id,
            "source": "external_api"
        }), 502

    # Non-2xx from upstream — return raw body for visibility
    content_text = r.text
    if not r.ok:
        app.logger.error("Upstream %s status=%s body=%s", trace_id, r.status_code, redact(content_text))
        return jsonify({
            "error": "Внешний API вернул ошибку",
            "status": r.status_code,
            "details": redact(content_text),
            "trace_id": trace_id,
            "source": "external_api"
        }), 502

    # Parse JSON
    try:
        result = r.json()
        game_code = result["choices"][0]["message"]["content"]
        if not game_code or "<html" not in game_code.lower():
            raise ValueError("Ответ не похож на HTML игры")
        print("Код:")
        pprint.pprint(game_code)
        print()
        return jsonify({"code": game_code, "trace_id": trace_id})
    except Exception as e:
        app.logger.exception("Parse error %s", trace_id)
        return jsonify({
            "error": "Не удалось разобрать ответ внешнего API",
            "details": redact(content_text) or redact(str(e)),
            "trace_id": trace_id,
            "source": "parsing"
        }), 500

# =========================
#  Global error handler
# =========================
@app.errorhandler(Exception)
def handle_unexpected(e):
    trace_id = str(uuid.uuid4())[:8]
    app.logger.exception("Unhandled %s", trace_id)
    return jsonify({
        "error": "Внутренняя ошибка сервера",
        "details": redact(str(e)),
        "trace_id": trace_id,
        "source": "backend"
    }), 500

# =========================
#  Entrypoint
# =========================
if __name__ == "__main__":
    # Run dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
