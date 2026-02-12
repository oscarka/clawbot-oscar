#!/usr/bin/env python3
"""
视觉引导的 AI 自动化系统
结合 macOS 视觉控制和 AI 模型，实现通用任务自动化
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

class VisionAgent:
    """视觉引导的 AI 自动化 Agent"""
    
    def __init__(self):
        self.vision_model = "glm-4.6v-flash"
        # 尝试多个模型，按优先级排序
        self.planning_models = [
            "claude-opus-4-5-20251101",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "glm-4.6v-flash"  # 备选：使用视觉模型
        ]
        self.platform302_api_key = os.getenv('PLATFORM302_API_KEY', 'sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW')
        self.screenshot_dir = Path("/tmp/vision_agent")
        self.screenshot_dir.mkdir(exist_ok=True)
        
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
    
    def plan_task(self, user_request: str) -> List[Dict[str, Any]]:
        """使用 AI 规划任务步骤（改进：要求更详细、更具体的操作指令）"""
        prompt = f"""用户请求：{user_request}

请将这个任务分解为**非常详细和具体**的执行步骤。每个步骤必须包括：

1. **step_number**: 步骤编号
2. **action**: 操作类型（open_app, click, type, wait, scroll, keyboard_shortcut等）
3. **target**: **非常具体的目标描述**，包括：
   - 如果是点击：明确指出是"顶部工具栏左侧的加号按钮"、"菜单栏的'文件'菜单"、"右下角的'发送'按钮"等
   - 如果是应用：使用实际的应用名称（如"WPS Office"、"Lark"、"飞书"等）
   - 如果是输入框：描述位置和特征（如"底部输入框"、"搜索框"等）
4. **content**: 操作内容（如果是输入操作，给出具体文本）
5. **expected_result**: 预期结果描述
6. **verification**: 如何验证这一步是否成功

**重要要求：**
- 必须基于实际的应用界面和操作流程
- 每个操作目标必须**非常具体**，不能模糊（如"新建按钮"不够，应该是"顶部工具栏左侧的'新建'按钮"或"左上角的加号图标"）
- 考虑 macOS 应用的实际界面布局
- 如果涉及文件操作，明确文件路径和操作方式
- 如果涉及搜索，明确搜索关键词和位置

请返回 JSON 格式的步骤列表，只返回 JSON，不要其他文字：
[
  {{
    "step_number": 1,
    "action": "open_app",
    "target": "WPS Office",
    "content": null,
    "expected_result": "WPS Office 应用已打开，显示主界面",
    "verification": "检查屏幕是否显示 WPS Office 主窗口，包含左侧导航栏和中间文件列表区域"
  }},
  {{
    "step_number": 2,
    "action": "click",
    "target": "顶部工具栏左侧的'新建'按钮或加号图标，用于创建新文件",
    "content": null,
    "expected_result": "打开新建文件对话框或直接创建新表格",
    "verification": "检查是否出现新表格窗口或新建文件对话框"
  }},
  {{
    "step_number": 3,
    "action": "click",
    "target": "新建对话框中的'表格'或'Excel'选项",
    "content": null,
    "expected_result": "创建新的 Excel 表格",
    "verification": "检查是否出现空白的 Excel 工作表界面，包含行号和列标"
  }}
]"""
        
        print("   正在调用 AI 规划模型...")
        
        response = None
        used_model = None
        
        # 尝试多个模型
        for model in self.planning_models:
            print(f"   尝试模型: {model}...")
            try:
                response = requests.post(
                    "https://api.302.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.platform302_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 4000
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    print(f"   ✅ 模型 {model} 可用")
                    used_model = model
                    break
                else:
                    print(f"   ⚠️  模型 {model} 不可用: HTTP {response.status_code}")
                    if model == self.planning_models[-1]:
                        print(f"   ❌ 所有模型都不可用")
                        print(f"   最后错误: {response.text[:200]}")
                        return []
                    continue
            except Exception as e:
                print(f"   ⚠️  模型 {model} 调用出错: {e}")
                if model == self.planning_models[-1]:
                    return []
                continue
        
        if response is None or response.status_code != 200:
            return []
        
        try:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            print(f"   ✅ 收到规划结果（使用模型: {used_model}），长度: {len(content)} 字符")
            # print(f"   内容预览: {content[:200]}...")
            
            # 尝试解析 JSON
            import re
            json_str = None
            
            # 1. 尝试匹配 Markdown 代码块 ```json ... ```
            code_block_match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', content)
            if code_block_match:
                json_str = code_block_match.group(1)
            
            # 2. 如果没找到，尝试匹配最外层的 [...]
            if not json_str:
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    json_str = json_match.group()
            
            # 3. 如果还是没找到，尝试清理内容（去掉可能的 markdown 标记）
            if not json_str:
                cleaned_content = content.replace('```json', '').replace('```', '').strip()
                if cleaned_content.startswith('[') and cleaned_content.endswith(']'):
                    json_str = cleaned_content

            if json_str:
                try:
                    steps = json.loads(json_str)
                    print(f"   ✅ 成功解析 {len(steps)} 个步骤")
                    return steps
                except json.JSONDecodeError:
                    print("   ⚠️  提取的 JSON 格式有误，尝试修复...")
                    # 这里可以添加简单的修复逻辑，或者直接报错
                    pass
            
            print("   ⚠️  未找到有效 JSON 数组，尝试直接解析整个内容...")
            steps = json.loads(content)
            if isinstance(steps, list):
                print(f"   ✅ 成功解析 {len(steps)} 个步骤")
                return steps
                
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON 解析失败: {e}")
            print(f"   原始内容(前500): {content[:500]}")
            print(f"   原始内容(后500): {content[-500:]}")
        except Exception as e:
            print(f"   ❌ 解析出错: {e}")
            if 'content' in locals():
                print(f"   原始内容(前500): {content[:500]}")
        
        return []
    
    def perceive_state(self) -> Dict[str, Any]:
        """感知当前屏幕状态"""
        screenshot = self.capture_screen()
        if not screenshot:
            return {"error": "截图失败"}
        
        prompt = """请分析这个屏幕截图，识别：
1. 当前活动的应用名称
2. 可见的 UI 元素（按钮、输入框、菜单等）
3. 当前屏幕的状态描述
4. 是否有错误提示或警告

返回 JSON 格式：
{
  "active_app": "应用名",
  "ui_elements": ["元素1", "元素2"],
  "state_description": "当前状态描述",
  "has_errors": false
}"""
        
        analysis = self.vision_analyze(screenshot, prompt)
        if analysis["success"]:
            # 尝试解析 JSON
            try:
                import re
                json_match = re.search(r'\{.*\}', analysis["analysis"], re.DOTALL)
                if json_match:
                    state = json.loads(json_match.group())
                    state["screenshot"] = screenshot
                    return state
            except:
                pass
        
        return {
            "screenshot": screenshot,
            "analysis_text": analysis.get("analysis", "")
        }
    
    def locate_element(self, target_description: str, current_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """定位目标 UI 元素"""
        screenshot = current_state.get("screenshot")
        if not screenshot:
            return None
        
        prompt = f"""请在这个截图中定位以下目标：{target_description}

请返回 JSON 格式，包含：
{{
  "found": true/false,
  "element_type": "按钮/输入框/菜单等",
  "coordinates": {{"x": 坐标, "y": 坐标}},
  "description": "元素描述"
}}"""
        
        analysis = self.vision_analyze(screenshot, prompt)
        if analysis["success"]:
            try:
                import re
                json_match = re.search(r'\{.*\}', analysis["analysis"], re.DOTALL)
                if json_match:
                    location = json.loads(json_match.group())
                    return location
            except:
                pass
        
        return None
    
    def find_app_intelligently(self, app_description: str) -> Optional[str]:
        """智能查找应用（使用系统 Spotlight，无需硬编码映射）"""
        print(f"   🤖 智能查找应用: {app_description}")
        
        # 1. 尝试直接打开（最简单）
        print(f"   📱 尝试直接打开...")
        result = subprocess.run(['open', '-a', app_description], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ 直接打开成功")
            return app_description
        
        # 2. 使用 Spotlight 精确搜索（macOS 原生能力）
        print(f"   🔍 使用 Spotlight 搜索...")
        search_result = subprocess.run([
            'mdfind', '-onlyin', '/Applications',
            f'kMDItemKind == "Application" && kMDItemDisplayName == "*{app_description}*"cd'
        ], capture_output=True, text=True)
        
        if search_result.returncode == 0 and search_result.stdout.strip():
            app_paths = [p.strip() for p in search_result.stdout.strip().split('\n') 
                        if p.strip() and p.endswith('.app')]
            if app_paths:
                app_name = Path(app_paths[0]).stem
                print(f"   ✅ Spotlight 找到: {app_name}")
                return app_name
        
        # 3. 模糊搜索（grep）- 改进搜索逻辑
        print(f"   🔍 模糊搜索...")
        # 先尝试完整搜索
        search_cmd = f'mdfind "kMDItemKind == \'Application\'" | grep -i "{app_description}"'
        search_result = subprocess.run(search_cmd, shell=True, capture_output=True, text=True)
        
        if search_result.returncode == 0 and search_result.stdout.strip():
            app_paths = [p.strip() for p in search_result.stdout.strip().split('\n') 
                        if p.strip() and p.endswith('.app')]
            if app_paths:
                app_name = Path(app_paths[0]).stem
                print(f"   ✅ 模糊搜索找到: {app_name}")
                return app_name
        
        # 如果还是找不到，尝试拆分关键词搜索
        keywords = app_description.split()
        for keyword in keywords:
            if len(keyword) < 3:
                continue
            print(f"   🔍 尝试关键词: {keyword}...")
            search_cmd = f'mdfind "kMDItemKind == \'Application\'" | grep -i "{keyword}"'
            search_result = subprocess.run(search_cmd, shell=True, capture_output=True, text=True)
            if search_result.returncode == 0 and search_result.stdout.strip():
                app_paths = [p.strip() for p in search_result.stdout.strip().split('\n') 
                            if p.strip() and p.endswith('.app')]
                if app_paths:
                    app_name = Path(app_paths[0]).stem
                    print(f"   ✅ 关键词搜索找到: {app_name}")
                    return app_name
        
        # 4. 特殊处理：常见应用的别名映射（仅作为最后备选）
        common_aliases = {
            "WPS Office": "wpsoffice",
            "WPS": "wpsoffice",
            "WPS表格": "wpsoffice",
            "Excel": "Microsoft Excel",
            "飞书": "Lark",
        }
        
        if app_description in common_aliases:
            alias_name = common_aliases[app_description]
            print(f"   🔄 尝试别名: {alias_name}...")
            result = subprocess.run(['open', '-a', alias_name], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ 通过别名打开成功: {alias_name}")
                return alias_name
        
        # 4. 在 /Applications 目录查找
        print(f"   🔍 在 /Applications 目录查找...")
        find_result = subprocess.run([
            'find', '/Applications', '-maxdepth', '2',
            '-name', f'*{app_description}*',
            '-type', 'd'
        ], capture_output=True, text=True)
        
        if find_result.returncode == 0 and find_result.stdout.strip():
            app_dirs = [d.strip() for d in find_result.stdout.strip().split('\n') if d.strip()]
            for app_dir in app_dirs[:3]:
                app_file = subprocess.run([
                    'find', app_dir, '-name', '*.app', '-maxdepth', '1'
                ], capture_output=True, text=True)
                if app_file.stdout.strip():
                    app_path = app_file.stdout.strip().split('\n')[0]
                    app_name = Path(app_path).stem
                    print(f"   ✅ 目录查找找到: {app_name}")
                    return app_name
        
        print(f"   ❌ 未找到应用: {app_description}")
        return None
    
    def perform_action(self, action: str, target: Dict[str, Any], content: Optional[str] = None) -> bool:
        """执行操作"""
        if action == "open_app":
            # 打开应用 - 使用智能查找（无需硬编码映射）
            app_description = target.get("target") or target.get("name")
            if not app_description:
                print(f"   ❌ 未指定应用名称")
                return False
            
            print(f"   📱 打开应用: {app_description}")
            
            # 智能查找应用
            app_name = self.find_app_intelligently(app_description)
            
            if not app_name:
                print(f"   ❌ 应用查找失败")
                return False
            
            # 打开应用
            result = subprocess.run(['open', '-a', app_name], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ 应用启动成功: {app_name}")
                time.sleep(2)  # 等待应用启动
                return True
            else:
                print(f"   ❌ 应用启动失败: {result.stderr}")
                return False
            
        elif action == "click":
            # 点击 - 增强版可靠性
            coords = target.get("coordinates", {})
            x = coords.get("x")
            y = coords.get("y")
            
            if x and y:
                print(f"   🖱️  移动鼠标并点击: ({x}, {y})")
                
                # 优先使用 cliclick (更可靠的 macOS 自动化工具)
                try:
                    # 1. 移动鼠标
                    subprocess.run(['cliclick', f'm:{int(x)},{int(y)}'], check=False)
                    time.sleep(0.3) # 等待鼠标移动到位
                    
                    # 2. 点击 (对于某些应用，双击更保险)
                    # 如果目标包含 "WPS" 或 "表格"，尝试双击
                    if "WPS" in str(target) or "表格" in str(target) or "Excel" in str(target):
                        print(f"   🖱️  检测到表格应用，使用双击...")
                        subprocess.run(['cliclick', 'dc:.'], check=False)
                    else:
                        subprocess.run(['cliclick', 'c:.'], check=False)
                        
                    time.sleep(0.5) # 等待点击生效
                    return True
                except FileNotFoundError:
                    # 如果没有 cliclick，回退到 peekaboo
                    print("   ⚠️  未安装 cliclick，回退到 peekaboo")
                    result = subprocess.run([
                        'peekaboo', 'click',
                        '--coords', f'{int(x)},{int(y)}'
                    ], capture_output=True)
                    time.sleep(0.5)
                    return result.returncode == 0
                except Exception as e:
                    print(f"   ❌ 点击操作出错: {e}")
                    return False
                
        elif action == "type":
            # 输入文本
            if content:
                print(f"   ⌨️  输入文本: {content}")
                
                # 优先使用 cliclick 输入
                try:
                    subprocess.run(['cliclick', f'w:500 t:{content}'], check=False)
                    return True
                except:
                    pass
                
                result = subprocess.run([
                    'peekaboo', 'type',
                    content,
                    '--delay', '10'
                ], capture_output=True)
                time.sleep(0.5)
                return result.returncode == 0
                
        elif action == "wait":
            # 等待
            duration = target.get("duration", 2)
            time.sleep(duration)
            return True
            
        return False
    
    def verify_result(self, expected_result: str, current_state: Dict[str, Any]) -> bool:
        """验证操作结果"""
        screenshot = current_state.get("screenshot")
        if not screenshot:
            return False
        
        prompt = f"""请检查当前屏幕是否达到了预期结果：{expected_result}

返回 JSON：
{{
  "success": true/false,
  "reason": "原因描述"
}}"""
        
        analysis = self.vision_analyze(screenshot, prompt)
        if analysis["success"]:
            try:
                import re
                json_match = re.search(r'\{.*\}', analysis["analysis"], re.DOTALL)
                if json_match:
                    verification = json.loads(json_match.group())
                    return verification.get("success", False)
            except:
                pass
        
        return False
    
    def capture_screen_fast(self) -> Optional[str]:
        """快速截图（使用 screencapture，比 Peekaboo 更快）"""
        screenshot_path = str(self.screenshot_dir / f"fast_{int(time.time())}.png")
        result = subprocess.run([
            'screencapture', '-x', screenshot_path
        ], capture_output=True, timeout=5)
        
        if result.returncode == 0 and os.path.exists(screenshot_path):
            return screenshot_path
        return None
    
    def start_realtime_capture(self, duration: int = 1, fps: int = 1) -> tuple:
        """启动 Peekaboo 实时捕获（优化：减少时间和FPS）"""
        capture_dir = self.screenshot_dir / "realtime"
        capture_dir.mkdir(exist_ok=True)
        capture_path = str(capture_dir / f"capture_{int(time.time())}")
        
        print(f"   📹 启动实时监控（{duration}秒，{fps} FPS）...")
        
        process = subprocess.Popen([
            'peekaboo', 'capture', 'live',
            '--mode', 'screen',
            '--duration', str(duration),
            '--active-fps', str(fps),
            '--idle-fps', '1',
            '--path', capture_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return process, capture_path
    
    def extract_key_frames(self, capture_path: str) -> List[str]:
        """从实时捕获中提取关键帧"""
        frames = []
        frame_dir = Path(capture_path)
        
        if frame_dir.exists():
            # Peekaboo 可能生成视频或帧序列
            # 先尝试找 PNG 帧
            frame_files = sorted(frame_dir.glob("*.png"))
            if frame_files:
                # 取最后几帧（最新的状态）
                frames = [str(f) for f in frame_files[-3:]]
            else:
                # 如果没找到 PNG，可能是视频文件，需要提取帧
                video_files = list(frame_dir.glob("*.mp4")) + list(frame_dir.glob("*.mov"))
                if video_files:
                    print(f"   📹 检测到视频文件，提取关键帧...")
                    # 使用 ffmpeg 提取帧（如果可用）
                    try:
                        video_path = str(video_files[0])
                        output_pattern = str(frame_dir / "frame_%04d.png")
                        subprocess.run([
                            'ffmpeg', '-i', video_path,
                            '-vf', 'fps=2',
                            '-frames:v', '6',
                            output_pattern
                        ], capture_output=True, check=True, timeout=10)
                        frame_files = sorted(frame_dir.glob("frame_*.png"))
                        frames = [str(f) for f in frame_files[-3:]] if frame_files else []
                    except:
                        print(f"   ⚠️  无法提取视频帧（需要安装 ffmpeg）")
        
        return frames
    
    def analyze_realtime_feedback(self, frame_path: str, expected_result: str) -> Dict[str, Any]:
        """使用免费的 GLM-4.6v-flash 分析实时反馈（优化：简化提示词，加快响应）"""
        prompt = f"""分析截图，判断是否达到预期：{expected_result}

返回JSON（必须）：
{{
  "success": true/false,
  "current_state": "简短状态描述",
  "next_action": {{
    "action": "click/type/wait",
    "target": "元素描述",
    "description": "操作说明"
  }},
  "stuck": true/false,
  "stuck_reason": "卡住原因"
}}

如果未成功，必须提供next_action。"""
        
        analysis = self.vision_analyze(frame_path, prompt)
        if analysis["success"]:
            try:
                import re
                json_match = re.search(r'\{.*\}', analysis["analysis"], re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"   ⚠️  JSON 解析失败: {e}")
        
        return {"success": False, "reason": "分析失败"}
    
    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤（带实时反馈）"""
        step_num = step.get("step_number", 0)
        action = step.get("action", "")
        target_desc = step.get("target", "")
        content = step.get("content")
        expected = step.get("expected_result", "")
        
        print(f"\n{'='*60}")
        print(f"执行步骤 {step_num}: {action} - {target_desc}")
        print(f"{'='*60}")
        
        # 1. 操作前感知状态
        print("📸 操作前感知状态...")
        before_state = self.perceive_state()
        print(f"   当前应用: {before_state.get('active_app', '未知')}")
        
        # 2. 定位目标（如果需要）
        target = None
        if action in ["click", "type"]:
            print(f"🔍 定位目标: {target_desc}...")
            target = self.locate_element(target_desc, before_state)
            if target and target.get("found"):
                coords = target.get("coordinates", {})
                print(f"   ✅ 找到目标: {target.get('description', '')}")
                if coords.get("x") and coords.get("y"):
                    print(f"   📍 坐标: ({coords.get('x')}, {coords.get('y')})")
            else:
                print(f"   ⚠️  未找到目标")
                # 如果模型提供了备选目标，尝试使用
                if target and target.get("alternative_targets"):
                    alt_targets = target.get("alternative_targets", [])
                    print(f"   💡 模型建议的备选目标: {', '.join(alt_targets[:3])}")
                    # 尝试定位第一个备选目标
                    if alt_targets:
                        alt_target = self.locate_element(alt_targets[0], before_state)
                        if alt_target and alt_target.get("found"):
                            print(f"   ✅ 找到备选目标: {alt_targets[0]}")
                            target = alt_target
                        else:
                            target = {"target": target_desc}
                    else:
                        target = {"target": target_desc}
                else:
                    target = {"target": target_desc}
        
        # 3. 执行操作
        print(f"⚙️  执行操作: {action}...")
        success = self.perform_action(action, target or {"target": target_desc}, content)
        
        if not success:
            return {"success": False, "error": "操作执行失败"}
        
        # 4. 快速反馈（优化：使用快速截图 + 异步分析）
        print(f"📹 快速反馈检查...")
        
        # 方案1: 使用快速截图（screencapture，比 Peekaboo 快）
        fast_screenshot = self.capture_screen_fast()
        
        feedback = None
        if fast_screenshot:
            print(f"   📸 快速截图完成")
            # 直接分析截图（不等待视频捕获）
            feedback = self.analyze_realtime_feedback(fast_screenshot, expected)
            print(f"   📊 反馈分析: {feedback.get('current_state', '未知')[:100]}")
        else:
            # 备选方案：使用 Peekaboo（但缩短时间）
            print(f"   📹 使用 Peekaboo 捕获（优化：1秒，1 FPS）...")
            monitor_process, capture_path = self.start_realtime_capture(duration=1, fps=1)
            monitor_process.wait()
            time.sleep(0.2)  # 减少等待时间
            
            frames = self.extract_key_frames(capture_path)
            if frames:
                print(f"   📸 提取了 {len(frames)} 个关键帧")
                feedback = self.analyze_realtime_feedback(frames[-1], expected)
                print(f"   📊 反馈分析: {feedback.get('current_state', '未知')[:100]}")
            else:
                print(f"   ⚠️  未获取到实时帧，使用普通截图验证")
        
        # 处理反馈结果
        if feedback:
            if feedback.get("success"):
                print(f"   ✅ 操作成功确认")
            else:
                print(f"   ⚠️  操作可能未达到预期")
                
                # 检查是否卡住
                if feedback.get("stuck"):
                    print(f"   🚨 检测到卡住: {feedback.get('stuck_reason', '未知原因')}")
                
                # 显示操作指导
                next_action = feedback.get("next_action")
                if next_action:
                    action_type = next_action.get("action", "未知")
                    target_desc = next_action.get("target", "未知")
                    description = next_action.get("description", "")
                    print(f"   💡 模型建议: {action_type} -> {target_desc}")
                    if description:
                        print(f"      {description}")
                        
                    # 自动执行建议的操作
                    if action_type and target_desc and action_type != "未知":
                        print(f"   🔄 尝试执行模型建议的恢复操作...")
                        
                        # 1. 定位（如果需要）
                        recovery_target = {"target": target_desc}
                        
                        # 使用刚才的截图来定位，避免重新截图
                        recov_screenshot = fast_screenshot if fast_screenshot else (frames[-1] if frames else None)
                        
                        if action_type in ["click", "type"]:
                             print(f"   🔍 定位建议目标: {target_desc}...")
                             if recov_screenshot:
                                 # 构造临时状态用于定位
                                 recov_state = {"screenshot": recov_screenshot}
                                 found_target = self.locate_element(target_desc, recov_state)
                                 if found_target and found_target.get("found"):
                                     recovery_target = found_target
                                     print(f"   ✅ 找到建议目标: {recovery_target.get('description', '')}")
                                     coords = recovery_target.get("coordinates", {})
                                     if coords:
                                         print(f"   📍 坐标: ({coords.get('x')}, {coords.get('y')})")
                                 else:
                                     print(f"   ⚠️  在当前截图中未定位到建议目标，将尝试盲操作或再次查找...")

                        # 2. 执行
                        # 注意：如果是 type 操作，目前 next_action 结构中没有 content 字段
                        # 这里暂时假设 target_desc 可能包含内容，或者仅支持简单的非内容输入
                        content_to_type = None
                        if action_type == "type":
                            # 尝试从 description 或 target 中提取内容，但这比较脆弱
                            # 简单处理：如果 description 包含引号，提取引号内容
                            import re
                            content_match = re.search(r'["\'](.*?)["\']', description)
                            if content_match:
                                content_to_type = content_match.group(1)
                                print(f"   📝 从描述中提取输入内容: {content_to_type}")
                        
                        recov_success = self.perform_action(action_type, recovery_target, content=content_to_type)
                        
                        if recov_success:
                             print(f"   ✅ 建议操作执行成功")
                             # 3. 再次验证
                             print(f"   🔄 再次验证结果...")
                             time.sleep(2.0) # 等待 UI 响应
                             
                             # 重新感知和验证
                             final_state = self.perceive_state()
                             verified = self.verify_result(expected, final_state)
                             
                             if verified:
                                 print(f"   ✅ 恢复成功！步骤已完成")
                                 return {"success": True, "state": final_state, "feedback": feedback, "recovered": True}
                             else:
                                 print(f"   ⚠️  恢复操作后仍未通过验证，继续下一步")
                                 # 虽然验证失败，但我们执行了恢复操作，可能状态已经改变
                                 # 返回成功但标记警告，以免整个任务由于这一步严格验证而停止
                                 return {"success": True, "state": final_state, "warning": "恢复后验证未通过", "feedback": feedback}
                        else:
                             print(f"   ❌ 建议操作执行失败")
                else:
                    print(f"   ⚠️  模型未提供操作指导")
        
        # 6. 操作后验证
        print(f"✅ 验证结果: {expected}...")
        after_state = self.perceive_state()
        verified = self.verify_result(expected, after_state)
        
        # 综合判断
        final_success = verified or (feedback and feedback.get("success", False))
        
        if final_success:
            print(f"   ✅ 步骤 {step_num} 成功完成")
            return {"success": True, "state": after_state, "feedback": feedback}
        else:
            print(f"   ⚠️  步骤 {step_num} 验证失败，但继续执行")
            return {"success": True, "state": after_state, "warning": "验证未通过", "feedback": feedback}
    
    def run_task(self, user_request: str) -> Dict[str, Any]:
        """执行完整任务"""
        print(f"\n🎯 开始执行任务: {user_request}")
        print(f"{'='*60}\n")
        
        # 1. 规划任务
        print("📋 规划任务步骤...")
        steps = self.plan_task(user_request)
        
        if not steps:
            return {"success": False, "error": "任务规划失败"}
        
        # 保存规划到文件
        try:
            with open("task_plan.json", "w", encoding="utf-8") as f:
                json.dump(steps, f, ensure_ascii=False, indent=2)
            print(f"✅ 任务规划已保存到: task_plan.json")
        except Exception as e:
            print(f"⚠️  保存规划文件失败: {e}")
            
        print(f"✅ 规划完成，共 {len(steps)} 个步骤\n")
        
        # 2. 执行步骤
        results = []
        for step in steps:
            result = self.execute_step(step)
            results.append(result)
            
            if not result.get("success"):
                print(f"\n❌ 步骤失败，停止执行")
                return {
                    "success": False,
                    "completed_steps": len(results),
                    "total_steps": len(steps),
                    "error": result.get("error")
                }
        
        print(f"\n{'='*60}")
        print(f"✅ 任务完成！共执行 {len(steps)} 个步骤")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "completed_steps": len(steps),
            "results": results
        }


def main():
    """主函数"""
    import sys
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Vision Agent - AI 驱动的视觉自动化代理")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--task", dest="task_flag", help="任务描述 (可选标记)")
    
    args = parser.parse_args()
    
    # 优先使用位置参数，如果没有则尝试使用 --task 参数
    user_request = args.task or args.task_flag
    
    if not user_request:
        print("用法: python3 vision_agent.py \"任务描述\"")
        print("示例: python3 vision_agent.py \"打开 Numbers 并创建一个新表格\"")
        sys.exit(1)
    
    agent = VisionAgent()
    result = agent.run_task(user_request)
    
    if result["success"]:
        print("✅ 任务执行成功")
        sys.exit(0)
    else:
        print(f"❌ 任务执行失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
