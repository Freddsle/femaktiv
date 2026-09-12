import importlib.util
import io
import os
import runpy
import stat
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.test import Client, SimpleTestCase
from gunicorn.config import Config
from gunicorn.http.parser import RequestParser


class LocalLauncherTests(SimpleTestCase):
    def setUp(self):
        module = importlib.util.spec_from_file_location(
            "femaktiv_run_local", settings.BASE_DIR / "bin/run_local.py"
        )
        self.launcher = importlib.util.module_from_spec(module)
        module.loader.exec_module(self.launcher)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def launch(self, environment=None, arguments=()):
        output = io.StringIO()
        with (
            patch.dict(os.environ, environment or {}, clear=True),
            patch.object(self.launcher, "ROOT", self.root),
            patch.object(self.launcher.sys, "argv", ["bin/run_local.py", *arguments]),
            patch.object(self.launcher.os, "chdir"),
            patch.object(self.launcher.os, "execve") as execute,
            redirect_stdout(output),
        ):
            self.launcher.main()
        execute.assert_called_once()
        executable, command, environment = execute.call_args.args
        self.assertEqual(executable, str(self.root / ".venv/bin/gunicorn"))
        return command, environment, output.getvalue()

    def configured_settings(self, environment):
        with patch.dict(os.environ, environment, clear=True):
            return runpy.run_path(str(settings.BASE_DIR / "config/settings.py"))

    def test_default_keeps_local_http_and_stable_private_key(self):
        command, environment, output = self.launch(
            {"GUNICORN_CMD_ARGS": "--bind 0.0.0.0:9000", "DJANGO_ALLOWED_HOSTS": "*"}
        )
        self.assertEqual(command[command.index("--bind") + 1], "127.0.0.1:8000")
        self.assertNotIn("GUNICORN_CMD_ARGS", environment)
        self.assertIn("http://127.0.0.1:8000/", output)
        configured = self.configured_settings(environment)
        self.assertFalse(configured["DEBUG"])
        self.assertEqual(configured["ALLOWED_HOSTS"], ["localhost", "127.0.0.1", "[::1]"])
        self.assertFalse(configured["SECURE_SSL_REDIRECT"])
        self.assertFalse(configured["SESSION_COOKIE_SECURE"])
        key_path = self.root / ".local/secret_key"
        self.assertEqual(stat.S_IMODE(key_path.stat().st_mode), 0o600)
        self.assertGreaterEqual(len(environment["DJANGO_SECRET_KEY"]), 64)
        _, restarted, _ = self.launch()
        self.assertEqual(restarted["DJANGO_SECRET_KEY"], environment["DJANGO_SECRET_KEY"])

    def test_ngrok_origin_configures_https_forms_and_exact_host(self):
        host = "femaktiv-demo.ngrok-free.app"
        origin = "https://" + host
        command, environment, output = self.launch(
            {
                "FEMAKTIV_PUBLIC_URL": origin + "/",
                "FEMAKTIV_PORT": "8001",
                "DJANGO_TRUST_PROXY": "1",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "https://*.ngrok-free.app",
            }
        )
        self.assertEqual(command[command.index("--bind") + 1], "127.0.0.1:8001")
        self.assertIn(origin + "/de/", output)
        configured = self.configured_settings(environment)
        self.assertFalse(configured["DEBUG"])
        self.assertEqual(configured["ALLOWED_HOSTS"], [host])
        self.assertEqual(configured["CSRF_TRUSTED_ORIGINS"], [origin])
        self.assertNotIn("SECURE_PROXY_SSL_HEADER", configured)
        self.assertTrue(configured["SESSION_COOKIE_SECURE"])
        self.assertTrue(configured["CSRF_COOKIE_SECURE"])
        self.assertTrue(configured["SECURE_SSL_REDIRECT"])

        # Exercise Gunicorn's real request parser, then the Django request path
        # with its resulting WSGI scheme, without a network or an ngrok account.
        gunicorn = Config()
        gunicorn.set("forwarded_allow_ips", command[command.index("--forwarded-allow-ips") + 1])
        raw = f"GET /en/ HTTP/1.1\r\nHost: {host}\r\nX-Forwarded-Proto: https\r\n\r\n".encode()
        request = next(RequestParser(gunicorn, [raw], ("127.0.0.1", 54321)))
        self.assertEqual(request.scheme, "https")
        untrusted = next(RequestParser(gunicorn, [raw], ("192.0.2.1", 54321)))
        self.assertEqual(untrusted.scheme, "http")
        keys = (
            "DEBUG",
            "ALLOWED_HOSTS",
            "CSRF_TRUSTED_ORIGINS",
            "SESSION_COOKIE_SECURE",
            "CSRF_COOKIE_SECURE",
            "LANGUAGE_COOKIE_SECURE",
            "SECURE_SSL_REDIRECT",
        )
        with self.settings(
            **{key: configured[key] for key in keys},
            SECURE_PROXY_SSL_HEADER=None,
            FEMAKTIV_SIGNUP_ENABLED=True,
        ):
            client = Client(enforce_csrf_checks=True, HTTP_HOST=host)
            secure = request.scheme == "https"
            for path in ("/en/", "/de/", "/en/accounts/signup/"):
                self.assertEqual(client.get(path, secure=secure).status_code, 200)
            self.assertTrue(client.cookies["csrftoken"]["secure"])
            form = {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}
            self.assertEqual(
                client.post(
                    "/en/accounts/signup/", form, secure=secure, HTTP_ORIGIN=origin
                ).status_code,
                200,
            )
            self.assertEqual(
                client.post(
                    "/en/accounts/signup/",
                    form,
                    secure=secure,
                    HTTP_ORIGIN="https://other.ngrok.app",
                ).status_code,
                403,
            )
            self.assertEqual(
                client.get("/en/", secure=secure, HTTP_HOST="other.ngrok-free.app").status_code, 400
            )
            self.assertEqual(client.get("/en/")["Location"], origin + "/en/")

    def test_invalid_public_urls_fail_before_creating_state(self):
        for value in (
            "http://demo.ngrok.app",
            "demo.ngrok.app",
            "https://*.ngrok-free.app",
            "https://demo.ngrok.app,other.example",
            "https://user:secret@demo.ngrok.app",
            "https://demo.ngrok.app/path",
            "https://demo.ngrok.app?query=1",
            "https://demo.ngrok.app#fragment",
            "https://demo.ngrok.app:8000",
            "https://demo.ngrok.app:invalid",
            "https://[invalid",
            "https://demo.\nngrok.app",
            "https://-invalid.ngrok.app",
        ):
            with self.subTest(value=value), self.assertRaisesMessage(SystemExit, "HTTPS origin"):
                self.launch({"FEMAKTIV_PUBLIC_URL": value})
        self.assertFalse((self.root / ".local").exists())

    def test_explicit_https_port_and_host_case_are_normalized(self):
        _, environment, _ = self.launch({"FEMAKTIV_PUBLIC_URL": "https://DEMO.ngrok.app:443/"})
        self.assertEqual(environment["DJANGO_ALLOWED_HOSTS"], "demo.ngrok.app")
        self.assertEqual(environment["DJANGO_CSRF_TRUSTED_ORIGINS"], "https://demo.ngrok.app")

    def test_invalid_ports_and_extra_bind_arguments_are_rejected(self):
        for port in ("0", "1023", "65536", "invalid"):
            with self.subTest(port=port), self.assertRaisesMessage(SystemExit, "FEMAKTIV_PORT"):
                self.launch({"FEMAKTIV_PORT": port})
        with self.assertRaisesMessage(SystemExit, "extra arguments are unsupported"):
            self.launch(arguments=("--bind", "0.0.0.0:8000"))
        self.assertFalse((self.root / ".local").exists())
