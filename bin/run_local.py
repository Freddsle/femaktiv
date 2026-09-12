"""Serve locally or through an explicit HTTPS tunnel, always bound to loopback."""

import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent


def public_origin(value):
    """Accept one HTTPS origin, never wildcard hosts, credentials or URL paths."""
    error = "FEMAKTIV_PUBLIC_URL must be an HTTPS origin, e.g. https://your-domain.ngrok-free.app."
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        valid_host = (
            "." in host
            and len(host) <= 253
            and all(re.fullmatch(r"(?!-)[a-z0-9-]{1,63}(?<!-)", part) for part in host.split("."))
        )
        if (
            url.scheme != "https"
            or not valid_host
            or url.port not in (None, 443)
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or any(character.isspace() for character in value)
        ):
            raise ValueError
    except ValueError:
        raise SystemExit(error) from None
    return f"https://{host}", host


def main():
    if len(sys.argv) > 1:
        raise SystemExit(
            "Use FEMAKTIV_PORT to configure the local server; extra arguments are unsupported."
        )
    environment = dict(os.environ)
    try:
        port = int(environment.get("FEMAKTIV_PORT", "8000"))
        if not 1024 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("FEMAKTIV_PORT must be between 1024 and 65535.") from None

    public_url = environment.get("FEMAKTIV_PUBLIC_URL", "").strip()
    site_url, allowed_hosts = (
        public_origin(public_url)
        if public_url
        else (f"http://127.0.0.1:{port}", "localhost,127.0.0.1,[::1]")
    )

    os.chdir(ROOT)
    state = ROOT / ".local"
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    key_file = state / "secret_key"
    try:
        with open(key_file, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
            output.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass

    environment.pop("GUNICORN_CMD_ARGS", None)
    environment.update(
        {
            "DJANGO_DEBUG": "0",
            "DJANGO_LOCAL_HTTP": "0" if public_url else "1",
            "DJANGO_ALLOWED_HOSTS": allowed_hosts,
            "DJANGO_SECRET_KEY": key_file.read_text().strip(),
            # Gunicorn handles HTTPS headers only from the loopback proxy. Django
            # must use its WSGI scheme, not re-read ngrok's appended raw headers.
            "DJANGO_TRUST_PROXY": "0",
        }
    )
    if public_url:
        environment["DJANGO_CSRF_TRUSTED_ORIGINS"] = site_url

    print(f"femaktiv: {site_url}/ (English) · {site_url}/de/ (Deutsch)", flush=True)
    executable = str(ROOT / ".venv/bin/gunicorn")
    os.execve(
        executable,
        [
            executable,
            "config.wsgi:application",
            "--bind",
            f"127.0.0.1:{port}",
            "--forwarded-allow-ips",
            "127.0.0.1",
            "--workers",
            "1",
            "--threads",
            "2",
            "--timeout",
            "90",
        ],
        environment,
    )


if __name__ == "__main__":
    main()
