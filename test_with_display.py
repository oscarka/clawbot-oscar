#!/usr/bin/env python3
"""
带可视化显示的测试脚本
实时更新状态到显示界面
"""

import subprocess
import time
import os
import sys
from pathlib import Path
from datetime import datetime

STATUS_FILE = Path("/tmp/vision_agent_status.txt")
LOG_FILE = Path("/tmp/vision_agent_status.log")
COMMAND_LOG = Path("/tmp/vision_agent_commands.log")

def log_command(command, status='executing'):
    """记录执行的命令"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {status.upper()}: {command}\n"
    
    with open(COMMAND_LOG, 'a') as f:
        f.write(log_entry)

def update_status(status: str, details: str = ""):
    """更新状态文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_text = f"""
{'='*60}
状态: {status}
时间: {timestamp}
{'='*60}
{details}
"""
    
    STATUS_FILE.write_text(status_text)
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {status}: {details}\n")
    
    # 终端输出
    colors = {
        "进行中": "\033[92m",
        "卡住了": "\033[93m",
        "中断了": "\033[91m",
        "完成": "\033[94m",
    }
    reset = "\033[0m"
    color = colors.get(status, "")
    print(f"{color}📊 [{timestamp}] {status}: {details}{reset}")
    sys.stdout.flush()

def send_notification(message: str):
    """发送 macOS 通知"""
    subprocess.run([
        'osascript', '-e',
        f'display notification "{message}" with title "Vision Agent"'
    ], capture_output=True)

def test_peekaboo_agent():
    """测试 Peekaboo Agent"""
    update_status("进行中", "测试 Peekaboo Agent 模式...")
    log_command("peekaboo learn", "executing")
    
    try:
        result = subprocess.run(
            ['peekaboo', 'learn'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if 'agent' in result.stdout.lower() or 'tool' in result.stdout.lower():
            update_status("进行中", "Peekaboo 支持 Agent 模式！")
            log_command("peekaboo learn", "success")
            return True
        else:
            update_status("中断了", "Peekaboo 可能不支持 Agent 模式")
            log_command("peekaboo learn", "error")
            return False
    except Exception as e:
        update_status("中断了", f"Peekaboo 测试失败: {e}")
        log_command("peekaboo learn", "error")
        return False

def test_peekaboo_agent_task():
    """使用 Peekaboo Agent 执行任务（实际执行）"""
    update_status("进行中", "使用 Peekaboo Agent 执行任务...")
    task = "用飞书发送一个本地文件给自己的文件助手"
    log_command(f"peekaboo agent '{task}'", "executing")
    
    try:
        # 方法1: 直接使用 Peekaboo Agent
        update_status("进行中", "启动 Peekaboo Agent...")
        log_command("启动 Peekaboo Agent", "executing")
        
        process = subprocess.Popen(
            ['peekaboo', 'agent', task],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 实时读取输出并更新状态
        last_status_update = time.time()
        step_count = 0
        
        for line in process.stdout:
            print(line, end='')
            sys.stdout.flush()
            
            # 解析 Peekaboo Agent 的输出
            line_lower = line.lower()
            
            if 'step' in line_lower or '步骤' in line:
                step_count += 1
                update_status("进行中", f"执行步骤 {step_count}...")
                log_command(f"步骤 {step_count}", "executing")
            elif 'see' in line_lower or 'screenshot' in line_lower or '截图' in line:
                update_status("进行中", "分析界面状态...")
                log_command("分析界面", "executing")
            elif 'click' in line_lower or '点击' in line:
                update_status("进行中", "执行点击操作...")
                log_command("点击操作", "executing")
            elif 'type' in line_lower or '输入' in line:
                update_status("进行中", "执行输入操作...")
                log_command("输入操作", "executing")
            elif 'success' in line_lower or '成功' in line or '✅' in line:
                update_status("进行中", "操作成功，继续...")
                log_command("操作成功", "success")
            elif 'error' in line_lower or '失败' in line or '❌' in line:
                update_status("卡住了", f"检测到错误: {line[:50]}")
                log_command(f"错误: {line[:50]}", "error")
            elif 'complete' in line_lower or '完成' in line:
                update_status("完成", "任务执行完成！")
                log_command("任务完成", "success")
            
            # 每2秒更新一次状态
            if time.time() - last_status_update > 2:
                update_status("进行中", f"正在执行中... (已执行 {step_count} 步)")
                last_status_update = time.time()
        
        process.wait()
        
        if process.returncode == 0:
            update_status("完成", "Peekaboo Agent 任务执行成功！")
            log_command("任务完成", "success")
            return True
        else:
            update_status("中断了", "Peekaboo Agent 任务执行失败")
            log_command("任务失败", "error")
            return False
            
    except subprocess.TimeoutExpired:
        update_status("卡住了", "任务执行超时")
        log_command("任务超时", "error")
        return False
    except Exception as e:
        update_status("中断了", f"Peekaboo Agent 测试失败: {e}")
        log_command(f"异常: {e}", "error")
        # 如果 Peekaboo Agent 失败，尝试使用 vision_agent
        update_status("进行中", "Peekaboo Agent 不可用，使用 Vision Agent...")
        return test_vision_agent_task(task)

def test_vision_agent_task(task):
    """使用 Vision Agent 执行任务（备选方案）"""
    update_status("进行中", "使用 Vision Agent 执行任务...")
    log_command(f"vision_agent.py '{task}'", "executing")
    
    try:
        process = subprocess.Popen(
            ['python3', str(Path(__file__).parent / 'vision_agent.py'), task],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        last_status_update = time.time()
        for line in process.stdout:
            print(line, end='')
            sys.stdout.flush()
            
            if '执行步骤' in line:
                step_info = line.split('执行步骤')[1].strip() if '执行步骤' in line else ''
                update_status("进行中", f"执行步骤: {step_info}")
                log_command(f"执行步骤: {step_info}", "executing")
            elif '成功完成' in line or '✅' in line:
                update_status("进行中", "步骤执行成功，继续...")
                log_command("步骤成功", "success")
            elif '失败' in line or '❌' in line:
                update_status("卡住了", f"检测到失败: {line[:50]}")
                log_command(f"步骤失败: {line[:50]}", "error")
            elif '定位目标' in line:
                target = line.split('定位目标:')[1].strip() if '定位目标:' in line else ''
                update_status("进行中", f"定位目标: {target[:30]}")
            
            if time.time() - last_status_update > 2:
                last_status_update = time.time()
        
        process.wait()
        
        if process.returncode == 0:
            update_status("完成", "Vision Agent 任务执行成功！")
            return True
        else:
            update_status("中断了", "Vision Agent 任务执行失败")
            return False
    except Exception as e:
        update_status("中断了", f"Vision Agent 失败: {e}")
        return False

def main():
    """主测试流程"""
    print("🚀 开始测试（带可视化显示）")
    print("📊 打开浏览器查看: http://localhost:8888")
    print("="*60)
    
    # 启动状态服务器（后台）
    server_process = subprocess.Popen(
        ['python3', str(Path(__file__).parent / 'status_server.py'), '8888'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    time.sleep(2)  # 等待服务器启动
    
    # 打开浏览器
    try:
        subprocess.Popen([
            'open', 'http://localhost:8888'
        ], capture_output=True)
    except:
        pass
    
    update_status("进行中", "初始化测试...")
    send_notification("开始测试")
    
    # 测试
    results = {}
    
    print("\n" + "="*60)
    print("测试 1: Peekaboo Agent 模式")
    print("="*60)
    results['peekaboo'] = test_peekaboo_agent()
    time.sleep(1)
    
    print("\n" + "="*60)
    print("测试 2: Peekaboo Agent 执行任务")
    print("="*60)
    results['agent_task'] = test_peekaboo_agent_task()
    time.sleep(1)
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    update_status("完成", "所有测试完成")
    send_notification("测试完成")
    
    print(f"\n📊 状态文件: {STATUS_FILE}")
    print(f"📝 日志文件: {LOG_FILE}")
    print(f"🌐 监控界面: http://localhost:8888")
    
    # 不停止服务器，让用户继续查看
    print("\n按 Ctrl+C 停止服务器")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        update_status("中断了", "用户中断测试")
        send_notification("测试被中断")
        sys.exit(1)
    except Exception as e:
        update_status("中断了", f"测试异常: {e}")
        send_notification(f"测试异常: {e}")
        raise
