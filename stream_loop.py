"""Read JSON lines as they arrive, retaining a wall-clock timeout."""
import json
import subprocess
import tempfile
import threading


def messages(cmd, payload, timeout, **options):
    with tempfile.TemporaryFile(mode="w+") as source:
        source.write(payload)
        source.seek(0)
        with subprocess.Popen(cmd, stdin=source, stdout=subprocess.PIPE,
                              text=True, **options) as proc:
            timer = threading.Timer(timeout, proc.kill)
            timer.start()
            try:
                for line in proc.stdout:
                    if line.strip():
                        yield json.loads(line)
                if proc.wait():
                    raise RuntimeError(f"{cmd[0]} exited with status {proc.returncode}")
            finally:
                timer.cancel()
                if proc.poll() is None:
                    proc.kill()
