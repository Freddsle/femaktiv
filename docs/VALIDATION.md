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

## ngrok preview follow-up

On 12 September 2026, `bin/serve` gained the opt-in `FEMAKTIV_PUBLIC_URL` HTTPS preview mode described in [README](../README.md#share-a-preview-through-ngrok). The full `./bin/check` run passed: 260 German translations, Ruff lint and formatting for 62 Python files, Django system/migration checks, static collection, 63 backend tests and four browser scenarios. Depmesh specification/link/graph checks, all 15 isolated relation fixtures, Donna validation and `git diff --check` also passed.

The five new launcher tests cover the default loopback HTTP mode and stable private key, exact public host and CSRF origin, secure cookies, HTTPS forwarding, rejection of foreign hosts/origins, URL normalization, and invalid URL/port/bind inputs. Depmesh resolves `bin/run_local.py` and `tests/unit/bin/test_run_local.py` in both directions through the existing Python convention.

A separate smoke check started the actual `./bin/serve` process on temporary loopback ports in both modes. Local HTTP, English/German pages, collected CSS and logo assets, HTTPS redirects, exact host validation, secure CSRF cookies and same-origin/foreign-origin form handling passed. The check simulated ngrok's `Host` and `X-Forwarded-Proto` headers; it created no accounts and stopped both test servers. No external tunnel or provider request was made.

The ngrok CLI was not installed in the inspected environment. A public ngrok endpoint, account authentication and ngrok's actual TLS termination remain untested; the user must install/authenticate ngrok and supply its URL to start the preview.

## Prototype boundaries

Chat persistence and account ownership are real. Replies are deterministic, visibly labelled placeholders; no LLM or anymize requests or provider credits are used. Q&A and the two public conversations contain authored examples. Public posting, moderation, file uploads, clinical review and live AI remain future work.

This delivery has not been published on the internet. PostgreSQL, external SMTP delivery, reverse-proxy HTTPS and a hosting provider are configurable but not exercised locally. Password recovery uses the local console email backend. The browser suite uses fictional data and a disposable test database.

## Rounded logo refinement

On 12 September 2026, the user authorized retaining only the soft central cross, preserving its central artwork, and improving resolution. The website uses [the rounded PNG](../static/img/femaktiv-logo-rounded.png); [the original image](../static/img/femaktiv-logo.png) remains unchanged.

The built-in image_gen tool produced the higher-resolution artwork. Its two outputs contained an opaque checkerboard, so the user explicitly authorized programmatic background removal. Pillow removed only the connected neutral exterior, refined the silhouette edge, and exported a 2048×2048 RGBA PNG. The generated artwork's central RGB pixels and full opacity were checked before final resampling. The exported corner pixels have alpha zero, with a full alpha range of 0–255. This is an actual transparent asset.

All logo consumers use the new asset, including the favicon, standalone error page, and new assistant messages. Intrinsic dimensions are square, and the former rectangular shadow and corner clipping have been removed.

The existing four browser journeys passed after the update. Desktop/mobile chat screenshots showed clean cutouts. Additional production-browser checks verified the 2048px image, transparent corner pixels, English/German pages and no horizontal overflow at 1440px and 390px.

### Image generation prompts

Built-in image_gen was used; the CLI/API fallback was not used. The following prompts record the generation inputs. Final transparency was completed with the separately authorized local processing described above.

First edit, using the original supplied logo:

```text
Use case: background-extraction / precise-object-edit.
Asset type: the existing femaktiv brand logo, cleaned up for use as a transparent website logo.
Image 1 is the EDIT TARGET and the only authority for the design. This is a careful restoration of this existing logo, not a redesign.

Primary request: extract just the central soft four-lobed rounded cross/clover emblem from the pink square screenshot. Remove all pale-pink rectangular background outside that four-lobed silhouette, the thin black screenshot edges, and any exterior artifacts. The resulting PNG must have a genuinely transparent alpha background, NOT a white or pink square and NOT a checkerboard drawn into the image.

Keep the center design exactly recognizable and unchanged: lowercase white serif word "femaktiv" across the middle; the small exact white tagline "- lifecycle essentials -" below it; the delicate white radial sun above the word; the group of white horizontal waves below. Preserve their relative placement, sizes, original letterforms, proportions, and spacing. Preserve the emblem's existing left-purple, middle-mauve/rose, right-coral/orange smooth gradient, with no invented colors. Do not change the central artwork, do not simplify it, do not remove the tagline or symbols.

Improve only edge quality and source resolution: smooth, clean, slightly rounder balanced lobes, softly curved joins, faithful to the supplied rounded cross. It should remain a four-lobed cross, not become a circle or a many-petaled flower. Crisp typography and graceful thin sun/wave lines, polished high-resolution rendering, preferably 2048x2048 PNG. Flat graphic, no bevel, no 3D, no lighting, no added shadow, no outline.
Composition: one emblem, centered, upright, occupying about 90% of a square canvas, equal minimal transparent padding. No alternate versions, no presentation board, no added words or decorative elements.
```

Background-only follow-up, using the first generated image:

```text
Use case: background-extraction.
Image 1 is the EDIT TARGET: an already finished femaktiv logo. Perform ONLY precise background removal. Preserve the colored four-lobed cross and ALL pixels, typography, sun, waves and gradient inside its outer silhouette as closely as possible. Do not redesign, recolor, retype, regenerate or reshape the emblem.

The existing gray checkerboard OUTSIDE the colored cross is an unwanted opaque background, not transparency. Remove every pixel of that checkerboard and its scratches and lines. Replace the outside with actual alpha=0 transparency in the saved PNG. The required output is an RGBA PNG file with a real transparency channel, not an RGB image showing a transparency grid. No painted grid, no white/gray/black/pink backdrop, no halo, no square panel, no shadow. Clean antialiased edge around the single existing rounded cross. Center it with the same canvas and orientation, retaining the existing high resolution.

Keep the exact center text "femaktiv" and "- lifecycle essentials -", the white sun above, the white waves below, and the purple-to-mauve-to-coral gradient unchanged. Only the exterior background changes. Deliver one genuinely transparent PNG cutout.
```
