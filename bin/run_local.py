"""Start a loopback-only production server with a stable private local signing key."""

import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
if len(sys.argv) > 1:
    raise SystemExit(
        "Use FEMAKTIV_PORT to configure the local server; extra arguments are unsupported."
    )
os.chdir(root)
state = root / ".local"
state.mkdir(mode=0o700, exist_ok=True)
state.chmod(0o700)
key_file = state / "secret_key"
try:
    with open(key_file, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
        output.write(secrets.token_urlsafe(64))
except FileExistsError:
    pass

environment = dict(os.environ)
environment.pop("GUNICORN_CMD_ARGS", None)
environment.update(
    {
        "DJANGO_DEBUG": "0",
        "DJANGO_LOCAL_HTTP": "1",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
        "DJANGO_SECRET_KEY": key_file.read_text().strip(),
    }
)
port = int(environment.get("FEMAKTIV_PORT", "8000"))
if not 1024 <= port <= 65535:
    raise SystemExit("FEMAKTIV_PORT must be between 1024 and 65535.")
print(
    f"femaktiv: http://127.0.0.1:{port}/ (English) · http://127.0.0.1:{port}/de/ (Deutsch)",
    flush=True,
)
executable = str(root / ".venv/bin/gunicorn")
os.execve(
    executable,
    [
        executable,
        "config.wsgi:application",
        "--bind",
        f"127.0.0.1:{port}",
        "--workers",
        "1",
        "--threads",
        "2",
        "--timeout",
        "30",
    ],
    environment,
)
