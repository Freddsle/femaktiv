# femaktiv

An English/German Django app for everyday questions, private notes and chat history, with public conversation examples.

Chat uses labelled **placeholder replies** by default and makes no AI calls. Optional live chat uses Anymize and a local evidence library. This is a prototype for fictional information; example answers are illustrative, not reviewed medical guidance.

## Start locally

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
./bin/setup
./bin/serve
```

Open [English](http://127.0.0.1:8000/) or [German](http://127.0.0.1:8000/de/). Stop with Ctrl+C. Use `./bin/dev` for automatic reloads during development.

Registration is closed by default. Create an administrator:

```bash
.venv/bin/python manage.py createsuperuser
```

Sign in at [/en/admin/](http://127.0.0.1:8000/en/admin/) to add tester accounts. Password-reset emails appear in the server terminal locally.

Accounts, notes and chats persist in `.local/db.sqlite3`. Account settings lets users delete their chats and notes. Deleting a source note leaves its saved chat copies intact.

## Configure live chat locally

Create a Git-ignored `.env.local` containing:

```dotenv
FEMAKTIV_AI_MODE=live
ANYMIZE_API_KEY='your-key'
ANYMIZE_MODEL='your-account-accessible-model'
ANYMIZE_ZDR_CONFIRMED=1
ANYMIZE_FALLBACKS_DISABLED_CONFIRMED=1
```

Set the confirmation flags only after enabling Zero Data Retention and disabling fallback models in your Anymize account. Keep keys server-side. Environment files are **not loaded automatically**.

Stop the server, then load the settings and restart from the repository folder:

```bash
chmod 600 .env.local
set -a
source .env.local
set +a
./bin/serve
```

In admin, enable **Live chat approved** for each intended tester. Anymize receives submitted messages and active chat context, including attached note copies, and handles identifier masking and response restoration. femaktiv does not verify masking or guarantee masked replies. Live chat has no web search.

See the [live-chat specification](specs/behavior/live_chat.md) for context controls, request limits and optional paid evaluation.

## Share a preview through ngrok

With [ngrok installed and authenticated](https://ngrok.com/download/linux), run in a separate terminal:

```bash
ngrok http http://127.0.0.1:8000 --inspect=false
```

Copy its HTTPS forwarding URL. Stop the femaktiv server and restart it in the same terminal with that URL:

```bash
FEMAKTIV_PUBLIC_URL=https://your-domain.ngrok-free.app ./bin/serve
```

Keep both processes running. Restart femaktiv whenever the URL changes. To return to local HTTP, stop the server and run `./bin/serve` without `FEMAKTIV_PUBLIC_URL`.

## Development

```bash
./bin/check
python3 bin/depemesh/check.py
donna -p llm validate --all
git diff --check
```

`bin/check` runs lint, Django checks, backend tests and browser tests without provider calls. Browser tests need Chrome/Chromium; install it if needed with `.venv/bin/python -m playwright install chromium`.

- [Specifications](specs/intro.md): product behavior and development workflows.
- [Validation results](docs/VALIDATION.md): recorded checks and limitations.
- [Hosting settings](.env.example): configuration reference; `bin/serve` is for local use and tunnel previews.
