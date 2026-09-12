"""Public locality lookups. Only an enumerated service and explicit locality leave here."""

import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

from django.conf import settings
from django.utils import timezone

from . import transport
from .context import validate_locality
from .contracts import SERVICE_CATEGORIES
from .errors import ChatError

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
SERVICE_WORDS = (
    "pflege",
    "pflegestütz",
    "care advice",
    "care support",
    "discharge",
    "entlass",
    "sozialdienst",
    "haushaltshilfe",
    "rehabilitation",
)
PHONE = re.compile(r"(?<!\w)(?:\+49|0049|0)[\d ()/–-]{7,24}\d(?!\w)")
EMAIL = re.compile(r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.in_title = False
        self.title = []
        self.parts = []
        self.contacts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self.hidden += 1
        if self.hidden:
            return
        if tag == "title":
            self.in_title = True
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith(("tel:", "mailto:")):
                self.contacts.append(href.split(":", 1)[1].split("?", 1)[0])
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "address"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg", "template"} and self.hidden:
            self.hidden -= 1
        if tag == "title":
            self.in_title = False
        if not self.hidden and tag in {"p", "div", "li", "address"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.in_title:
                self.title.append(data)


def fetch_page(url, budget):
    seen = set()
    while True:
        url = transport.safe_url(url)
        if url in seen:
            raise ChatError("unsafe_url")
        seen.add(url)
        budget.consume("page")
        status, headers, data = transport.request(
            url,
            budget=budget,
            max_bytes=512_000,
            timeout=7,
            headers={"Accept": "text/html, text/plain"},
        )
        if status in {301, 302, 303, 307, 308}:
            url = urljoin(url, headers.get("location", ""))
            continue
        if status != 200 or headers.get("content-type", "").split(";")[0].lower() not in {
            "text/html",
            "text/plain",
        }:
            raise ChatError("search_unavailable")
        parser = PageText()
        charset = re.search(r"charset=([\w-]+)", headers.get("content-type", ""), re.I)
        encoding = (
            charset.group(1)
            if charset and charset.group(1).lower() in {"utf-8", "iso-8859-1", "windows-1252"}
            else "utf-8"
        )
        parser.feed(data.decode(encoding, errors="replace"))
        title = " ".join(" ".join(parser.title).split())[:200]
        text = "\n".join(
            " ".join(line.split()) for line in " ".join(parser.parts).splitlines() if line.strip()
        )
        return url, title, text, parser.contacts


def _locality_match(text, locality):
    return re.search(r"(?<!\w)" + re.escape(locality.casefold()) + r"(?!\w)", text.casefold())


def contact_record(url, title, text, linked_contacts, locality, number):
    """Require actual page evidence for locality, organisation/service and contact."""
    if not title or not _locality_match(text, locality):
        return None
    if not any(word in title.casefold() for word in SERVICE_WORDS):
        return None
    # A contact must occur near the named locality, not solely in a global footer.
    location = _locality_match(text, locality)
    excerpt = text[max(0, location.start() - 1000) : location.end() + 3000]
    phones = list(dict.fromkeys(" ".join(match.split()) for match in PHONE.findall(excerpt)))[:3]
    emails = list(dict.fromkeys(EMAIL.findall(excerpt)))[:3]
    # Linked-only contact values are included only when also present in the local excerpt.
    for linked in linked_contacts:
        if linked in excerpt and EMAIL.fullmatch(linked) and linked not in emails:
            emails.append(linked)
    if not phones and not emails:
        return None
    return {
        "id": f"contact-{number}",
        "title": title,
        "url": url,
        "section": "Local service contact",
        "kind": "contact",
        "locality": locality,
        "organisation": title,
        "phones": phones,
        "emails": emails[:3],
        "publication_date": None,
        "checked_date": timezone.localdate().isoformat(),
        "applicability": f"The fetched page names {locality} and a relevant service. Contact details were found on that page.",
        "limitations": "Availability, language support and personal eligibility are unknown. Confirm directly. Page verification does not authenticate every claim of the organisation.",
        "passage": excerpt[:4000],
    }


def _rank(candidate, locality):
    host = urlsplit(candidate["url"]).hostname or ""
    preferred = (
        "bund.de",
        "zqp.de",
        "aok.de",
        "tk.de",
        "barmer.de",
        "pflegestuetzpunkteberlin.de",
        locality.casefold()
        .replace("ü", "ue")
        .replace("ö", "oe")
        .replace("ä", "ae")
        .replace("ß", "ss")
        .replace(" ", "-")
        + ".de",
    )
    return (not any(host == domain or host.endswith("." + domain) for domain in preferred),)


def lookup(category, locality, budget):
    locality = validate_locality(locality)
    if category not in SERVICE_CATEGORIES or not locality:
        raise ChatError("invalid_locality", 400)
    records, seen = [], set()
    failed = False
    for suffix in ("Kontakt", "Beratungsstelle Kontakt"):
        if records or budget.counts.get("page", 0) >= 3:
            break
        budget.consume("search")
        # No transcript, model-generated query, personal name or diagnosis is accepted.
        query = f"{SERVICE_CATEGORIES[category]} {locality} {suffix}"
        try:
            data = transport.request_json(
                BRAVE_URL
                + "?"
                + urlencode({"q": query, "country": "DE", "search_lang": "de", "count": 5}),
                budget=budget,
                headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY},
            )
            if not isinstance(data, dict) or not isinstance(data.get("web", {}), dict):
                raise ChatError("search_unavailable")
            candidates = data.get("web", {}).get("results", [])
            if not isinstance(candidates, list):
                raise ChatError("search_unavailable")
            candidates = [
                item
                for item in candidates
                if isinstance(item, dict) and isinstance(item.get("url"), str)
            ]
            safe_candidates = []
            for item in candidates:
                try:
                    safe_candidates.append({"url": transport.safe_url(item["url"])})
                except ChatError:
                    failed = True
            for item in sorted(safe_candidates, key=lambda candidate: _rank(candidate, locality)):
                if budget.counts.get("page", 0) >= 3:
                    break
                try:
                    url = transport.safe_url(item["url"])
                    if url in seen:
                        continue
                    seen.add(url)
                    page = fetch_page(url, budget)
                    record = contact_record(*page, locality, len(records) + 1)
                    if record:
                        records.append(record)
                except ChatError as error:
                    if error.code in {"context_changed", "not_found"}:
                        raise
                    if error.code == "deadline_exceeded" and budget.remaining() < 1:
                        raise
                    failed = True
        except ChatError as error:
            if error.code in {"deadline_exceeded", "context_changed", "not_found"}:
                raise
            failed = True
            break  # An ambiguous search failure does not automatically trigger a paid retry.
    return records, "verified" if records else "unavailable" if failed else "no_results"
