"""Runs INSIDE the network namespace; forwards only to the credential-free Unix socket."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import socket
import subprocess
import sys
import threading

class Connection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(90)
        self.sock.connect('/run/keno-api.sock')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if self.path != '/v1/responses' or not 0 < length <= 4 * 1024 * 1024:
                self.send_error(403)
                return
            connection = Connection('localhost', timeout=90)
            connection.request('POST', '/v1/responses', self.rfile.read(length),
                               {'Content-Type': 'application/json'})
            response = connection.getresponse()
            self.send_response(response.status)
            self.send_header('Content-Type', response.getheader('Content-Type', 'application/json'))
            self.end_headers()
            while chunk := response.read1(65536):
                self.wfile.write(chunk)
                self.wfile.flush()
            connection.close()
        except (OSError, ValueError, http.client.HTTPException):
            self.close_connection = True

if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run(sys.argv[1:])
    finally:
        server.shutdown()
    sys.exit(result.returncode)
