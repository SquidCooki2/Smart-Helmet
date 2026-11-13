"""Downloads model weights into laptop_vision/models/.

- pothole.pt  <- huggingface.co/cazzz307/Pothole-Finetuned-YoloV8 (Yolov8-fintuned-on-potholes.pt)
- yolov8n.pt  <- Ultralytics (auto-download)
"""
import os
import shutil

from huggingface_hub import hf_hub_download

MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODELS, exist_ok=True)

dst = os.path.join(MODELS, "pothole.pt")
if not os.path.exists(dst):
    try:
        src = hf_hub_download("cazzz307/Pothole-Finetuned-YoloV8", "Yolov8-fintuned-on-potholes.pt")
        shutil.copy(src, dst)
    except Exception as e:  # the repo is gated: needs an HF account with granted access
        print("\nCould not download pothole.pt:", type(e).__name__)
        print("This repo is gated. Request access at https://huggingface.co/cazzz307/Pothole-Finetuned-YoloV8,")
        print("then run `huggingface-cli login` (or set HF_TOKEN) and re-run this script,")
        print("or download the file manually and save it as", dst, "\n")
if os.path.exists(dst):
    print("pothole.pt ready:", dst)

base = os.path.join(MODELS, "yolov8n.pt")
if not os.path.exists(base):
    from ultralytics import YOLO
    YOLO("yolov8n.pt")  # downloads to CWD
    if os.path.exists("yolov8n.pt"):
        shutil.move("yolov8n.pt", base)
print("yolov8n.pt ready:", base)
