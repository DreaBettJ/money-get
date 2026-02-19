#!/usr/bin/env python3
"""简单日志服务器 - 远程查看 money-get 日志"""
import http.server
import socketserver
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
PORT = 8890

class LogHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            log_list = self._list_logs()
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Money-Get Logs</title></head>
<body>
<h1>📈 Money-Get 日志</h1>
<h2><a href="/money_get.log">运行日志</a></h2>
<h2><a href="/trade_20260219.log">交易日志</a></h2>
<ul>{log_list}</ul>
</body></html>"""
            self.wfile.write(html.encode("utf-8"))
        else:
            super().do_GET()
    
    def _list_logs(self):
        files = []
        for f in LOG_DIR.glob("*.log"):
            files.append(f"<li><a href='/{f.name}'>{f.name}</a> ({f.stat().st_size} bytes)</li>")
        return "\n".join(files) if files else "<li>暂无日志</li>"

print(f"📡 日志服务启动: http://localhost:{PORT}")
print(f"📁 日志目录: {LOG_DIR}")
with socketserver.TCPServer(("", PORT), LogHandler) as httpd:
    httpd.serve_forever()
