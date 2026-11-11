"""Credential-holding host gateway; only the OpenAI Responses endpoint is reachable."""
from contextlib import AbstractContextManager
from http.server import BaseHTTPRequestHandler
import os
import json
from pathlib import Path
import socketserver
import threading
import urllib.error
import urllib.request

LIMIT = 4 * 1024 * 1024

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            length = -1
        if self.path != '/v1/responses' or not 0 < length <= LIMIT or self.headers.get('Transfer-Encoding'):
            self.send_error(403)
            return
        self.connection.settimeout(30)
        body = self.rfile.read(length)
        request = urllib.request.Request(self.server.endpoint, data=body,
                    headers=self.server.headers, method='POST')
        try:
            # No redirects: a credential must never follow an upstream redirect.
            opener = urllib.request.build_opener(NoRedirect)
            with opener.open(request, timeout=60) as response:
                self.send_response(response.status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self.end_headers()
                total = 0
                while chunk := response.read1(65536):
                    total += len(chunk)
                    if total > 16 * LIMIT:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (OSError, urllib.error.URLError):
            # Never send upstream headers, credential values, or bodies back on errors.
            self.close_connection = True

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(30)
        return request, address

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

class Gateway(AbstractContextManager):
    def __init__(self, path, auth_file=None):
        self.path = Path(path)
        self.auth_file = auth_file or Path.home() / ".codex/auth.json"

    def __enter__(self):
        key = os.environ.get('OPENAI_API_KEY')
        auth = {}
        if not key and self.auth_file.is_file():
            auth = json.loads(self.auth_file.read_text())
            key = auth.get('OPENAI_API_KEY')
        endpoint = 'https://api.openai.com/v1/responses'
        headers = {'Content-Type': 'application/json'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        else:
            tokens = auth.get('tokens') or {}
            token, account = tokens.get('access_token'), tokens.get('account_id')
            if not token or not account:
                raise ValueError('Configure OPENAI_API_KEY or log in to the host Codex CLI first')
            endpoint = 'https://chatgpt.com/backend-api/codex/responses'
            headers.update({'Authorization': 'Bearer ' + token, 'ChatGPT-Account-Id': account})
        self.server = Server(str(self.path), Handler)
        self.server.endpoint = endpoint
        self.server.headers = headers
        os.chmod(self.path, 0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.path.unlink(missing_ok=True)
