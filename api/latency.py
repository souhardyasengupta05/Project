from http.server import BaseHTTPRequestHandler
import json
import statistics

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/latency':
            self.handle_latency()
        else:
            self.send_error(404)
    
    def handle_latency(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data)
            
            # Your latency calculation logic here
            # ... (same as before)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
