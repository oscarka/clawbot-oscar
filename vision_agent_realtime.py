#!/usr/bin/env python3
"""
实时视觉反馈的 AI 自动化系统
使用 Peekaboo 实时捕获 + AI 分析，实现流畅的操作反馈
"""

import subprocess
import json
import base64
import os
import tempfile
import requests
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
import queue

class RealtimeVisionAgent:
    """带实时视觉反馈的 AI Agent"""
    
    def __init__(self):
        self.vision_model = "glm-4.6v-flash"
        self.planning_model = "claude-opus-4-5-20251101"
        self.platform302_api_key = os.getenv('PLATFORM302_API_KEY', 'sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW')
        self.screenshot_dir = Path("/tmp/vision_agent")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.capture_queue = queue.Queue()
        self.is_monitoring = False
        
    def capture_screen(self, path: Optional[str] = None) -> str:
        """截图当前屏幕"""
        if path is None:
            path = str(self.screenshot_dir / f"screenshot_{int(time.time())}.png")
        
        result = subprocess.run([
            'peekaboo', 'image',
            '--mode', 'screen',
            '--path', path
        ], capture_output=True)
        
        if result.returncode == 0:
            return path
        return None
    
    def start_realtime_monitoring(self, duration: int = 10, fps: int = 2):
        """启动实时监控（使用 Peekaboo live capture）"""
        print(f"   📹 启动实时监控（{duration}秒，{fps} FPS）...")
        
        capture_dir = self.screenshot_dir / "realtime"
        capture_dir.mkdir(exist_ok=True)
        capture_path = str(capture_dir / "live_capture")
        
        # 使用 Peekaboo 实时捕获
        process = subprocess.Popen([
            'peekaboo', 'capture', 'live',
            '--mode', 'screen',
            '--duration', str(duration),
            '--active-fps', str(fps),
            '--idle-fps', '1',
            '--path', capture_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.is_monitoring = True
        return process, capture_path
    
    def extract_key_frames(self, capture_path: str, interval: float = 0.5) -> List[str]:
        """从实时捕获中提取关键帧"""
        # Peekaboo 会生成视频或帧序列
        # 这里简化处理，实际需要根据 Peekaboo 输出格式调整
        frames = []
        
        # 如果 Peekaboo 生成了帧序列
        frame_dir = Path(capture_path)
        if frame_dir.exists():
            frame_files = sorted(frame_dir.glob("*.png"))
            # 按间隔提取
            for i in range(0, len(frame_files), max(1, int(interval * 2))):
                frames.append(str(frame_files[i]))
        
        return frames
    
    def analyze_realtime_feedback(self, frames: List[str], expected_result: str) -> Dict[str, Any]:
        """分析实时反馈，判断操作是否成功"""
        if not frames:
            return {"success": False, "reason": "无反馈帧"}
        
        # 分析最后一帧（最新状态）
        latest_frame = frames[-1]
        
        prompt = f"""请分析这个屏幕截图，判断操作是否达到了预期结果。

预期结果：{expected_result}

请返回 JSON：
{{
  "success": true/false,
  "progress": 0.0-1.0,
  "current_state": "当前状态描述",
  "next_action": "下一步建议",
  "needs_adjustment": true/false
}}"""
        
        analysis = self.vision_analyze(latest_frame, prompt)
        if analysis["success"]:
            try:
                import re
                json_match = re.search(r'\{.*\}', analysis["analysis"], re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except:
                pass
        
        return {"success": False, "reason": "分析失败"}
    
    def vision_analyze(self, screenshot_path: str, prompt: str) -> Dict[str, Any]:
        """使用 AI 视觉模型分析截图"""
        with open(screenshot_path, 'rb') as f:
            image_data = f.read()
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        response = requests.post(
            "https://api.302.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.platform302_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return {"success": True, "analysis": content}
        else:
            return {"success": False, "error": response.text}
    
    def find_app_intelligently(self, app_description: str) -> Optional[str]:
        """智能查找应用（使用系统 Spotlight）"""
        print(f"   🤖 智能查找应用: {app_description}")
        
        # 1. 尝试直接打开
        result = subprocess.run(['open', '-a', app_description], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ 直接打开成功")
            return app_description
        
        # 2. 使用 Spotlight 搜索
        print(f"   🔍 使用 Spotlight 搜索...")
        search_result = subprocess.run([
            'mdfind', '-onlyin', '/Applications',
            f'kMDItemKind == "Application" && kMDItemDisplayName == "*{app_description}*"cd'
        ], capture_output=True, text=True)
        
        if search_result.returncode == 0 and search_result.stdout.strip():
            app_paths = [p.strip() for p in search_result.stdout.strip().split('\n') 
                        if p.strip() and p.endswith('.app')]
            if app_paths:
                app_path = app_paths[0]
                app_name = Path(app_path).stem
                print(f"   📍 找到应用: {app_name}")
                return app_name
        
        # 3. 模糊搜索
        search_cmd = f'mdfind "kMDItemKind == \'Application\'" | grep -i "{app_description}"'
        search_result = subprocess.run(search_cmd, shell=True, capture_output=True, text=True)
        if search_result.returncode == 0 and search_result.stdout.strip():
            app_paths = [p.strip() for p in search_result.stdout.strip().split('\n') 
                        if p.strip() and p.endswith('.app')]
            if app_paths:
                app_name = Path(app_paths[0]).stem
                print(f"   📍 找到应用: {app_name}")
                return app_name
        
        return None
    
    def execute_with_realtime_feedback(self, action: str, target: Dict[str, Any], 
                                       content: Optional[str] = None, 
                                       expected_result: str = "") -> Dict[str, Any]:
        """执行操作并获取实时反馈"""
        print(f"   ⚙️  执行操作: {action}")
        
        # 1. 操作前截图
        before_screenshot = self.capture_screen()
        
        # 2. 执行操作
        success = self._perform_action(action, target, content)
        
        if not success:
            return {"success": False, "error": "操作执行失败"}
        
        # 3. 启动实时监控
        monitor_process, capture_path = self.start_realtime_monitoring(duration=5, fps=2)
        
        # 4. 等待监控完成
        monitor_process.wait()
        
        # 5. 提取关键帧并分析
        frames = self.extract_key_frames(capture_path)
        feedback = self.analyze_realtime_feedback(frames, expected_result)
        
        # 6. 操作后截图
        after_screenshot = self.capture_screen()
        
        return {
            "success": feedback.get("success", True),
            "feedback": feedback,
            "before": before_screenshot,
            "after": after_screenshot,
            "frames": frames
        }
    
    def _perform_action(self, action: str, target: Dict[str, Any], content: Optional[str] = None) -> bool:
        """执行基础操作"""
        if action == "open_app":
            app_description = target.get("target") or target.get("name")
            app_name = self.find_app_intelligently(app_description)
            if app_name:
                result = subprocess.run(['open', '-a', app_name], capture_output=True, text=True)
                if result.returncode == 0:
                    time.sleep(2)
                    return True
            return False
        # ... 其他操作
        return False
    
    def plan_task(self, user_request: str) -> List[Dict[str, Any]]:
        """规划任务（复用原有逻辑）"""
        # ... 复用 vision_agent.py 的规划逻辑
        pass
    
    def run_task(self, user_request: str) -> Dict[str, Any]:
        """执行任务（带实时反馈）"""
        # ... 使用 execute_with_realtime_feedback
        pass


if __name__ == '__main__':
    print("实时视觉反馈系统（开发中）")
    print("建议：使用 Peekaboo capture live + AI 分析实现实时反馈")
