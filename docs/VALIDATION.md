# femaktiv validation

Implementation review on 12 September 2026. This report records the local Django prototype governed by [the platform specification](../specs/behavior/platform.md). Startup and extension instructions are in [README](../README.md).

## Environment

Python 3.14.5, Django 5.2.17, Gunicorn 23.0.0, WhiteNoise 6.12.0, Playwright 1.62.0 and Google Chrome 151.0.7922.137 on Linux. Application dependencies are pinned in `uv.lock`; local persistence uses SQLite.

## Automated verification

The integration check is `./bin/check`: translation validation/compilation, Ruff lint/format, Django system checks, missing-migration checks, static-file collection, backend tests and browser journeys. Donna runs this command followed by Depmesh verification, workflow validation and `git diff --check`.

Donna's verification step completed successfully:

| Check | Observed result |
| --- | --- |
| German translations | 260 translated entries, no fuzzy/untranslated entries; compilation passed |
| Ruff lint and formatting | Passed; 60 Python files formatted |
| Django system and migration checks | No issues; no missing migrations |
| Static collection | Passed; versioned CSS, JavaScript and image assets generated |
| Backend tests | 58 passed |
| Playwright browser tests | 4 passed |
| Depmesh | 114 files, 256 directed relations; all 15 source/test fixture pairs and exclusions passed |
| Donna workflow validation | All artifacts valid |
| Whitespace check | `git diff --check` passed |

Backend coverage includes registration, recovery tokens/emails, CSRF enforcement, owner isolation including staff accounts, note edits/deletion, immutable message context, durable chats, atomic rollback, idempotent retries and conflicting request identifiers. Localization checks include a German browser on an English page and a language cookie that differs from the current page.

The four browser journeys cover account creation through note attachment and saved history; a failed request with draft retention and a keyboard skip link; a delayed response after navigation; and public examples/topic filtering in both languages. They assert no unexpected JavaScript or HTTP errors and no horizontal overflow in the checked layouts.

## Local deployment and review

`./bin/serve` starts Gunicorn with `DEBUG=False`, WhiteNoise assets and a loopback-only HTTP listener. English is at `http://127.0.0.1:8000/`; German is at `http://127.0.0.1:8000/de/`. A stable private signing key and the local database live in ignored `.local/`.

Browser screenshots are written to `.local/screenshots/`. The review covers 1440px desktop and 390px mobile layouts, both languages, and the signup, private-note, attachment, conversation-history and logout/login journey.

Reviewed `home-en-desktop.png`, `home-de-desktop.png`, `home-de-mobile.png`, `community-en-mobile.png`, `chat-en-desktop.png` and `chat-de-mobile.png`. Decorative hero rings were adjusted to remove mobile/tablet overflow. Additional browser measurements passed for 12 English/German public and account pages at 390px and the German homepage at 360, 390, 700, 720, 768, 900, 1024 and 1440px.

A separate production-mode browser smoke check used an isolated temporary SQLite database and actual Gunicorn/WhiteNoise. Registration, a private note, a message with an attached snapshot, English-to-German switching, private no-store headers and collected CSS all passed. Restarting the server preserved the session, both messages and the attachment snapshot. The temporary database was removed afterwards.

`manage.py check --deploy` passed with a generated secret, explicit host/CSRF origin, `DEBUG=False` and the local-HTTP override disabled. The local helper rejects additional bind arguments and ignores `GUNICORN_CMD_ARGS`; its intended listener is loopback only.

## Prototype boundaries

Chat persistence and account ownership are real. Replies are deterministic, visibly labelled placeholders; no LLM or anymize requests or provider credits are used. Q&A and the two public conversations contain authored examples. Public posting, moderation, file uploads, clinical review and live AI remain future work.

This delivery has not been published on the internet. PostgreSQL, external SMTP delivery, reverse-proxy HTTPS and a hosting provider are configurable but not exercised locally. Password recovery uses the local console email backend. The browser suite uses fictional data and a disposable test database.
