import random
import string
import os, sys
import logging
import re
from core.session_handlers import session_manager
from core.teamserver import operator_manager as op_manage
from colorama import init, Fore, Style

brightgreen = "\001" + Style.BRIGHT + Fore.GREEN + "\002"
brightyellow = "\001" + Style.BRIGHT + Fore.YELLOW + "\002"
brightred = "\001" + Style.BRIGHT + Fore.RED + "\002"
brightblue = "\001" + Style.BRIGHT + Fore.BLUE + "\002"

tcp_listener_sockets = {}
tls_listener_sockets = {}
http_listener_sockets = {}
https_listener_sockets = {}
portforwards = {}

logger = logging.getLogger(__name__)

class SessionDefender:
	def __init__(self):
		self.is_active = True

		# commands that spawn a new shell / interpreter on Windows
		self.win_dangerous = {
			"powershell", "powershell.exe", "cmd", "cmd.exe",
			"curl", "wget", "telnet",
			"python", "python3", "php", "ruby", "irb", "perl",
			"jshell", "node", "ghci"
		}

		# editors & shells on Linux + same interpreters
		self.linux_dangerous = {
			"bash", "sh", "zsh", "tclsh",
			"less", "more", "nano", "pico", "vi", "vim", "gedit", "atom", "emacs", "telnet"
		} | self.win_dangerous

		# regexes for unclosed quotes/backticks on Linux (backslash escapes)
		self._linux_pairings = [
			(r"(?<!\\)'", "'"),
			(r'(?<!\\)"', '"'),
			(r"(?<!\\)`", "`"),
		]
		# regexes for unclosed quotes on Windows (backtick escapes)
		self._win_pairings = [
			(r"(?<!`)'",  "'"),
			(r'(?<!`)"',  '"'),
			# we drop the backtick‐pairing on Windows to avoid confusion
		]

	def inspect_command(self, os_type: str, cmd: str) -> bool:
		"""
		Return True if the command is safe to send, False if it should be blocked.
		"""

		if not cmd:
			return True

		if not self.is_active:
			return True

		# 1) Unclosed quotes/backticks
		if os_type == "windows":
			pairings = self._win_pairings
			
		else:
			pairings = self._linux_pairings

		for pattern, char in pairings:
			count = len(re.findall(pattern, cmd))
			if count % 2 != 0:
				logger.debug(f"Blocked command {cmd!r} for unclosed {char}s (found {count})")
				return False

		# 2) Trailing backslash (Linux only)
		if os_type == "linux" and cmd.rstrip().endswith("\\"):
			logger.debug(brightred + f"Blocked command {cmd} on linux agent for ending in a backslash")
			return False

		# 3) Dangerous binaries
		first = cmd.strip().split()[0].lower()
		if os_type == "windows":
			if first in self.win_dangerous:
				return False
		else:
			if first in self.linux_dangerous:
				return False

		# safe
		return True


def gen_session_id():
	return '-'.join(
		''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
		for _ in range(3)
	)

PROMPT_PATTERNS = [
	re.compile(r"^PS [^>]+> ?"),         # PowerShell prompt
	re.compile(r"^[\w\-\@]+[:~\w\/-]*[#$] ?"), # bash/zsh prompt
	re.compile(r"^[A-Za-z]:\\.*> ?"),  #CMD shell prompt
	# add more if you spawn e.g. cmd.exe, fish, etc.
]

WRAPPER_ARTIFACTS = {
	'";',              # the stray semicolon+quote line
	'Write-Output "',  # the trailing half-marker line
}

def normalize_output(raw: str, last_cmd: str) -> str:
	"""
	1) Strip the echoed command
	2) Remove any lines matching known prompts
	3) Drop our leftover wrapper artifacts ("; and Write-Output ")
	4) Trim leading/trailing whitespace
	"""
	lines = raw.splitlines()
	cleaned = []

	for line in lines:
		s = line.strip()

		# 1) drop an exact echo of our command
		if s == last_cmd.strip():
			continue

		# 2) drop any PS/CMD/bash prompts
		if any(pat.match(line) for pat in PROMPT_PATTERNS):
			continue

		# 3) drop any pure wrapper‐artifact lines
		if s in WRAPPER_ARTIFACTS:
			continue

		if re.match(r"^__OP__[^_]+__$", s):
			continue

		cleaned.append(line)

	return "\n".join(cleaned).strip()

def echo(msg: str, to_console, to_op, world_wide, color=False, _raw_printer=print, end="\n"):
    # Simplified echo for API-only mode
    #logger.debug("echo: %r", msg)

    if color:
        msg = color + msg

    if world_wide:
        for ident, obj in op_manage.operators.items():
            sock = obj.handler
            if sock:
                try:
                    sock.send((msg + end).encode())
                except:
                    pass
        print(msg) # For local logs/capture

    elif to_op:
        operator = op_manage.operators.get(to_op)
        if operator and operator.handler:
            try:
                operator.handler.sendall((msg + end).encode())
            except:
                pass

    elif to_console:
        print(msg)


def list_sessions():
	if not session_manager.sessions:
		print(brightyellow + "[*] No sessions connected.")
		return  # <- stop here so the header/bar isn’t printed

	print(brightgreen + (f"{'SID':<20} {'Alias':<15} {'Transport':<10} {'Hostname':<20} {'User':<25} {'OS':<10} {'Arch':<10}"))
	print(brightgreen +("-" * 110))

	for sid, session in session_manager.sessions.items():
		transport = session.transport
		meta = session.metadata

		hostname = meta.get("hostname", "N/A")
		user = meta.get("user", "N/A")
		os_info = meta.get("os")
		arch = meta.get("arch", "N/A")

		# Resolve alias if set
		alias = "N/A"
		for a, real_sid in session_manager.alias_map.items():
			if real_sid == sid:
				alias = a
				break


		if sid is None or transport is None or hostname is None or user is None or os_info is None or arch is None or alias is None:
			print(brightyellow + "Fetching metadata from agent please wait")
			continue
		else:
			print(brightred + (f"{sid:<20} {alias:<15} {transport:<10} {hostname:<20} {user:<25} {os_info:<10} {arch:<10}"))


def list_listeners():
	if not tcp_listener_sockets and not http_listener_sockets and not tls_listener_sockets and not https_listener_sockets:
		print(brightyellow + "No active listeners.")
	else:
		if http_listener_sockets:
			print(brightgreen + "\n[HTTP Listeners]")
			for name in http_listener_sockets:
				print(brightgreen + (f"- {name}"))

		if https_listener_sockets:
			print(brightgreen + "\n[HTTPS Listeners]")
			for name in https_listener_sockets:
				print(brightgreen + (f"- {name}"))

		if tcp_listener_sockets:
			print(brightgreen + "\n[TCP Listeners]")
			for name in tcp_listener_sockets:
				print(brightgreen + (f"- {name}"))

		if tls_listener_sockets:
			print(brightgreen + "\n[TLS Listeners]")
			for name in tls_listener_sockets:
				print(brightgreen + (f"- {name}"))

def shutdown():
	try:
		for name, sock in tcp_listener_sockets.items():
			try:
				sock.close()
				print(brightyellow + f"Closed TCP {name}")

			except:
				pass

	except Exception:
		pass

	try:
		for name, sock in tls_listener_sockets.items():
			try:
				sock.close()
				print(brightyellow + f"Closed TLS {name}")

			except:
				pass

	except Exception:
		pass	

	try:
		for name, httpd in http_listener_sockets.items():
			try:
				httpd.shutdown()
				print(brightyellow + f"Closed HTTP {name}")

			except Exception as e:
				print(brightred + f"[!] Failed to shutdown HTTP {name}: {e}")

	except Exception:
		pass

	try:
		for name, httpd in https_listener_sockets.items():
			try:
				httpd.shutdown()
				print(brightyellow + f"Closed HTTPS {name}")

			except Exception as e:
				print(brightred + f"[!] Failed to shutdown HTTPS {name}: {e}")

	except Exception:
		pass



def register_forward(rule_id, sid, local_host, local_port, remote_host, remote_port, thread, listener):
	"""
	Register an active port-forward rule.

	Args:
		rule_id (str): Unique identifier for this forward.
		sid (str): Session ID.
		local_host (str): Local host/interface to bind.
		local_port (int): Local port to listen on.
		remote_host (str): Remote host to forward to.
		remote_port (int): Remote port to forward to.
		thread (threading.Thread): Thread handling this forward.
		listener (socket.socket): Listening socket for this forward.
	"""
	display = next((a for a, rsid in session_manager.alias_map.items() if rsid == sid), sid)
	portforwards[rule_id] = {
		"sid": display,
		"local_host": local_host,
		"local": local_port,
		"remote": f"{remote_host}:{remote_port}",
		"thread": thread,
		"listener": listener
	}

def unregister_forward(rule_id):
	"""
	Remove and stop a port-forward rule, closing its listener and joining its thread.
	"""
	entry = portforwards.pop(rule_id, None)
	if not entry:
		return
		
	try:
		entry["listener"].close()

	except:
		pass

	entry["thread"].join(timeout=1)

def list_forwards():
	"""
	Return all currently registered port-forward rules.
	"""
	return portforwards

# ----- helpers -----
defender = SessionDefender()