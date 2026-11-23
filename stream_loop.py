"""Read JSON lines as they arrive, retaining a wall-clock timeout."""
import json
import subprocess
import tempfile
import threading


def messages(cmd, payload, timeout, *, on_stderr=None, **options):
    with tempfile.TemporaryFile(mode="w+") as source:
        source.write(payload)
        source.seek(0)
        if on_stderr is not None:
            options["stderr"] = subprocess.PIPE
        with subprocess.Popen(cmd, stdin=source, stdout=subprocess.PIPE,
                              text=True, **options) as proc:
            timer = threading.Timer(timeout, proc.kill)
            timer.start()
            if on_stderr is not None:
                def read_stderr():
                    for line in proc.stderr:
                        on_stderr(line)
                reader = threading.Thread(target=read_stderr, daemon=True)
                reader.start()
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
                if on_stderr is not None:
                    reader.join()
