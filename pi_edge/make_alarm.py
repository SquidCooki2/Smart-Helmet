"""Generates alarm.wav (beeping tone) next to this script."""
import math
import os
import struct
import wave

RATE = 22050
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")
frames = bytearray()
for beep in range(4):
    for i in range(int(RATE * 0.2)):
        v = int(30000 * math.sin(2 * math.pi * 1000 * i / RATE))
        frames += struct.pack("<h", v)
    frames += b"\x00\x00" * int(RATE * 0.1)
with wave.open(out, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(bytes(frames))
print("wrote", out)
