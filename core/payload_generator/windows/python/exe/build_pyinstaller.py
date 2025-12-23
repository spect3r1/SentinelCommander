import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from colorama import init, Fore, Style

init()

brightgreen = Style.BRIGHT + Fore.GREEN
brightred = Style.BRIGHT + Fore.RED
reset = Style.RESET_ALL

WINEPREFIX = os.path.expanduser("~/wine-py")
WINE_PYTHON = "python"  # resolved inside wine
WINE = "wine"

def build(output_path: Path, payload_code: str) -> bool:
    """
    Build a Windows executable using Wine + PyInstaller.
    """

    tempdir = Path(tempfile.mkdtemp(prefix="py_build_"))
    wine_drive_c = Path(WINEPREFIX) / "drive_c"
    wine_build_dir = wine_drive_c / "pybuild"

    try:
        # Ensure Wine build directory exists
        wine_build_dir.mkdir(parents=True, exist_ok=True)

        # Write payload locally
        script_path = tempdir / "implant.py"
        script_path.write_text(payload_code, encoding="utf-8")

        # Copy script into Wine C:\
        wine_script_path = wine_build_dir / "implant.py"
        shutil.copy(script_path, wine_script_path)

        # Windows-style paths
        win_script = r"C:\pybuild\implant.py"
        win_dist = r"C:\pybuild\dist"
        win_build = r"C:\pybuild\build"

        cmd = [
            WINE,
            WINE_PYTHON,
            "-m",
            "PyInstaller",
            "--onefile",
            "--noconsole",
            "--clean",
            "--name", "SentinelPython",
            "--distpath", win_dist,
            "--workpath", win_build,
            win_script
        ]

        env = os.environ.copy()
        env["WINEPREFIX"] = WINEPREFIX

        print(f"[*] Running PyInstaller via Wine...")

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(brightred + "[!] PyInstaller failed" + reset)
            print(result.stderr)
            return False

        # Resulting EXE path
        exe_path = wine_build_dir / "dist" / "SentinelPython.exe"

        if not exe_path.exists():
            print(brightred + "[!] EXE not found after build" + reset)
            return False

        shutil.copy(exe_path, output_path)
        print(brightgreen + f"[+] Built Windows EXE → {output_path}" + reset)
        return True

    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
