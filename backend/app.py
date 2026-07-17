import os
from flask import Flask, render_template, make_response
from flask_socketio import SocketIO

from backend.sockets.handlers import registrar_handlers

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-de-desarrollo-solo-local")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
registrar_handlers(socketio)


@app.route("/")
def index():
    # Nunca guardar esta página en caché: así el navegador SIEMPRE vuelve a pedir
    # el HTML al servidor, y con él, la versión más reciente de CSS/JS.
    respuesta = make_response(render_template("index.html"))
    respuesta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return respuesta


if __name__ == "__main__":
    # Uso LOCAL (py -m backend.app): host="0.0.0.0" para la red WiFi de la casa
    puerto = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=puerto, debug=True, allow_unsafe_werkzeug=True)
