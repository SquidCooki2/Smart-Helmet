"""Flask-SocketIO server that drives the smartphone turn-signal display."""
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
current = {"direction": "off"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/set_signal/<direction>", methods=["POST"])
def set_signal(direction):
    if direction not in ("left", "right", "off"):
        return jsonify(error="direction must be left, right or off"), 400
    current["direction"] = direction
    socketio.emit(f"signal_{direction}")
    return jsonify(status="ok", direction=direction)


@socketio.on("connect")
def on_connect():
    # Sync a newly connected phone with the current state.
    socketio.emit(f"signal_{current['direction']}", to=None)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)
