import os
import sys
import json
import time
import base64
import argparse
import subprocess
import traceback
from datetime import datetime

# Import existing core modules (assuming dependencies are installed in the environment)
try:
    import cv2
    import numpy as np
    import pyautogui
    # macOS Native
    import Quartz
    import Vision
    from Cocoa import NSURL
    from Foundation import NSDictionary
    # YOLO for UI Detection
    from ultralytics import YOLO
except ImportError as e:
    # Safe fallback if dependencies are missing (except critical ones)
    sys.stderr.write(f"Warning: Missing dependency: {e}\n")
    if "ultralytics" in str(e):
        sys.stderr.write("YOLO features will be disabled.\n")

# Optional LLM Imports (Lazy Loaded)
genai = None
types = None
OpenAI = None

# ==========================================
# Configuration & Constants (Loaded from Env)
# ==========================================
SCREENSHOT_DIR = os.path.join(os.path.expanduser("~"), ".openclaw", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# YOLO model: resolve from script dir -> openclaw root (where package.json lives)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OPENCLAW_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
YOLO_MODEL_PATH = os.path.join(_OPENCLAW_ROOT, "ui-elements-detection.pt")

# ==========================================
#  Core Classes (Refactored from VisionAgentPro)
# ==========================================

class LocalPerception:
    """
    Handles Screen Capture, OCR, Icon Matching, YOLO Detection, and Low-Level Actions.
    """
    def __init__(self):
        self.speech_enabled = False # Disable TTS for backend service
        self.yolo_model = None
        self._load_yolo()

    def _load_yolo(self):
        """Loads the YOLO model if available."""
        if os.path.exists(YOLO_MODEL_PATH):
            try:
                self.log(f"Loading YOLO model from {YOLO_MODEL_PATH}...")
                self.yolo_model = YOLO(YOLO_MODEL_PATH)
                self.log("YOLO model loaded successfully.")
            except Exception as e:
                self.log(f"Failed to load YOLO model: {e}", "error")
        else:
            self.log(f"YOLO model not found at {YOLO_MODEL_PATH}. UI detection disabled.", "warn")

    def capture_screen(self, filename="screenshot.png"):
        """Captures full screen to a file."""
        path = os.path.join(SCREENSHOT_DIR, filename)
        subprocess.run(["/usr/sbin/screencapture", "-x", path], check=True)
        return path

    def detect_ui_elements(self, image_path):
        """
        Runs YOLO inference to detect UI elements.
        Returns: list of dicts with {id, label, confidence, box, center}
        """
        if not self.yolo_model:
            return []

        try:
            results = self.yolo_model(image_path, verbose=False)
            elements = []
            
            # Process results (usually only 1 result for 1 image)
            for r in results:
                for idx, box in enumerate(r.boxes):
                    cls_id = int(box.cls)
                    label = self.yolo_model.names[cls_id]
                    conf = float(box.conf)
                    xyxy = box.xyxy.tolist()[0]
                    
                    # Calculate center point
                    x1, y1, x2, y2 = xyxy
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    elements.append({
                        "id": idx + 1,
                        "label": label,
                        "confidence": conf,
                        "center": (center_x, center_y),
                        "box": [round(c) for c in xyxy]
                    })
            
            return elements
        except Exception as e:
            self.log(f"YOLO Detection Error: {e}", "error")
            return []

    def recognize_text(self, image_path):
        """
        Uses macOS Native Vision Framework for OCR.
        Returns: String of all text found.
        """
        try:
            input_url = NSURL.fileURLWithPath_(image_path)
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
            request.setUsesLanguageCorrection_(True)
            request.setRecognitionLanguages_(["zh-Hans", "en-US"])
    
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(input_url, NSDictionary.dictionary())
            
            handler.performRequests_error_([request], None)
            observations = request.results()
            full_text = []
            for observation in observations:
                candidates = observation.topCandidates_(1)
                if candidates:
                    full_text.append(candidates[0].string())
            return "\n".join(full_text)
        except Exception as e:
            self.log(f"OCR Error: {e}", "error")
            return ""

    def click(self, x, y, double=False):
        """
        Uses PyAutoGUI for mouse control.
        """
        # Move OS mouse (Quartz event for reliability)
        subprocess.run(["/usr/bin/osascript", "-e", f'tell application "System Events" to click at {{{x},{y}}}'], check=False)

    def type_text(self, text):
        """
        Clipboard Paste (Cmd+V) to support CJK input reliably.
        """
        try:
            p = subprocess.Popen(['/usr/bin/pbcopy'], stdin=subprocess.PIPE, encoding='utf8')
            p.communicate(input=text)
            time.sleep(0.1)
            # Cmd+V
            script = 'tell application "System Events" to keystroke "v" using command down'
            subprocess.run(["/usr/bin/osascript", "-e", script], check=False)
            # Press Return immediately after typing if it's a message
            # logic removed, let LLM decide to press return separately or combine actions
        except Exception as e:
            self.log(f"Paste Error: {e}", "error")

    def press_key(self, key_code, modifiers=[]):
        """
        Press a specific key code.
        """
        mod_str = ""
        if modifiers:
            mod_str = " using {" + ",".join([m + " down" for m in modifiers]) + "}"
        
        script = f'tell application "System Events" to key code {key_code}{mod_str}'
        subprocess.run(["/usr/bin/osascript", "-e", script], check=False)

    def launch_app(self, app_name):
        """
        Robustly launch an application by name.
        """
        MAPPING = {
            "飞书": ["Lark", "Feishu", "飞书"],
            "feishu": ["Lark", "Feishu", "飞书"],
            "lark": ["Lark", "Feishu"],
            "wps": ["wpsoffice", "WPS Office", "wps"],
            "wps office": ["wpsoffice", "WPS Office"],
            "wechat": ["WeChat", "微信"],
            "微信": ["WeChat", "微信"],
            "chrome": ["Google Chrome", "Chrome"],
            "safari": ["Safari"],
            "finder": ["Finder"],
            "calculator": ["Calculator", "计算器"],
            "计算器": ["Calculator"],
        }
        
        candidates = MAPPING.get(app_name.lower(), [app_name])
        
        for name in candidates:
            try:
                subprocess.run(["/usr/bin/open", "-a", name], check=True, capture_output=True)
                self.log(f"Launched app: {name}")
                time.sleep(2) # Wait for app to focus
                return True
            except subprocess.CalledProcessError:
                continue
                
        self.log(f"Failed to launch app: {app_name}", "warn")
        return False

    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"[{timestamp}] [{level.upper()}] {message}\n")
        sys.stderr.flush()

class VisionExecutor:
    """
    High-level logic that coordinates Perception and Actions.
    """
    def __init__(self, provider="openai", api_key=None, base_url=None, model=None):
        self.perception = LocalPerception()
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = None
        self._init_client()

    def _init_client(self):
        global genai, types, OpenAI
        
        if self.provider == "google":
             try:
                 from google import genai
                 from google.genai import types
             except ImportError:
                 self.perception.log("Missing properties: pip install google-generativeai", "error")
                 return

             self.client = genai.Client(api_key=self.api_key)
        else:
            # Assume OpenAI Compatible (302.AI, etc.)
            try:
                from openai import OpenAI
            except ImportError:
                self.perception.log("Missing dependency: pip install openai", "error")
                return

            self.client = OpenAI(
                api_key=self.api_key.strip(), 
                base_url=self.base_url.strip(),
                default_headers={"Authorization": f"Bearer {self.api_key.strip()}"}
            )

    def plan_next_step(self, task, screen_text, ui_elements, steps_taken=None):
        """
        Uses LLM to decide the next UI action, incorporating YOLO detections.
        """
        if not self.api_key:
             return {"action": "fail", "reason": "No API Key provided"}

        steps_taken = steps_taken or []

        # Format UI Elements for LLM
        ui_list_str = ""
        if ui_elements:
            ui_list_str = "Detected Interactive Elements (Use ID to Click):\n"
            for el in ui_elements:
                ui_list_str += f"- ID {el['id']}: {el['label']} (Conf: {el['confidence']:.2f})\n"
        else:
            ui_list_str = "No UI elements detected via YOLO (Rely on OCR text or app launch).\n"

        # Build history and anti-loop hint
        history_str = ""
        anti_loop_hint = ""
        if steps_taken:
            recent = [s.get("action") for s in steps_taken[-5:]]
            history_str = "Recent actions taken: " + ", ".join(str(a) for a in recent) + "\n"
            # Detect repeated action (same action 2+ times in last 3 steps)
            if len(recent) >= 2 and recent[-1] == recent[-2]:
                last_action = recent[-1]
                if last_action == "launch":
                    last_app = steps_taken[-1].get("app", "")
                    anti_loop_hint = f"CRITICAL: You already launched '{last_app}' twice. It is OPEN. Do NOT launch again. Proceed to the NEXT step: type text, click buttons, or use done if task complete.\n"
                elif last_action == "key_press":
                    anti_loop_hint = "CRITICAL: You already pressed the same key twice. The UI (e.g. Spotlight) is likely OPEN. Do NOT repeat key_press. Type the search text, then press Enter, or click elements.\n"
                else:
                    anti_loop_hint = f"WARNING: You repeated '{last_action}' twice. Try a DIFFERENT action - type, click, or done.\n"

        prompt = f"""
        You are a GUI Automation Agent on macOS.
        Current Task: "{task}"
        
        {history_str}{anti_loop_hint}
        Screen Context (OCR Text):
        {screen_text[:800]}... (truncated)

        {ui_list_str}

        Decide the next IMMEDIATE action. Return ONLY valid JSON.
        
        CRITICAL RULES:
        - If app is already open (you launched it recently): do NOT launch again. Proceed to type or click.
        - If Spotlight/search is open: type the search term, then key_press return.
        - If same action appears in recent history: choose a DIFFERENT action.
        - When task is complete: use {{"action": "done"}}
        
        Tips:
        - **Launch App**: Only if the app is NOT visible yet. Once launched, move to type/click.
        - **Click Element**: Use `{{"action": "click_element", "id": 123}}` for YOLO-detected elements. PREFERRED.
        - **Type**: Use `{{"action": "type", "text": "..."}}` for search boxes, calculator input, etc.
        - **Key_press**: Use for return, enter, escape. For Cmd+Space open Spotlight, do it ONCE then type.
        
        Actions:
        - {{"action": "launch", "app": "Calculator"}}
        - {{"action": "click_element", "id": 5}}
        - {{"action": "type", "text": "Calculator"}}
        - {{"action": "key_press", "key": "return"}}
        - {{"action": "done"}}
        - {{"action": "fail", "reason": "..."}}
        """
        
        try:
            if self.provider == "google":
                 response = self.client.models.generate_content(
                    model=self.model or "gemini-2.0-flash", 
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                 return json.loads(response.text)
            else:
                 response = self.client.chat.completions.create(
                     model=self.model or "gpt-4o",
                     messages=[{"role": "user", "content": prompt}],
                     response_format={"type": "json_object"}
                 )
                 return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.perception.log(f"LLM Error: {e}", "error")
            return {"action": "fail", "reason": str(e)}

    def execute(self, task_description, max_steps=10):
        self.perception.log(f"Starting Task: {task_description}")
        
        steps_taken = []
        
        for i in range(max_steps):
            screenshot = self.perception.capture_screen(f"step_{i}.png")
            
            # Run Perception (Parallel-ish)
            text = self.perception.recognize_text(screenshot)
            ui_elements = self.perception.detect_ui_elements(screenshot)
            
            self.perception.log(f"Step {i+1} Perception: Found {len(ui_elements)} UI elements, {len(text)} chars of text.")
            
            plan = self.plan_next_step(task_description, text, ui_elements, steps_taken)
            
            action = plan.get("action")
            steps_taken.append(plan)
            
            # Hard anti-loop: if same action 3+ times in a row, force done to break loop
            recent_actions = [s.get("action") for s in steps_taken[-4:]]
            if len(recent_actions) >= 3 and len(set(recent_actions)) == 1:
                self.perception.log(f"Loop detected: '{recent_actions[0]}' repeated 3+ times. Forcing done.", "warn")
                return {"status": "timeout", "error": f"Loop detected: repeated {recent_actions[0]}", "steps": steps_taken}
            
            self.perception.log(f"Step {i+1} Action: {action} -> {json.dumps(plan)}")
            
            if action == "done":
                return {"status": "success", "steps": steps_taken}
            elif action == "fail":
                return {"status": "error", "error": plan.get("reason"), "steps": steps_taken}
            elif action == "launch":
                app_name = plan.get("app", "")
                self.perception.launch_app(app_name)
            elif action == "click_element":
                el_id = plan.get("id")
                target = next((e for e in ui_elements if e["id"] == el_id), None)
                if target:
                    cx, cy = target["center"]
                    self.perception.log(f"Clicking Element {el_id} ({target['label']}) at ({cx}, {cy})")
                    self.perception.click(cx, cy)
                else:
                    self.perception.log(f"Element ID {el_id} not found in current frame.", "warn")
            elif action == "click_text":
                # Basic text search implementation (placeholder for bounding box search)
                # In real scenario, we need text bounding boxes from Vision framework.
                # For now, we fallback to a simpler text prompt or assume center if not implemented
                self.perception.log("click_text not fully implemented with coordinates, skipping click.", "warn")
            elif action == "type":
                self.perception.type_text(plan.get("text", ""))
            elif action == "key_press":
                key_input = plan.get("key", "").lower()
                modifiers = []
                key_main = key_input
                
                if "+" in key_input:
                    parts = key_input.split("+")
                    key_main = parts[-1]
                    modifiers = parts[:-1]
                
                key_map = {"return": 36, "enter": 76, "space": 49, "tab": 48, "escape": 53, "delete": 51}
                code = key_map.get(key_main, 36)
                self.perception.press_key(code, modifiers=modifiers)
            
            time.sleep(2)

        return {"status": "timeout", "steps": steps_taken}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--max-steps", type=int, default=10, help="Max steps (default 10)")
    parser.add_argument("--provider", default="openai", help="LLM Provider")
    parser.add_argument("--api-key", default=os.environ.get("OPENCLAW_API_KEY"), help="API Key")
    parser.add_argument("--base-url", default=os.environ.get("OPENCLAW_BASE_URL"), help="Base URL")
    parser.add_argument("--model", default=os.environ.get("OPENCLAW_MODEL"), help="Model ID")
    
    args = parser.parse_args()
    
    executor = VisionExecutor(
        provider=args.provider,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model
    )
    
    try:
        result = executor.execute(args.task, max_steps=args.max_steps)
        print(json.dumps(result))
    except Exception as e:
        traceback.print_exc()
        print(json.dumps({"status": "fatal_error", "error": str(e)}))

if __name__ == "__main__":
    main()
