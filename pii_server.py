import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from spacy_detector import SpacyNERPIIDetector

class Model:
    def __init__(self):
        self.is_loaded = False
        self.model_path = os.getenv("SPACY_MODEL_PATH", "extracted_model/en_core_web_trf/en_core_web_trf-3.8.0")

    def load(self):
        print(f"Loading {self.model_path}...")
        self.is_loaded = True
        detector = SpacyNERPIIDetector(model_path=self.model_path)
        self.detector = detector
        print(f"{self.model_path} loaded successfully!")

    def infer(self, input_text):
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        print(f"Processing inference: {input_text}")
        result = self.detector.detect_pii_combined(input_text)
        return result

model = Model()

class ModelHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/infer':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                input_text = data.get('input', '')

                response = model.infer(input_text)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"output": response}).encode('utf-8'))

            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

def main():
    print("Starting model server...")
    model.load()

    server = HTTPServer(('localhost', 0), ModelHandler)
    port = server.server_address[1]
    print(f"SERVER_PORT:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
