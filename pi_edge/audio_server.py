"""Flask server (port 5001) that plays the collision alarm on the Pi."""
import os
import subprocess
import threading

from flask import Flask, jsonify

ALARM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")

app = Flask(__name__)
_proc = None
_lock = threading.Lock()


@app.route("/play_alarm", methods=["POST"])
def play_alarm():
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            return jsonify(status="already_playing"), 200  # no overlapping audio
        _proc = subprocess.Popen(["aplay", "-q", ALARM])
    return jsonify(status="playing"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
