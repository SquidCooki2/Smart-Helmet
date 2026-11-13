"""Central configuration. Override via environment variables where noted."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PI_IP = os.environ.get("PI_IP", "192.168.1.50")
PI_CAMERA_PORT = int(os.environ.get("PI_CAMERA_PORT", 5000))
PI_AUDIO_PORT = int(os.environ.get("PI_AUDIO_PORT", 5001))
DISPLAY_PORT = int(os.environ.get("DISPLAY_PORT", 8080))

MODEL_DIR = os.path.join(BASE_DIR, "models")
POTHOLE_CONF = 0.60
ARM_FRAMES = 10                # consecutive frames arm must be extended
ARM_MARGIN = 0.15              # min horizontal wrist-shoulder distance (normalized)
ARM_HEIGHT_TOL = 0.15          # max vertical wrist-shoulder offset (normalized)
GROWTH_THRESHOLD = 1.30        # >30% area growth
GROWTH_WINDOW = 1.0            # seconds
ALARM_COOLDOWN = 5.0           # seconds
VEHICLE_CLASSES = {2, 5, 7}    # COCO: car, bus, truck
FRAME_SIZE = (640, 480)
YOLO_DEVICE = os.environ.get("YOLO_DEVICE", None)  # e.g. "cuda:0"; None = auto
POTHOLE_EVERY_N = 2            # run pothole model every N frames
