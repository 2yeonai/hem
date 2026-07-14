from __future__ import annotations

import subprocess
import sys
from pathlib import Path


root = Path(__file__).resolve().parent
python = root / "work" / ".venv" / "Scripts" / "python.exe"
stdout_path = root / "work" / "media-transcription.out.log"
stderr_path = root / "work" / "media-transcription.err.log"
command = [
    str(python), "convert_to_obsidian.py", "--phase", "media",
    "--whisper-model", "base", "--match", ".m4a", "--skip-existing",
]

stdout = stdout_path.open("w", encoding="utf-8")
stderr = stderr_path.open("w", encoding="utf-8")
flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
process = subprocess.Popen(command, cwd=root, stdout=stdout, stderr=stderr, creationflags=flags)
stdout.close()
stderr.close()
print(process.pid)
