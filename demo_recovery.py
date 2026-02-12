
import time
import sys
import os
from unittest.mock import MagicMock
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append('/Users/oscar/moltbot')
from vision_agent import VisionAgent

# Status update utility (similar to test_with_display.py)
STATUS_FILE = Path("/tmp/vision_agent_status.txt")
LOG_FILE = Path("/tmp/vision_agent_status.log")
COMMAND_LOG = Path("/tmp/vision_agent_commands.log")

def update_status(status: str, details: str = ""):
    """Update status file for the web display"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_text = f"状态: {status}\n时间: {timestamp}\n{details}"
    STATUS_FILE.write_text(status_text)
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {status}: {details}\n")
    
    # Also print to stdout
    print(f"[{timestamp}] {status}: {details}")

def log_command(command, status='executing'):
    """Log command for the web display"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(COMMAND_LOG, 'a') as f:
        f.write(f"[{timestamp}] {status.upper()}: {command}\n")

def run_demo():
    print("🚀 Starting Recovery Demo...")
    update_status("准备中", "初始化演示...")
    time.sleep(1)

    # Initialize Agent
    agent = VisionAgent()
    
    # --- MOCK SETUP START ---
    # We mock the internal methods to simulate the scenario without needing real apps
    # But we add delays and status updates to make it visible
    
    # Mock capture_screen to return a dummy path
    agent.capture_screen = MagicMock(return_value="/tmp/mock_screenshot.png")
    agent.capture_screen_fast = MagicMock(return_value="/tmp/mock_screenshot_fast.png")
    agent.start_realtime_capture = MagicMock(return_value=(MagicMock(), "/tmp/mock_capture"))
    agent.extract_key_frames = MagicMock(return_value=["/tmp/mock_frame.png"])
    
    # Mock locate_element with delay
    def mock_locate(description, state):
        update_status("进行中", f"🔍 正在定位目标: {description}...")
        time.sleep(1.5) # Simulate processing
        return {"found": True, "coordinates": {"x": 100, "y": 200}, "description": "Mock Target"}
    agent.locate_element = mock_locate

    # Mock perform_action with visual updates
    def mock_perform(action, target, content=None):
        target_name = target.get('target', 'Unknown')
        if not target_name and 'description' in target:
            target_name = target['description']
            
        update_status("进行中", f"⚙️ 执行操作: {action} -> {target_name}")
        log_command(f"{action} {target_name}", "executing")
        time.sleep(2) # Simulate action
        update_status("进行中", f"✅ 操作完成: {action}")
        log_command(f"{action} {target_name}", "success")
        return True
    agent.perform_action = mock_perform

    # Mock vision_analyze to simulate the FAILURE and SUGGESTION
    def mock_analyze(screenshot, prompt):
        time.sleep(1) # Simulate AI thinking
        
        # 1. Feedback analysis (The interesting part!)
        if "next_action" in prompt: 
            update_status("分析中", "🤔 AI 正在分析操作反馈...")
            time.sleep(2)
            
            error_msg = "检测到异常：弹窗遮挡了按钮"
            suggestion = "点击 '关闭' 按钮"
            update_status("卡住了", f"❌ {error_msg}")
            log_command("反馈分析: 失败", "error")
            time.sleep(2)
            
            update_status("恢复中", f"💡 AI 建议: {suggestion}")
            log_command(f"建议: {suggestion}", "warning")
            time.sleep(2)
            
            return {
                "success": True, 
                "analysis": '''{
                    "success": false,
                    "current_state": "Popup blocking button",
                    "stuck": true,
                    "stuck_reason": "Popup detected",
                    "next_action": {
                        "action": "click",
                        "target": "Close Popup Button",
                        "description": "Click the X to close the popup"
                    }
                }'''
            }
        # 2. Verification (Post-recovery)
        elif "expected_result" in prompt:
            update_status("验证中", "👀 正在验证操作结果...")
            time.sleep(1.5)
            update_status("进行中", "✅ 验证通过！恢复成功")
            return {
                "success": True,
                "analysis": '{"success": true, "reason": "Popup gone, button clicked"}'
            }
        # 3. State perception
        else:
             return {
                "success": True,
                "analysis": '{"active_app": "MockApp", "ui_elements": ["Button"], "state_description": "Ready"}'
            }
    agent.vision_analyze = mock_analyze
    # --- MOCK SETUP END ---

    # Define the step to execute
    step = {
        "step_number": 1,
        "action": "click",
        "target": "Submit Button",
        "expected_result": "Form Submitted"
    }

    # Run the agent!
    update_status("进行中", f"🎬 开始执行步骤 1: 点击提交按钮")
    time.sleep(1)
    
    agent.execute_step(step)
    
    update_status("完成", "🎉 演示结束！成功自动修复错误")
    log_command("演示结束", "success")

if __name__ == "__main__":
    run_demo()
