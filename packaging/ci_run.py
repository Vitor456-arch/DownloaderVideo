"""Preserve command status and expose failure details in GitHub check annotations."""
import os
import subprocess
import sys

result = subprocess.run(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
print(result.stdout, end="", flush=True)
if result.returncode and os.environ.get("GITHUB_ACTIONS"):
    tail = result.stdout[-40000:]
    for offset in range(0, len(tail), 4000):
        text = tail[offset:offset + 4000].replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::error title=Command failure::" + text, flush=True)
raise SystemExit(result.returncode)
