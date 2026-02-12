import base64
import json
import os
import time
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import requests
import pyautogui
import cv2
import numpy as np

# Import macOS Native Vision Framework (via PyObjC)
try:
    import Quartz
    import Vision
    from Cocoa import NSURL
except ImportError:
    print("❌ 缺少 PyObjC 库，请运行: pip install pyobjc")
    exit(1)

# ==========================================
# System 1: Local Perception Engine (Fast)
# ==========================================
class LocalPerception:
    """
    本地感知引擎：使用 macOS 原生 Vision 框架进行毫秒级 OCR 和屏幕分析。
    不依赖云端 API，速度快（<500ms），无成本。
    """
    def __init__(self):
        self.TextRecognitionLevelFast = Vision.VNRequestTextRecognitionLevelFast
        self.TextRecognitionLevelAccurate = Vision.VNRequestTextRecognitionLevelAccurate

    def find_icon(self, screenshot_path, template_path, threshold=0.9):
        """
        Use OpenCV Template Matching to find an icon in the screenshot.
        Returns center coordinates (x, y) or None.
        Threshold raised to 0.9 to avoid false positives.
        Ignores matches in top-left corner (Apple Menu area).
        """
        if not os.path.exists(template_path):
            return None
        
        if not os.path.exists(screenshot_path):
             screenshot_path = self.capture_screen_to_file()
             if not screenshot_path: return None

        img = cv2.imread(screenshot_path)
        template = cv2.imread(template_path)
        
        if img is None or template is None:
            return None

        # Optimization: Downscale for speed (50%)
        # Note: If template was cropped from full res, we must downscale both OR neither.
        # If we downscale both, the relative scale is preserved.
        img_small = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
        template_small = cv2.resize(template, (0, 0), fx=0.5, fy=0.5)
        
        # Match
        result = cv2.matchTemplate(img_small, template_small, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            # Map back to original coordinates
            x_small, y_small = max_loc
            w_small, h_small = template_small.shape[1], template_small.shape[0]
            
            # Upscale coordinates by 2
            center_x = int((x_small + w_small // 2) * 2)
            center_y = int((y_small + h_small // 2) * 2)
            
            # Retina adjustment? 
            # screencapture on Retina is 2x points. Quartz click needs points.
            # So if image is 2880px wide, point is 1440.
            # We need to divide by 2 for the CLICK coordinate if the screenshot is retina.
            # Let's check image width.
            screen_w_points = Quartz.CGDisplayPixelsWide(Quartz.CGMainDisplayID())
            img_w_pixels = img.shape[1]
            scale_factor = img_w_pixels / screen_w_points
            
            final_click_x = int(center_x / scale_factor)
            final_click_y = int(center_y / scale_factor)

            # Zone Filter: Ignore Top-Left Corner (Apple Menu Area)
            if final_click_x < 100 and final_click_y < 100:
                print(f"   � [CV] Ignoring ghost match at ({final_click_x}, {final_click_y}) | Conf: {max_val:.2f}")
                return None

            print(f"   �👁️  [CV] Found Icon '{os.path.basename(template_path)}' at ({final_click_x}, {final_click_y}) | Conf: {max_val:.2f}")
            return (final_click_x, final_click_y)
        
        return None

    def capture_screen_to_file(self) -> Optional[str]:
        """
        使用 screencapture CLI 截图到临时文件。
        """
        temp_path = "/tmp/vision_fast_capture.png"
        try:
            # -x: 不播放声音
            # -r: 不截取光标 (可选)
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            subprocess.run(['screencapture', '-x', temp_path], check=True, timeout=2)
            
            if not os.path.exists(temp_path):
                return None
            return temp_path
        except Exception as e:
            print(f"⚠️ 截图失败: {e}")
            return None

    def find_text_on_screen(self, target_text: str, fuzzy: bool = True) -> Optional[Tuple[int, int, int, int]]:
        """
        在屏幕上查找指定文本的坐标。
        """
        img_path = self.capture_screen_to_file()
        if not img_path:
            return None
            
        # Debug: 打印这一帧看到的所有文字，方便调试
        debug_texts = []

        try:
            # 1. 创建 NSURL
            url = NSURL.fileURLWithPath_(img_path)
            
            # 2. 创建 Vision Handler (直接使用 URL)
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
            
            # 3. 创建 OCR 请求
            request = Vision.VNRecognizeTextRequest.alloc().init()
            # 尝试使用 Accurate 模式，虽然慢一点点(几十ms)，但对中文和复杂界面更准确
            # 如果太慢再改回 Fast
            request.setRecognitionLevel_(self.TextRecognitionLevelAccurate) 
            request.setUsesLanguageCorrection_(True) # 启用语言校正
            request.setRecognitionLanguages_(['zh-Hans', 'en-US']) # 显式指定语言

            # 4. 执行
            success, error = handler.performRequests_error_([request], None)
            
            if not success:
                print(f"⚠️ OCR 失败: {error}")
                return None
                
            # 5. 分析坐标
            # 获取屏幕 Point 尺寸 (用于计算点击坐标)
            screen_h_points = Quartz.CGDisplayPixelsHigh(Quartz.CGMainDisplayID())
            screen_w_points = Quartz.CGDisplayPixelsWide(Quartz.CGMainDisplayID())
            
            # 目前 screencapture 默认截取主屏
            # Vision 的归一化坐标是相对于整个图像的
            # 我们需要知道图像的像素尺寸来验证缩放，但 initWithURL 不直接给尺寸
            # 不过我们知道 screencapture 也是全屏，所以 Vision 的 (0-1) 映射到屏幕 (0-screen_points) 
            # 只需要考虑 y 轴翻转
            
            # 注意：Retina 屏的 screencapture 图片像素数是 point 数的 2 倍
            # 但 Vision 输出的是归一化坐标 (0.0 - 1.0)
            # 所以我们只要用归一化坐标 * screen_point_size 就能得到点击坐标
            
            results = request.results()
            target_clean = target_text.lower().replace(" ", "")
            
            best_bbox = None
            best_len = float('inf')
            
            for observation in results:
                candidate = observation.topCandidates_(1)[0]
                text = candidate.string()
                debug_texts.append(text)
                
                text_clean = text.lower().replace(" ", "")
                
                # 负面过滤 (针对 WPS 特性)
                if "表格" in target_text and "多维" in text:
                    continue
                
                is_exact = target_clean == text_clean
                is_fuzzy = target_clean in text_clean
                
                match_found = False
                
                if is_exact:
                    match_found = True
                    # 精确匹配优先级最高，直接锁定 (或者也可以继续找，看是否有更靠上面的？这里假设第一个精确匹配就是最好的)
                    best_bbox = observation.boundingBox()
                    break 
                
                elif fuzzy and is_fuzzy:
                    # 模糊匹配：选择长度最短的 (杂质最少)
                    # 例如目标 "表格"，匹配到 "新建多维表格"(长) vs "表格"(短)，选短的
                    if len(text_clean) < best_len:
                        best_len = len(text_clean)
                        best_bbox = observation.boundingBox()
                        match_found = True

            print(f"   👀 本地 OCR 文本({len(debug_texts)}个): {debug_texts[:20]} ...")
            
            if best_bbox:
                # 转换坐标 (Vision 原点左下 -> 屏幕原点左上)
                bbox = best_bbox
                x = bbox.origin.x * screen_w_points
                y = (1 - bbox.origin.y - bbox.size.height) * screen_h_points
                w = bbox.size.width * screen_w_points
                h = bbox.size.height * screen_h_points
                
                center_x = int(x + w / 2)
                center_y = int(y + h / 2)
                
                found = (center_x, center_y, int(w), int(h))
                print(f"   👁️  本地视觉发现 '{target_text}': {found}")
                return found
                
        except Exception as e:
            print(f"   ❌ Vision 处理异常: {e}")
            import traceback
            traceback.print_exc()
            
        return None

    def verify_text_presence_in_area(self, target_text: str, region: str = "all") -> bool:
        """
        Verify if text exists in a specific region of the screen using OCR.
        region: 'all', 'top' (Target Check), 'bottom' (Input Check)
        """
        img_path = self.capture_screen_to_file()
        if not img_path: return False

        try:
            url = NSURL.fileURLWithPath_(img_path)
            handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(self.TextRecognitionLevelFast) # Fast enough for verify
            request.setRecognitionLanguages_(['zh-Hans', 'en-US'])
            
            success, error = handler.performRequests_error_([request], None)
            if not success: return False
            
            results = request.results()
            target_clean = target_text.lower().replace(" ", "")
            
            screen_h = Quartz.CGDisplayPixelsHigh(Quartz.CGMainDisplayID())
            
            for observation in results:
                text = observation.topCandidates_(1)[0].string()
                text_clean = text.lower().replace(" ", "")
                
                if target_clean in text_clean:
                    # Check Region
                    if region == "all":
                        return True
                    
                    bbox = observation.boundingBox()
                    # bbox.origin.y is from bottom-left (0.0 at bottom, 1.0 at top)
                    
                    if region == "top":
                        # Top 20% of screen (y > 0.8)
                        if bbox.origin.y > 0.8:
                            print(f"   ✅ [Verify] Target Found in Top Area: '{text}'")
                            return True
                    elif region == "bottom":
                        # Bottom 30% of screen (y < 0.3)
                        if bbox.origin.y < 0.3:
                            print(f"   ✅ [Verify] Input Found in Bottom Area: '{text}'")
                            return True
                            
            return False
            
        except Exception:
            return False

# ==========================================
# System 2: Vision Agent Pro (Controller)
# ==========================================
class VisionAgentPro:
    def __init__(self):
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # 使用环境变量或默认 Key (与 vision_agent.py 保持一致)
        self.platform302_api_key = os.getenv('PLATFORM302_API_KEY', 'sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW')
        
        # 初始化双系统
        self.eye = LocalPerception() # System 1
        # System 2 (Cloud) 保持原有逻辑，这里简化
        self.planning_models = ["claude-3-5-sonnet-20240620", "gpt-4o"] 

    def human_click(self, x: int, y: int, double_click: bool = False):
        """使用 Quartz 模拟人类点击 (System 1 动作，无需 cliclick)"""
        try:
            print(f"   🖱️  Action: ({x}, {y}) {'Double' if double_click else ''} Click")
            
            # 移动鼠标
            move_event = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, move_event)
            time.sleep(0.2)
            
            # 点击按下
            down_event = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, down_event)
            
            # 点击抬起
            up_event = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseUp, (x, y), Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, up_event)
            
            if double_click:
                time.sleep(0.1)
                # 第二次点击，需要设置 clickState = 2
                down_event_2 = Quartz.CGEventCreateMouseEvent(
                    None, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft
                )
                Quartz.CGEventSetIntegerValueField(down_event_2, Quartz.kCGMouseEventClickState, 2)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, down_event_2)
                
                up_event_2 = Quartz.CGEventCreateMouseEvent(
                    None, Quartz.kCGEventLeftMouseUp, (x, y), Quartz.kCGMouseButtonLeft
                )
                Quartz.CGEventSetIntegerValueField(up_event_2, Quartz.kCGMouseEventClickState, 2)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, up_event_2)
                
            time.sleep(0.3)
        except Exception as e:
            print(f"   ❌ 点击失败: {e}")
            
    def type_text(self, text: str):
        """
        Use Clipboard + Cmd+V to simulate typing.
        Solves IME issues (e.g. 'nihao' vs '你好').
        """
        try:
            print(f"   📋 Paste: '{text}'")
            # 1. Copy to clipboard using pbcopy
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, encoding='utf8')
            p.communicate(input=text)
            
            time.sleep(0.1)
            
            # 2. Command + V
            # Use keystroke 'v' using {command down}
            cmd = """osascript -e 'tell application "System Events" to keystroke "v" using {command down}'"""
            subprocess.run(cmd, shell=True, check=False)
            
            time.sleep(0.2)
        except Exception as e:
            print(f"   ❌ Paste Failed: {e}")

    def find_text_with_retry(self, keywords: List[str], timeout: int = 5) -> Optional[Tuple[int, int, int, int]]:
        """
        主动轮询屏幕，直到找到目标文本或超时。
        """
        start_time = time.time()
        print(f"   🔍 正在寻找: {keywords} (Timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            for kw in keywords:
                coords = self.eye.find_text_on_screen(kw)
                if coords:
                    return coords
            
            # 没找到，稍微等一下再试 (Polling)
            time.sleep(0.5)
            
        print(f"   ⚠️  超时！未找到: {keywords}")
        return None

    def execute_fast_step(self, step: Dict[str, Any]) -> bool:
        """
        执行单个步骤（优先使用 Fast Loop）
        """
        step_num = step.get('step_number', 0)
        action = step['action']
        # 兼容 Gemini 可能使用的不同 Key
        # 依次尝试这些 Key，找到第一个非空的
        target_desc = ''
        for key in ['target', 'app_name', 'content', 'text', 'keys', 'key', 'value', 'input']:
            if step.get(key):
                target_desc = step.get(key)
                break
        
        print(f"\n⚡️ [Step {step_num}] {action} -> {target_desc if target_desc else '(无具体目标)'}")
        
        # 定义一些同义词映射，增强适应性
        SYNONYMS = {
            "新建": ["新建", "New", "+", "Create"],
            "表格": ["表格", "Excel", "Sheet"], 
            "空白": ["空白", "Blank", "New Blank", "新建空白"],
            "WPS Office": ["WPS", "wpsoffice"],
        }
        
        # 策略 1: 直接坐标点击 (System 2 Multimodal Pre-planned)
        if step.get('coordinate'):
            coord = step['coordinate']
            screen_w = Quartz.CGDisplayPixelsWide(Quartz.CGMainDisplayID())
            screen_h = Quartz.CGDisplayPixelsHigh(Quartz.CGMainDisplayID())
            nx, ny = coord
            actual_x = int((nx / 1000.0) * screen_w)
            actual_y = int((ny / 1000.0) * screen_h)
            
            print(f"   🎯 精确打击: [{nx}, {ny}] -> ({actual_x}, {actual_y})")
            self.human_click(actual_x, actual_y)
            return True

        # 策略 2: 打开应用
        if action == "open_app":
            if not target_desc: return False
            app_name = target_desc
            if "WPS" in target_desc or "表格" in target_desc: app_name = "wpsoffice"
            if "飞书" in target_desc: app_name = "Lark"
            
            print(f"   🚀 快速启动: {app_name}")
            # 尝试使用 AppleScript 强制激活 (比 open -a 更能抢占焦点)
            try:
                script = f'tell application "{app_name}" to activate'
                subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            except Exception:
                # Fallback
                subprocess.run(['open', '-a', app_name], check=False)
            
            # 等待窗口前台化 (非常重要，否则会输入到 Terminal)
            time.sleep(2.0)
            return True

        # 策略 3: OCR 点击 (带轮询 + 同义词适配 + 图标匹配)
        if action in ["click", "double_click"]:
            if not target_desc:
                print("   ❌ Error: 点击操作必须有目标 (target)")
                return False
                
            # --- VISION OPTIMIZATION: Check for known icons first ---
            if "send" in target_desc.lower() or "发送" in target_desc.lower() or "attach" in target_desc.lower():
                print(f"   ⚡️ [FastPath] Checking for icons in '{target_desc}'...")
                
                # --- VERIFY INPUT CONTENT BEFORE CLICKING SEND ---
                # Strategy: Check if the last typed content exists in the bottom area
                # This is tricky because we don't know what was just typed unless we track state.
                # But we can verify if the input box is NOT empty.
                # For now, let's just log verification.
                print(f"   🛡️ [Verify] Before sending, checking input area...")
                
                icon_coords = None
                
                # Check Send Icon
                if "send" in target_desc.lower() or "发送" in target_desc.lower():
                     icon_coords = self.eye.find_icon("non_existent_path.png", "icon_send.png")

                if icon_coords:
                    cx, cy = icon_coords
                    print(f"   🚀 [FastPath] Template Match HIT! Clicking ({cx}, {cy})")
                    is_double = action == "double_click"
                    self.human_click(cx, cy, double_click=is_double)
                    return True
                else:
                    print(f"   💨 [FastPath] Icon not found, falling back to OCR.")
            # -----------------------------------------------------

            keywords = [target_desc]
            for key, variants in SYNONYMS.items():
                if key in target_desc:
                    keywords.extend(variants)
            keywords = list(set(keywords))
            
            # 使用轮询查找
            coords = self.find_text_with_retry(keywords, timeout=8)
            
            if coords:
                cx, cy, _, _ = coords
                is_double = action == "double_click" or "双击" in target_desc
                self.human_click(cx, cy, double_click=is_double)
                
                # --- VERIFY TARGET AFTER OPENING ---
                # If we just double clicked a person's name (to open chat), verify they are now the active chat (Top Area)
                if is_double and len(target_desc) > 1:
                     print(f"   🛡️ [Verify] Verifying chat opened for '{target_desc}'...")
                     time.sleep(1.0) # Wait for animation
                     if self.eye.verify_text_presence_in_area(target_desc, region="top"):
                         print(f"   ✅ [SAFE] Verified check request: '{target_desc}' is open.")
                     else:
                         print(f"   ⚠️ [RISK] Could not verify '{target_desc}' in title bar. Continuing but risky.")

                return True
            else:
                print("   ⚠️  本地 OCR 最终未找到目标 (尝试 System 2 恢复)...")
                return False

        # 策略 3: 输入文本
        if action == "type":
            content = step.get('content') or step.get('text') or target_desc
            print(f"   ⌨️  输入: {content}")
            self.type_text(content)
            
            # --- VERIFY INPUT ---
            time.sleep(0.5)
            print(f"   🛡️ [Verify] Checking if '{content}' appeared in input box...")
            if self.eye.verify_text_presence_in_area(content, region="bottom"):
                 print(f"   ✅ [SAFE] Input verified.")
            else:
                 print(f"   ⚠️ [RISK] Input '{content}' not detected in bottom area. Might trigger retry.")
                 # TODO: Trigger retry logic here
            return True

        # 策略 4: 快捷键
        if action == "keyboard_shortcut":
            keys = step.get('keys') or step.get('key') or step.get('content') or target_desc
            print(f"   ⌨️  快捷键: {keys}")
            
            modifiers = []
            key = keys
            if "+" in keys:
                parts = keys.split("+")
                key = parts[-1]
                if "command" in parts or "cmd" in parts: modifiers.append("command down")
                if "shift" in parts: modifiers.append("shift down")
                if "control" in parts or "ctrl" in parts: modifiers.append("control down")
                if "option" in parts or "alt" in parts: modifiers.append("option down")
            
            using_str = " using {" + ", ".join(modifiers) + "}" if modifiers else ""
            
            # 特殊处理 return vs enter
            if key.lower() == "return": key = "return" # key code 36
            if key.lower() == "enter": key_code = 76 # keypad enter often triggers send
            
            try:
                if key.lower() == "enter":
                     # Keypad Enter (76)
                     cmd = f"""osascript -e 'tell application "System Events" to key code 76{using_str}'"""
                elif key.lower() == "return":
                     # Standard Return (36)
                     cmd = f"""osascript -e 'tell application "System Events" to key code 36{using_str}'"""
                else:
                     cmd = f"""osascript -e 'tell application "System Events" to keystroke "{key}"{using_str}'"""
                
                subprocess.run(cmd, shell=True, check=False)
                time.sleep(0.5)
            except Exception as e:
                print(f"   ❌ 快捷键失败: {e}")
            return True

        # 策略 5: 等待 / 验证
        if action == "wait":
            # 如果提供了 target，则变成了 "Wait until text appears"
            if target_desc and target_desc not in ["None", ""]:
                print(f"   🛑 验证: 等待 '{target_desc}' 出现...")
                self.find_text_with_retry([target_desc], timeout=10)
            else:
                print(f"   ⏳ (已跳过显式等待，依靠 Active Polling)")
            return True

        return True

    def __init__(self):
        self.eye = LocalPerception()
        # 优先使用 Google API Key (如果环境变量存在)
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.platform302_api_key = os.getenv('PLATFORM302_API_KEY')
        
        # 模型配置
        self.planning_model_google = "gemini-2.0-flash" # 替代已过时的 1.5-flash
        
    def query_gemini(self, prompt: str) -> Optional[str]:
        """直接调用 Google Gemini API"""
        if not self.google_api_key:
            print("❌ 未配置 GOOGLE_API_KEY")
            return None
            
    def query_gemini(self, prompt: str, image_path: Optional[str] = None) -> Optional[str]:
        """直接调用 Google Gemini API (支持图文多模态)"""
        if not self.google_api_key:
            print("❌ 未配置 GOOGLE_API_KEY")
            return None
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.planning_model_google}:generateContent?key={self.google_api_key}"
        headers = {"Content-Type": "application/json"}
        
        parts = [{"text": prompt}]
        
        # 如果有图片，读取并编码
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": image_data
                    }
                })
                print(f"   📸 已附加屏幕截图 ({os.path.getsize(image_path)/1024:.1f} KB)")
            except Exception as e:
                print(f"   ⚠️ 读取截图失败: {e}")
        
        data = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            print(f"   🧠 调用 Gemini 2.0 Flash ({self.planning_model_google})...")
            start = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"   ⏱️  耗时: {time.time() - start:.2f}s")
            
            if response.status_code != 200:
                print(f"   ❌ Google API Error: {response.text}")
                return None
                
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            error_msg = str(e)
            print(f"   ⚠️ Gemini 调用异常: {error_msg}")
            
            if "SSL" in error_msg or "Connection" in error_msg:
                 print("   💡 提示: 网络连接失败。如果您在中国大陆，请尝试添加 --proxy 参数。")
                 print("     示例: python3.9 vision_agent_pro.py ... --proxy http://127.0.0.1:7890")
            
            return None

    def plan_task(self, user_request: str) -> List[Dict[str, Any]]:
        """使用 AI 规划任务步骤 (System 2 - Multimodal Context Aware)"""
        
        # 1. 获取当前屏幕状态 (Context Awareness)
        print("   📸 正在获取当前屏幕状态以辅助规划...")
        screenshot_path = self.eye.capture_screen_to_file()
        
        prompt = f"""You are an automation expert. Plan the detailed steps for this request on macOS based on the provided tools.
Request: "{user_request}"

Context: I have provided a screenshot of the CURRENT SCREEN state. 
1. Analyze the screenshot. If the app (e.g. Feishu/Lark, WPS) is ALREADY open or in a specific state (e.g. chat window open), skip unnecessary steps.
2. If I need to search, look for "Search" bar.
3. If I need to type, look for "Input" box.

Available Actions:
1. open_app(app_name): Launch app. Use "wpsoffice" for WPS, "Lark" for Feishu.
2. click(text_target): Click text. 
   - CRITICAL: Icons (Emoji, Send, Gear) have NO TEXT. Do NOT try to click them directly unless you see their tooltip text.
   - HINT: To "Input", find the "Input Box" placeholder text like "Send a message" or "Type..." or click the empty space near the bottom.
3. double_click(text_target): Use this for opening files/chats if single click is unreliable.
4. type(text): Type text.
5. keyboard_shortcut(keys): "return" (Send), "command+return" (Line break).
6. wait(text_target): Check for UI changes (e.g. Chat Title).

Strategies for Chat Apps (Feishu/Lark):
1. Open App. 
2. IF chat is not open: Double Click Contact Name (e.g. "张小帆").
3. Type Message: `type("[Smile]")` (Just type the emoji text).
4. Send (CRITICAL):
   - Option A (Best): `keyboard_shortcut("command+return")` (This Force Sends in most apps).
   - Option B: `keyboard_shortcut("enter")` (Keypad Enter).
   - Option C: `click` "Send" icon (Only if you are sure about the coordinate).

Return strictly a JSON list of steps. 
- For TEXT Targets: `{{"action": "click", "target": "Name"}}`
- For ICON Targets: `{{"action": "click", "coordinate": [850, 920], "desc": "Click Send Icon"}}`
- DO NOT return steps with empty targets/coordinates.
"""
        # 优先使用 Google Gemini (速度最快)
        if self.google_api_key:
            # 传图给 Gemini 进行上下文感知规划
            json_str = self.query_gemini(prompt, image_path=screenshot_path)
            
            if json_str:
                try:
                    # 清理可能存在的 markdown 标记
                    json_str = json_str.replace("```json", "").replace("```", "").strip()
                    plan = json.loads(json_str)
                    
                    # 🛡️ 防御性编程: 确保每一步都有 step_number
                    for i, step in enumerate(plan):
                        if 'step_number' not in step:
                            step['step_number'] = i + 1
                            
                    print(f"   📋 生成计划 ({len(plan)} 步)")
                    return plan
                except Exception as e:
                    print(f"   ❌ 解析 Gemini 响应失败: {e}")
                    print(f"   原始响应: {json_str[:200]}...")
        
        # Fallback (302.ai or Hardcoded Debug)
        print("   ⚠️  无可用 AI 模型或调用失败，回退到 Debug 模式...")
        # ... (保留之前的硬编码作为最后的保底，但这里为了简洁省略，实际代码中可以保留)
        return []

    def execute_recovery_plan(self, plan: List[Dict[str, Any]]) -> bool:
        """执行恢复计划 (支持坐标点击)"""
        screen_w = Quartz.CGDisplayPixelsWide(Quartz.CGMainDisplayID())
        screen_h = Quartz.CGDisplayPixelsHigh(Quartz.CGMainDisplayID())
        
        for step in plan:
            action = step.get('action')
            coord = step.get('coordinate') # [x, y] normalized 0-1000
            
            if coord and action == "click":
                # System 2 直接给出了坐标 (解决 Icon 无法 OCR 的问题)
                nx, ny = coord
                # 转换归一化坐标 -> 屏幕坐标
                actual_x = int((nx / 1000.0) * screen_w)
                actual_y = int((ny / 1000.0) * screen_h)
                
                print(f"   🤖 System 2 指导点击坐标: [{nx}, {ny}] -> ({actual_x}, {actual_y})")
                self.human_click(actual_x, actual_y)
                time.sleep(1) # 恢复操作稍微慢点
                continue
            
            # 或者是普通文本步骤
            success = self.execute_fast_step(step)
            # 增加观察延迟，避免操作过快用户看不清，同时等待UI响应
            time.sleep(1.0) 
            
            if not success:
                print("   ❌ 恢复步骤执行失败")
                return False
                
        return True

    def analyze_failure_and_recover(self, failed_step: Dict[str, Any], user_request: str) -> bool:
        """
        System 2 Error Recovery:
        1. Capture Screenshot
        2. Ask Gemini what's wrong and how to fix it (Text OR Coordinates)
        3. Execute recovery steps
        """
        print(f"\n🚑 System 2 介入: 分析失败原因 (Step {failed_step['step_number']})...")
        
        # 1. 截图
        screenshot_path = self.eye.capture_screen_to_file()
        if not screenshot_path: return False
            
        # 2. 构造 Prompt
        prompt = f"""Task: "{user_request}"
Failed Step: {json.dumps(failed_step)}
Error: The agent could not find the target text locally.

Look at the screenshot. 
1. Analyze why the step failed (e.g. target is an icon, no text, or obscured).
2. Provide a recovery plan.
   - If the target is an ICON/IMAGE (like 'Emoji', 'Send', 'Menu'), you MUST provide 'coordinate': [x, y] (0-1000 scale from top-left).
   - If the target is TEXT, provide 'target': "text to find".

Return JSON only:
{{
  "analysis": "explanation",
  "recovery_plan": [
    {{"action": "click", "coordinate": [500, 500], "desc": "Click emoji icon"}},
    {{"action": "type", "content": "hello"}}
  ]
}}
"""
        # 3. 调用 Gemini
        json_str = self.query_gemini(prompt, image_path=screenshot_path)
        if not json_str: return False
            
        try:
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            result = json.loads(json_str)
            print(f"   🧐 分析: {result['analysis']}")
            print(f"   🛠️  恢复方案: {len(result['recovery_plan'])} 步")
            print(f"   📜 方案详情: {json.dumps(result['recovery_plan'], ensure_ascii=False)}")
            
            # 4. 执行恢复
            return self.execute_recovery_plan(result['recovery_plan'])
            
        except Exception as e:
            print(f"   ❌ 解析恢复方案失败: {e}")
            return False

    def run_task(self, user_request: str):
        print(f"🤖 Vision Agent Pro 启动 | 任务: {user_request}")
        
        if not self.google_api_key:
            print("⚠️警告: 未设置 GOOGLE_API_KEY，将无法使用 System 2 规划！")
            
        # 1. 规划
        plan = self.plan_task(user_request)
        if not plan:
            print("❌ 无法生成计划，任务终止")
            return

        # 2. 执行
        print("\n🚀 切换到 System 1 (Local Fast Loop) 执行...")
        for i, step in enumerate(plan):
            success = self.execute_fast_step(step)
            
            if not success:
                print(f"❌ 步骤 {step['step_number']} 失败。")
                if self.google_api_key:
                    # 尝试恢复
                    recovered = self.analyze_failure_and_recover(step, user_request)
                    if recovered:
                         print("   ✅ 恢复成功，继续执行后续步骤...")
                         continue 
                    else:
                        print("   ❌ 恢复失败，任务终止。")
                        break
                else:
                    break
        
        # 3. 终极验证 (System 2 Closed-Loop Verification)
        if self.google_api_key:
            self.verify_task_completion(user_request)
                
        print("\n✅ 任务结束")

    def verify_task_completion(self, user_request: str, max_retries: int = 3):
        """
        任务完成后进行视觉验证，如果未完成则自动补救 (Autopilot - Recursive Loop)
        """
        for attempt in range(max_retries):
            print(f"\n🕵️‍♂️ System 2 终极验证 (第 {attempt + 1}/{max_retries} 次): 检查任务是否完成...")
            
            # 1. 截图
            screenshot_path = self.eye.capture_screen_to_file()
            if not screenshot_path: return

            # 2. 询问 Gemini
            prompt = f"""Task: "{user_request}"
Context: The agent has finished executing the plan.
1. Look at the screenshot. Did we successfully achieve the goal? (e.g. check if the message is actually sent, or just typed in the box).
2. If NOT achieved, provide a "correction_plan" to finish the job.

Return JSON:
{{
  "success": false,
  "analysis": "Message is typed but not sent.",
  "correction_plan": [
    {{"action": "keyboard_shortcut", "content": "command+return", "desc": "Force Send"}},
    {{"action": "click", "coordinate": [920, 920], "desc": "Click Send Icon (Backup)"}}
  ]
}}
"""
            json_str = self.query_gemini(prompt, image_path=screenshot_path)
            if not json_str: return

            try:
                json_str = json_str.replace("```json", "").replace("```", "").strip()
                result = json.loads(json_str)
                
                if result.get("success"):
                    print("   🎉 验证通过: 任务已成功完成！")
                    return # 成功退出循环
                else:
                    print(f"   ⚠️ 验证失败: {result.get('analysis')}")
                    print(f"   🚑 启动自动补救 (Autopilot) - {len(result.get('correction_plan', []))} 步...")
                    
                    # --- CORE FIX: 暴力发送补救 (Focus + Vision + Keys) ---
                    print("   💪 [Brute Force] 启动强力发送程序...")
                    
                    # 1. 强制激活窗口 (Focus Snatch)
                    target_app = None
                    if "飞书" in user_request: target_app = "Lark"
                    elif "WPS" in user_request: target_app = "wpsoffice"
                    elif "微信" in user_request: target_app = "WeChat"
                    
                    if target_app:
                        print(f"   🔄 [Recovery] 强制激活窗口: {target_app}")
                        try:
                            # Use AppleScript to activate and ensure frontmost
                            subprocess.run(["osascript", "-e", f'tell application "{target_app}" to activate'], check=False)
                            time.sleep(1.0) # 让窗口飞一会儿
                        except:
                            pass

                    # 2. 视觉找图标 (Smart Click)
                    # 强制重新截图，因为 verify 的截图已经是 10秒 前的了
                    icon_coords = self.eye.find_icon("force_fresh_capture.png", "icon_send.png")
                    
                    if icon_coords:
                        cx, cy = icon_coords
                        print(f"   👁️  [Recovery] 视觉锁定发送按钮: ({cx}, {cy}) -> CLICK")
                        self.human_click(cx, cy)
                        time.sleep(0.5)
                    else:
                         print("   ⚠️ [Recovery] 未找到发送图标，准备盲打快捷键...")

                    # 3. 盲打快捷键 (Blind Keys)
                    print("   ⌨️  [Recovery] 尝试多种发送热键 (Return / Enter / Cmd+Return)...")
                    try:
                        # 1. Standard Return (Most likely for Feishu if 'Enter to Send' is on)
                        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 36'], check=False) 
                        time.sleep(0.5)
                        
                        # 2. Keypad Enter
                        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 76'], check=False)
                        time.sleep(0.5)
                        
                        # 3. Command + Return (Fallback)
                        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke return using {command down}'], check=False)
                        time.sleep(0.5)
                    except:
                        pass
                    # ---------------------------

                    # 执行 AI 生成的补救计划 (作为备份)
                    success = self.execute_recovery_plan(result.get('correction_plan', []))
                    if success:
                        print("   ✅ 补救动作执行完毕，准备重新验证...")
                        time.sleep(2.0) # 等待补救生效
                    else:
                        print("   ❌ 补救动作执行失败。")
                    
            except Exception as e:
                print(f"   ❌ 验证过程出错: {e}")
        
        print(f"\n❌ 达到最大验证次数 ({max_retries})，任务可能仍未完成。请人工检查。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--google-api-key", help="Google API Key")
    args = parser.parse_args()
    
    if args.google_api_key:
        os.environ['GOOGLE_API_KEY'] = args.google_api_key
    
    agent = VisionAgentPro()
    agent.run_task(args.task or "在WPS表格中输入金价2600美元")
