# femaktiv backend overview for a pitch deck

A 16:9 slide explaining the prototype through its value to the user: personal context, credible sources and practical support. Two independent panels distinguish private personal context from the curated library of public sources, with separate lavender and coral arrows into femaktiv. The composition uses the existing website palette and the femaktiv, Django, Anymize and OpenAI marks to identify the application and its tools.

## Files

- [4K PNG](backend-overview.png) — 3840 × 2160; insert as a full-slide image in PowerPoint, Google Slides, Keynote or Canva.
- [PDF](backend-overview.pdf) — one 16:9 page with selectable text and vector diagram elements.
- [Editable SVG](backend-overview.svg) — 1920 × 1080 with editable text/shapes and embedded logos. Font appearance can vary between editors; the PNG and PDF preserve the rendered appearance.
- [Browser version](backend-overview.html) — self-contained, with no external fonts, scripts or image requests. Designed at slide dimensions rather than as a responsive website.
- [Build script](build.py) — changes copy/layout and regenerates all four exports using the existing Playwright dependency and local Chrome/Chromium.

## Suggested narration

“femaktiv draws on two distinct inputs: her private context and a curated library of public guidance. Her questions, selected notes and active conversation belong to her; the source library contains selected published guidance. The Django backend selects relevant evidence and guides each model request. Anymize handles identifier masking before the OpenAI model drafts a response. femaktiv checks the returned references and presents practical guidance, in English or German.”

The slide is a conceptual view of the configured live prototype. The actual sequence is intake through Anymize, selection of local evidence, composition through Anymize, then application validation and citation storage. Clarification can finish after intake. The combined AI card represents these two bounded calls; the diagram does not imply a third model call. The model badge identifies **GPT-5.6**, matching the operator's configured `openai/gpt-5.6-sol` checked on 13 September 2026. The label is explicit presentation copy in `MODEL_LABEL`; the renderer never reads credentials or local environment files. Update it when the configured model changes. The diagram does not assert that model selection automatically tracks the newest ChatGPT release, and ChatGPT's consumer application is not part of this API integration.

Personal notes and chat history are not source-library records. The separate input arrows describe distinct ownership and purposes; relevant context and source passages are brought together for answer composition. This visual revision does not change storage or provider behavior.

Reference checks match source IDs to supplied records and stored links. They are not verification of the medical correctness of generated claims. Anymize owns masking/restoration; the slide does not assert independently verified anonymity or clinical validation. The evidence panel describes the selected local library, not ingestion of the complete list in `00_initial/sources.md`, live research, access to whole study databases, or a partnership with the named organizations.

## Artwork and factual sources

- Palette from [site.css](../../../static/css/site.css): paper `#fcf9f6`, plum `#39273e`, purple `#785098`, lavender `#ede5f2`, blush `#f5eae8`, rose `#ecd2d9`, coral `#dd9076` and muted text `#736675`.
- femaktiv artwork: the existing [approved logo](../../../static/img/femaktiv-logo-rounded.png), embedded without changing the original.
- [Anymize wordmark](assets/anymize.svg): extracted from the navigation SVG on the [official Anymize website](https://anymize.ai/en), retrieved 13 September 2026. Its paths and original color are retained. The logo identifies the integration provider; it does not imply an endorsement.
- [Django logo](assets/django.svg): downloaded from the [official SVG asset](https://www.djangoproject.com/m/img/logos/django-logo-positive.svg) linked on the [Django logo page](https://www.djangoproject.com/community/logos/), retrieved 13 September 2026. It identifies the actual framework, retains its original color/proportions and links to Django in the SVG/HTML/PDF. This follows the [service-identification terms](https://www.djangoproject.com/trademarks/); no Django affiliation or endorsement is claimed.
- [OpenAI symbol](assets/openai.svg): the [OpenAI provider asset served by Anymize](https://anymize.ai/icons/providers/openai.svg), retrieved 13 September 2026, retained without recoloring or altering its paths. The symbol belongs to OpenAI and identifies the configured GPT model accessed through Anymize. Use follows the [OpenAI brand guidance](https://openai.com/brand/) for accurate service references; the diagram does not portray a partnership or direct ChatGPT application integration.
- Architecture: [live-chat specification](../../../specs/behavior/live_chat.md), [service](../../../chats/service.py), [provider](../../../chats/provider.py) and [evidence library](../../../content/evidence.json).
- The source organizations are rendered as text labels, not recreated official logos. Their names reflect records actually in the application's local library: DGE, NIH/NHLBI, EFSA, gesund.bund.de and ZQP.

## Why these logos and source labels

**Django** identifies the backend, **Anymize** identifies the masking/model gateway, and **OpenAI** identifies the configured model inside that gateway. Their roles remain distinct from the source institutions. Other model brands are not shown because the diagram describes this configuration.

**NIH/NHLBI**, **EFSA** and **DGE** are recognizable evidence-source names. The [NIH FAQ](https://www.nih.gov/about-nih/frequently-asked-questions) restricts logo use promoting non-NIH products, and [EFSA's logo terms](https://www.efsa.europa.eu/en/images/efsalogo) restrict use as company design features and commercial use without written agreement. Plain typographic source badges are used here. DGE certification logos are not appropriate evidence-source decorations because they identify a different, licensed certification relationship. No source-logo permission or institutional partnership is claimed.

This entire deliverable lives under `docs/pitch/backend-schema/`, already covered by the repository's existing `docs/` governance rule in [Depmesh](../../../depmesh.toml). Application code, website wording and active implementation workflow state are outside this artwork change.

## Rebuild

From the repository root:

```bash
.venv/bin/python docs/pitch/backend-schema/build.py
```

This uses a fresh local browser profile and local artwork only; it does not invoke the application or an AI provider. The system browser must be available, or Playwright's Chromium must be installed. Some sandbox environments require permission to launch a browser process.

## Verification

The revised PNG was visually reviewed at full-slide scale, including the separate context/source panels and nested OpenAI badge. All SVG text bounds fit the canvas. Export checks confirm a 3840 × 2160 PNG and a single 16:9 PDF page with selectable text. Diagram content was reviewed against the current local source library and two-call provider flow. Repository relation/link validation, Donna artifact validation and whitespace checks were run separately from application tests; this artwork does not change application behavior.
