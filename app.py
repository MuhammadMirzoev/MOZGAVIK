from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

API_URL = "https://approxination.com/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 379f5469-cb64-47ec-bab1-462ee3824c1b"
}

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Генератор игр</title>
  <style>
    body {margin:0;height:100vh;display:flex;font-family:Arial,sans-serif;background:#1e1e1e;color:white;}
    #left,#right{flex:1;display:flex;flex-direction:column;padding:20px;box-sizing:border-box;}
    #left{border-right:2px solid #333;background:#2a2a2a;}
    textarea{flex:1;resize:none;width:100%;background:#111;color:white;border:1px solid #444;border-radius:6px;padding:10px;font-size:14px;}
    button{margin-top:15px;padding:12px;background:#0078ff;border:none;border-radius:6px;color:white;font-size:16px;cursor:pointer;transition:.2s;}
    button:hover{background:#005fcc;}
    iframe{flex:1;border:none;background:white;border-radius:6px;}
    #loading{margin-top:10px;font-size:14px;color:#aaa;display:none;}
  </style>
</head>
<body>
  <div id="left">
    <h2>Текст книги</h2>
    <textarea id="bookText" placeholder="Вставь сюда текст из книги..."></textarea>
    <button id="generateBtn">Создать игру</button>
    <div id="loading">⏳ Генерация игры...</div>
  </div>
  <div id="right">
    <h2>Игра</h2>
    <iframe id="gameFrame"></iframe>
  </div>

  <script>
    document.getElementById("generateBtn").addEventListener("click", async () => {
      const text = document.getElementById("bookText").value.trim();
      if (!text) {
        alert("Вставьте текст из книги!");
        return;
      }

      document.getElementById("loading").style.display = "block";

      try {
        const response = await fetch("/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });

        const result = await response.json();

        if (result.code) {
        const blob = new Blob([result.code], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        document.getElementById("gameFrame").src = url;
        } else {
        console.error("Ошибка генерации:", result);
        alert("Ошибка: " + (result.error || "Неизвестная ошибка") + 
        (result.details ? "\\nДетали: " + result.details : ""));
      }

      } catch (err) {
        alert("Ошибка соединения: " + err.message);
      } finally {
        document.getElementById("loading").style.display = "none";
      }
    });
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/generate", methods=["POST"])
def generate_game():
    data = request.json
    book_text = data.get("text", "")

    if not book_text.strip():
        return jsonify({"error": "Текст пустой"}), 400

    prompt = f"""
Ты — генератор 2D-игр на JavaScript с HTML5 Canvas. 
Я дам тебе текст из книги (главу или отрывок). Твоя задача:

1. Создать интерактивную 2D-игру, которая помогает игроку понять суть текста. 
   - Игровой процесс полностью формируется по контексту текста.
   - Это может быть визуализация идей, мини-игра для запоминания событий, логическая задача, кликер и т.д.
2. В игре должен быть:
   - Какой-то способ взаимодействия (клик, движение объектов, выбор вариантов и т.п.), который отражает текст.
   - Счет или прогресс (например, очки за правильные действия, сбор идей, достижение целей текста).
   - Явный конец игры, после которого игрок понимает ключевую идею или сюжет текста.
3. Код должен быть в чистом JS + HTML + Canvas, чтобы его можно было сохранить как `game.html` и запустить в браузере.
4. Игровой сюжет и механика должны прямо ссылаться на события, идеи или персонажей текста.
5. Комментарии в коде полезны для связи с текстом, но не обязательны.
6. Формат экрана игры должен быть 1 к 1
7. ОБЯЗАТЕЛЬНО Если будет текст, следи чтобы он вмещался в пространство где он должен быть, чтобы все было красиво и дизайн хороший делай
8. Много кода, от 1000 строк кода.
9. Анимации тоже можешь добавлять разные.
10. Звуки тоже можно добавлять
11. В интерфейсе игры обязательно:
    - Счет
    - Кнопка стоп
    - Кнопка выхода
    - Подсказки
    - В окне завершения игры окончательный счет и кнопка нажать заново
    - Остальное относительно контекста
12. Если в игре нужно собирать какие либо объекты то убедись что игрок сможет до них добраться. Также
13. Если можно добавить процедурную генерацию уровней, то добавь, по контексту крч

__________________________________________________________________

{book_text}

__________________________________________________________________

Сделай игру, которая помогает понять этот текст.

Верни мне чистый код html без ничего лишнего
"""

    response = requests.post(API_URL, headers=HEADERS, json={
        "messages": [{"role": "user", "content": prompt}],
        "model": "solver"
    })

    try:
        result = response.json()
        game_code = result["choices"][0]["message"]["content"]
        return jsonify({"code": game_code})
    except Exception:
        return jsonify({"error": "Ошибка генерации", "details": response.text}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
