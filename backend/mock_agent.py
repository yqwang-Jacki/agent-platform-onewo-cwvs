from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockAgentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        messages = data.get('messages', [])
        last = messages[-1] if messages else {"content": ""}
        user_msg = last.get('content', '')

        response = {
            "content": f"[模拟回复] 已收到你的消息：{user_msg}\n\n（这是 Mock Agent 返回的固定回复，用于测试端到端链路）",
            "tokens_used": 12,
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 9999), MockAgentHandler)
    print("Mock Agent listening on http://127.0.0.1:9999")
    server.serve_forever()
