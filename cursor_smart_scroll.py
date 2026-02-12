#!/usr/bin/env python3
"""
智能 Cursor 聊天框滚动脚本
使用 macOS Accessibility API 和 AI 视觉识别
"""

import subprocess
import json
import base64
import os
import tempfile
import requests
from pathlib import Path

def get_cursor_chat_area_via_ai(screenshot_path):
    """使用 AI 视觉模型识别聊天框位置"""
    # 读取截图
    with open(screenshot_path, 'rb') as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # 调用 302 平台的 GLM-4.6v-flash 识别聊天框位置
    api_key = os.getenv('PLATFORM302_API_KEY', 'sk-eQ2fzH6DQyBKCwxcsr2cNRuop90nq7kAIfHuicRBIVfaMsRW')
    
    prompt = """请分析这个 Cursor IDE 窗口截图，识别聊天面板的位置。

请返回 JSON 格式：
{
  "chat_area": {
    "x": 聊天面板左上角 X 坐标,
    "y": 聊天面板左上角 Y 坐标,
    "width": 聊天面板宽度,
    "height": 聊天面板高度,
    "center_x": 聊天面板中心 X 坐标,
    "center_y": 聊天面板中心 Y 坐标
  },
  "confidence": 0.0-1.0 的置信度
}

如果无法识别，返回 {"error": "无法识别聊天面板"}"""
    
    response = requests.post(
        "https://api.302.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "glm-4.6v-flash",
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
            "max_tokens": 500
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            import re
            json_match = re.search(r'\{[^{}]*"chat_area"[^{}]*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
    
    return None

def scroll_chat_area_apple_script(center_x, center_y, amount=15):
    """使用 AppleScript 在指定位置滚动（macOS 原生方式）"""
    print(f"🍎 使用 macOS 原生 AppleScript 滚动 {amount} 次...")
    print(f"   这是 macOS 系统原生的滚动方式，不依赖第三方工具")
    
    script = f'''
    tell application "System Events"
        tell process "Cursor"
            set frontmost to true
            delay 0.5
            
            -- 点击聊天区域聚焦
            click at {{{center_x}, {center_y}}}
            delay 0.5
            
            -- 向上滚动（使用滚轮事件，慢速滚动）
            -- 使用 key code 126 (上箭头) 模拟滚轮向上
            repeat {amount} times
                key code 126
                delay 0.12 -- 每次滚动间隔 0.12 秒，让用户能看到
            end repeat
        end tell
    end tell
    '''
    
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        total_time = amount * 0.12
        print(f"✅ macOS 原生滚动完成（{amount} 次，总耗时约 {total_time:.1f} 秒）")
        print(f"   使用方式：macOS 系统原生 AppleScript + System Events")
        return True
    else:
        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
        print(f"❌ macOS 原生滚动失败: {error_msg}")
        return False

def scroll_chat_area_peekaboo(center_x, center_y, amount=15):
    """使用 Peekaboo 在指定位置滚动"""
    print(f"👀 使用 Peekaboo 滚动 {amount} 次...")
    
    # 先点击聚焦
    click_result = subprocess.run([
        'peekaboo', 'click',
        '--app', 'Cursor',
        '--coords', f'{int(center_x)},{int(center_y)}'
    ], capture_output=True, text=True)
    
    if click_result.returncode != 0:
        print(f"⚠️  点击聚焦失败: {click_result.stderr}")
    
    import time
    time.sleep(0.5)  # 等待聚焦完成
    
    # 分多次慢速滚动，让用户能看到
    print(f"📜 开始慢速滚动（每次间隔 0.15 秒）...")
    success_count = 0
    
    for i in range(amount):
        result = subprocess.run([
            'peekaboo', 'scroll',
            '--app', 'Cursor',
            '--direction', 'up',
            '--amount', '1',  # 每次只滚动 1 个单位
            '--smooth'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            success_count += 1
            if (i + 1) % 5 == 0:
                print(f"  ✓ 已滚动 {i + 1}/{amount} 次...")
        else:
            print(f"  ⚠️  第 {i + 1} 次滚动失败: {result.stderr}")
        
        time.sleep(0.15)  # 每次滚动间隔 0.15 秒
    
    if success_count > 0:
        print(f"✅ Peekaboo 滚动完成（成功 {success_count}/{amount} 次，总耗时约 {amount * 0.15:.1f} 秒）")
        return True
    else:
        print(f"❌ Peekaboo 滚动全部失败")
        return False

def main():
    """主函数：智能滚动 Cursor 聊天框"""
    # 1. 截图
    screenshot_path = tempfile.mktemp(suffix='.png')
    result = subprocess.run([
        'peekaboo', 'image',
        '--app', 'Cursor',
        '--mode', 'window',
        '--path', screenshot_path
    ], capture_output=True)
    
    if result.returncode != 0:
        print("❌ 截图失败")
        return 1
    
    # 2. 使用 AI 识别聊天框位置
    print("🔍 使用 AI 识别聊天框位置...")
    chat_area = get_cursor_chat_area_via_ai(screenshot_path)
    
    if not chat_area or 'error' in chat_area:
        print("⚠️  AI 无法识别聊天框，使用默认位置")
        # 使用默认位置（窗口右侧 75% 处，垂直居中）
        window_info = subprocess.run(
            ['peekaboo', 'list', 'windows', '--app', 'Cursor', '--json'],
            capture_output=True,
            text=True
        )
        
        if window_info.returncode == 0:
            try:
                windows = json.loads(window_info.stdout)
                if windows.get('data', {}).get('windows'):
                    bounds = windows['data']['windows'][0].get('bounds', [[0, 0], [1370, 875]])
                    window_width = bounds[1][0]
                    window_height = bounds[1][1]
                    center_x = window_width * 0.75
                    center_y = window_height * 0.5
                else:
                    center_x, center_y = 1000, 500
            except:
                center_x, center_y = 1000, 500
        else:
            center_x, center_y = 1000, 500
    else:
        center_x = chat_area['chat_area']['center_x']
        center_y = chat_area['chat_area']['center_y']
        confidence = chat_area.get('confidence', 0)
        print(f"✅ 识别到聊天框位置: ({center_x:.0f}, {center_y:.0f}), 置信度: {confidence:.2f}")
    
    # 3. 滚动（大幅慢速滚动，让用户能看到）
    scroll_amount = 15  # 滚动次数（从 5 增加到 15）
    print(f"📜 在位置 ({center_x:.0f}, {center_y:.0f}) 滚动聊天框...")
    print(f"📊 滚动参数：{scroll_amount} 次，慢速模式（每次间隔 0.1-0.15 秒）")
    print("=" * 50)
    
    # 先截图记录滚动前状态
    before_screenshot = tempfile.mktemp(suffix='_before.png')
    subprocess.run([
        'peekaboo', 'image',
        '--app', 'Cursor',
        '--mode', 'window',
        '--path', before_screenshot
    ], capture_output=True)
    
    # 优先使用 macOS 原生方式（AppleScript）
    print("\n🎯 尝试方式 1: macOS 原生 AppleScript 滚动")
    print("-" * 50)
    scroll_success = False
    
    if scroll_chat_area_apple_script(center_x, center_y, scroll_amount):
        scroll_success = True
        scroll_method = "macOS 原生 (AppleScript)"
    else:
        # 备选：使用 Peekaboo
        print("\n🎯 尝试方式 2: Peekaboo 滚动（备选）")
        print("-" * 50)
        if scroll_chat_area_peekaboo(center_x, center_y, scroll_amount):
            scroll_success = True
            scroll_method = "Peekaboo（备选）"
        else:
            print("\n❌ 所有滚动方式都失败了")
            os.unlink(before_screenshot)
            return 1
    
    # 等待滚动完成
    import time
    time.sleep(0.5)
    
    # 截图验证滚动效果
    after_screenshot = tempfile.mktemp(suffix='_after.png')
    subprocess.run([
        'peekaboo', 'image',
        '--app', 'Cursor',
        '--mode', 'window',
        '--path', after_screenshot
    ], capture_output=True)
    
    # 比较截图
    if os.path.exists(before_screenshot) and os.path.exists(after_screenshot):
        import hashlib
        def md5_file(path):
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        
        before_hash = md5_file(before_screenshot)
        after_hash = md5_file(after_screenshot)
        
        print("\n" + "=" * 50)
        print("📊 滚动验证结果：")
        print(f"  滚动前截图 MD5: {before_hash[:16]}...")
        print(f"  滚动后截图 MD5: {after_hash[:16]}...")
        
        if before_hash != after_hash:
            print(f"✅ 截图已变化，滚动生效！使用方式: {scroll_method}")
        else:
            print(f"⚠️  截图未变化，可能已到顶部或内容相同")
            print(f"   使用方式: {scroll_method}")
        
        # 保留截图供检查
        print(f"\n📸 截图已保存：")
        print(f"   滚动前: {before_screenshot}")
        print(f"   滚动后: {after_screenshot}")
    
    print("\n" + "=" * 50)
    print(f"✅ 滚动完成！使用方式: {scroll_method}")
    
    # 不删除截图，让用户检查
    # os.unlink(before_screenshot)
    # os.unlink(after_screenshot)
    
    # 清理
    os.unlink(screenshot_path)
    return 0

if __name__ == '__main__':
    exit(main())
