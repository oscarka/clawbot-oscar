import sys
import os
import subprocess
import requests
from ultralytics import YOLO

# Model URL and Path
MODEL_URL = "https://huggingface.co/macpaw-research/yolov11l-ui-elements-detection/resolve/main/ui-elements-detection.pt"
MODEL_PATH = "ui-elements-detection.pt"

def download_model():
    if not os.path.exists(MODEL_PATH):
        print(f"Downloading model to {MODEL_PATH}...")
        response = requests.get(MODEL_URL, stream=True)
        response.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
    else:
        print(f"Model found at {MODEL_PATH}")

def run_test():
    # 1. Download Model
    download_model()

    # 2. Capture Screen
    screen_path = "test_screen.png"
    print("Capturing screen...")
    subprocess.run(["/usr/sbin/screencapture", "-x", screen_path], check=True)
    print(f"Screen saved to {screen_path}")

    # 3. Load Model & Predict
    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    
    print("Running inference...")
    results = model(screen_path)

    # 4. Save and Show Results
    annotated_path = "test_screen_annotated.jpg"
    for r in results:
        r.save(annotated_path)  # save to check
        print(f"\n--- Detection Results ---")
        print(f"Saved annotated image to: {os.path.abspath(annotated_path)}")
        print(f"Found {len(r.boxes)} elements:")
        for idx, box in enumerate(r.boxes):
            cls_id = int(box.cls)
            cls_name = model.names[cls_id]
            conf = float(box.conf)
            xyxy = box.xyxy.tolist()[0]
            print(f"[{idx+1}] {cls_name} (Conf: {conf:.2f}) -> Box: {xyxy}")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Error: {e}")
