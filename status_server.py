#!/usr/bin/env python3
"""
状态服务器：提供实时状态更新
通过 HTTP 服务器提供状态文件和日志
"""

import http.server
import socketserver
import os
from pathlib import Path
import json
from datetime import datetime

STATUS_FILE = Path("/tmp/vision_agent_status.txt")
LOG_FILE = Path("/tmp/vision_agent_status.log")
COMMAND_LOG = Path("/tmp/vision_agent_commands.log")

from urllib.parse import urlparse

class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path_only = parsed_path.path
        
        if path_only == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 读取状态
            status_data = {
                "status": "进行中",
                "details": "",
                "timestamp": datetime.now().isoformat(),
                "commands": []
            }
            
            if STATUS_FILE.exists():
                content = STATUS_FILE.read_text()
                for line in content.split('\n'):
                    if line.startswith('状态:'):
                        status_data["status"] = line.split('状态:')[1].strip()
                    elif line.strip() and not line.startswith('=') and not line.startswith('时间:'):
                        status_data["details"] = line.strip()
            
            # 读取命令日志
            if COMMAND_LOG.exists():
                commands = COMMAND_LOG.read_text().strip().split('\n')
                status_data["commands"] = commands[-20:]  # 最近20条
            
            self.wfile.write(json.dumps(status_data, ensure_ascii=False).encode('utf-8'))
            
        elif path_only == '/status.txt':
            # 直接返回状态文件
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if STATUS_FILE.exists():
                self.wfile.write(STATUS_FILE.read_text().encode('utf-8'))
            else:
                self.wfile.write('状态文件不存在'.encode('utf-8'))
                
        elif path_only == '/log':
            # 返回日志
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if LOG_FILE.exists():
                self.wfile.write(LOG_FILE.read_text().encode('utf-8'))
            else:
                self.wfile.write('日志文件不存在'.encode('utf-8'))
        else:
            # 返回 HTML 文件
            if path_only == '/' or path_only == '/index.html':
                self.path = '/status_display.html'
            super().do_GET()
    
    def log_message(self, format, *args):
        # 不输出访问日志
        pass

def start_server(port=8888):
    """启动状态服务器"""
    os.chdir(Path(__file__).parent)
    
    with socketserver.TCPServer(("", port), StatusHandler) as httpd:
        print(f"🚀 状态服务器启动: http://localhost:{port}")
        print(f"📊 监控界面: http://localhost:{port}/")
        print("按 Ctrl+C 停止服务器")
        httpd.serve_forever()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    start_server(port)
