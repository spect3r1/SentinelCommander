import queue
import random
import string
import sys

class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.output_queue = queue.Queue()
        self.tcp_listener_socket = {}

    def gen_session_id(self):
        parts = []
        for _ in range(3):
            parts.append(''.join(random.choices(string.ascii_letters + string.digits, k=4)))
        return '-'.join(parts)
    
    def register_http_session(self, sid):
        if sid not in self.sessions:
            self.sessions[sid] = queue.Queue()
        
    def register_tcp_session(self, client_socket):
        sid = self.gen_session_id()
        self.sessions[sid] = client_socket
        return sid
    
    def close_all_tcp_listeners(self):
        for name, sock in self.tcp_listener_socket.items():
            try:
                sock.close()
            except Exception:
                pass
            del self.tcp_listener_socket[name]