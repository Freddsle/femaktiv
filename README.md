# femaktiv

A bilingual space for everyday questions, personal context and future AI assistance. The public website and private workspace run together in one Django application.

## Start locally

Python 3.14 and [uv](https://docs.astral.sh/uv/getting-started/installation/) are required. From this repository:

```bash
./bin/setup
./bin/serve
```

Open **http://127.0.0.1:8000/** for English or **http://127.0.0.1:8000/de/** for German. Create an account through the website; there are no shared default credentials. Stop the foreground server with Ctrl+C. To use another local port, run `FEMAKTIV_PORT=8001 ./bin/serve`.

`bin/setup` installs the locked dependencies, compiles translations, applies migrations and collects static assets. `bin/serve` runs Gunicorn with WhiteNoise, `DEBUG=False`, and a stable signing key stored privately in `.local/secret_key`. It binds only to `127.0.0.1` and explicitly permits local HTTP. `./bin/dev` runs Django's development server with reload support.

## Share a preview through ngrok

Install [ngrok and configure your account's authtoken](https://ngrok.com/download/linux) once. After `./bin/setup`, open a terminal and start the tunnel:

```bash
ngrok http http://127.0.0.1:8000 --inspect=false
```

Copy the HTTPS URL from ngrok's `Forwarding` line. Stop any existing femaktiv server on port 8000, then run this in a second terminal from the repository, replacing the example URL with yours:

```bash
FEMAKTIV_PUBLIC_URL=https://your-domain.ngrok-free.app ./bin/serve
```

Open that public URL for English or append `/de/` for German. The launcher configures Django's exact allowed host and CSRF origin, keeps `DEBUG=False`, enables secure cookies and HTTPS redirects, and uses the existing private signing key and database. Gunicorn recognizes HTTPS forwarded by the loopback ngrok agent. HTTP traffic inspection is disabled by the [ngrok CLI flag](https://ngrok.com/docs/gateway/agent/cli#ngrok-http).

Keep both processes running while showing the site. If the ngrok URL changes, restart `bin/serve` with the new URL. The public URL must be an HTTPS origin without a path, credentials or wildcard. To return to local HTTP, stop the server and run `./bin/serve` without `FEMAKTIV_PUBLIC_URL`. The helper never starts ngrok itself. Password recovery still prints emails in the server terminal with the default console backend.

## What works

- Real email/password registration, login/logout, account settings and password change/recovery.
- Private notes and preferences, with create/edit/delete controls.
- Persistent chats, history, renaming, deletion and explicit note attachments.
- Immutable copies of attached notes: changing a note does not rewrite a previous conversation.
- English and German navigation, forms, errors, account emails and example content. English is the first-visit default; an explicit language choice is remembered.
- Two read-only conversation examples and six public Q&A previews in three topics.

The chat API saves each message and returns a visibly labelled **placeholder reply**. No LLM or anymize requests are made. Example answers are illustrative authored content, not personalised recommendations or reviewed medical guidance. Q&A posting and moderation are not implemented.

## Accounts and data

Accounts, chats, notes and sessions are stored in `.local/db.sqlite3`; they survive refreshes and server restarts. Logout does not delete stored data. Users can delete their notes and chats. Deleting a note leaves copies already attached to messages; deleting a chat removes those copies. Both `.local/` and secrets are ignored by Git.

Password recovery prints an email and reset URL in the local server terminal. This console backend is for local development only; configure SMTP for a hosted site. Create an administrator when needed with:

```bash
.venv/bin/python manage.py createsuperuser
```

The admin URL is `/en/admin/` or `/de/admin/`. Private notes, chat messages and attachments are deliberately not registered in the admin interface.

## Verification

```bash
./bin/check
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

`bin/check` validates/compiles German translations, runs Ruff, Django checks and missing-migration checks, collects static assets, runs backend tests and executes the Playwright browser suite. Browser tests use an installed Google Chrome/Chromium automatically. Alternatively install Playwright's Chromium with `.venv/bin/python -m playwright install chromium`, or set `FEMAKTIV_BROWSER_EXECUTABLE` to a browser binary. Browser tests require permission to create local sockets and launch a browser. They use an isolated browser profile and temporary test database, never a live AI provider.

Screenshots from the browser suite are saved under `.local/screenshots/`. See [validation results](docs/VALIDATION.md) for actual commands and outcomes from this implementation.

## Project structure and extension points

- `accounts/`: custom email user, forms and standard Django authentication views.
- `notes/`: owner-restricted saved context.
- `chats/`: durable conversations, immutable attachments, API validation and a replaceable reply service.
- `pages/` and `content/examples.json`: public pages and bilingual static examples.
- `templates/`, `static/` and `locale/`: shared presentation, small JavaScript modules and translations.
- `config/`: settings, route prefixes, deployment entrypoint and cache controls.

The active requirements are in [the platform specification](specs/behavior/platform.md). The original nutrition build specification is preserved as historical/future reference; its Next.js, English-only, no-account and no-database requirements do not govern this version. Development follows the project's Donna workflow and Depmesh ownership mappings.

### Connect a future LLM

Replace `chats/service.py:generate_reply` with an explicitly configured server-side adapter. Its inputs are conversation history, the selected note context and the requested reply language. Keep ownership, persistence, retry identifiers and response-mode labels in the HTTP/storage layer. Do not turn on a paid provider in ordinary tests.

The current endpoint is `POST /<language>/api/chats/<chat UUID>/messages/`, with a JSON body containing only `content`, `note_ids` and `client_request_id`. Session authentication and CSRF are required. Successful replies include both stored messages, chat metadata and `mode: "placeholder"`. A reused request identifier with the same payload returns the existing turn; a different payload returns a conflict.

A real provider integration needs its own bounded history/token handling, provider error handling and content policy. The current adapter does not provide medical advice, retrieval, live sources or autonomous agents.

### Extend Q&A later

`pages/content.py` loads the current examples separately from page rendering. Later, Django topic/question/answer models can supply the same templates. Add authenticated posting, ownership checks and moderation together before accepting public contributions. No forum framework or separate service is needed for the initial read-only preview.

### Maintain translations

English source strings use Django gettext/template translation tags. German UI translations live in `locale/de/LC_MESSAGES/django.po`; long example content has English/German entries in `content/examples.json`. The product name remains `femaktiv` in both languages. User-authored notes and saved messages are never automatically translated.

Compilation has no system gettext dependency:

```bash
./bin/translations
```

To extract new messages, install GNU gettext (`xgettext`, `msgmerge`, `msgfmt`) and run:

```bash
.venv/bin/python manage.py makemessages -l de --ignore=.venv --ignore=.local --ignore=staticfiles --ignore=tests --ignore=.session --no-wrap
./bin/translations
```

The compiler rejects fuzzy/untranslated entries and changed interpolation placeholders. Review new German strings for the consistent friendly `du` tone.

## Prepare for hosting

This delivery is local; no public site has been published. `.env.example` lists production environment variables. It is a reference, not automatically loaded: configure these values in the host's environment/secret manager.

For hosting, set a unique `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, explicit allowed hosts and CSRF origins, PostgreSQL credentials and SMTP. Use HTTPS and leave `DJANGO_LOCAL_HTTP` unset. Set `DJANGO_TRUST_PROXY=1` only behind a trusted proxy that sanitizes `X-Forwarded-Proto`. Run migrations, translation compilation and `collectstatic` during deployment, then serve `config.wsgi:application` using Gunicorn. The `bin/serve` helper is intentionally for local use only.

Run `.venv/bin/python manage.py check --deploy` under the actual hosting configuration. Hosting decisions still include persistent database storage/backups, recovery email delivery, rate limits for account endpoints and operational monitoring. Application logs should contain operational status, not note text, message bodies or passwords. Live AI and a public user-generated forum remain separate future work.
