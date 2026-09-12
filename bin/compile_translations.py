#!/usr/bin/env python3
"""Validate and compile the German Django catalogue without system gettext tools.

Run bin/translations after editing a PO file. GNU gettext is only needed when
extracting new source strings with Django's standard makemessages command.
"""

import argparse
import gettext
import re
from pathlib import Path

import polib
from django.utils.translation import gettext_noop, ngettext_lazy

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"%\([^)]+\)[#0 +\-]?(?:\d+|\*)?(?:\.(?:\d+|\*))?[diouxXeEfFgGcrsa]")


# Keep runtime-generated Django form copy in the project catalogue so German
# account screens consistently address the member as "du". These declarations
# are also discovered by Django's standard makemessages command.
def django_ui_messages():
    return (
        gettext_noop("Password"),
        gettext_noop("Password confirmation"),
        gettext_noop("Old password"),
        gettext_noop("New password"),
        gettext_noop("New password confirmation"),
        gettext_noop("Email"),
        gettext_noop("Enter the same password as before, for verification."),
        gettext_noop("The two password fields didn’t match."),
        gettext_noop("Your old password was entered incorrectly. Please enter it again."),
        gettext_noop("Your password can’t be too similar to your other personal information."),
        gettext_noop("Your password can’t be a commonly used password."),
        gettext_noop("Your password can’t be entirely numeric."),
        gettext_noop("This password is too common."),
        gettext_noop("This password is entirely numeric."),
        gettext_noop("The password is too similar to the %(verbose_name)s."),
        gettext_noop("This field is required."),
        gettext_noop("Enter a valid email address."),
        ngettext_lazy(
            "Your password must contain at least %(min_length)d character.",
            "Your password must contain at least %(min_length)d characters.",
            "min_length",
        ),
    )


def compile_catalogue(check_only=False):
    path = ROOT / "locale/de/LC_MESSAGES/django.po"
    if not path.is_file():
        raise ValueError(f"Missing translation catalogue: {path.relative_to(ROOT)}")
    catalog = polib.pofile(str(path), check_for_duplicates=True)
    problems = []
    active = [entry for entry in catalog if not entry.obsolete]
    for entry in active:
        if "fuzzy" in entry.flags or not entry.translated():
            problems.append(f"Untranslated or fuzzy: {entry.msgid!r}")
            continue
        translations = list(entry.msgstr_plural.values()) if entry.msgid_plural else [entry.msgstr]
        expected = set(PLACEHOLDER.findall(entry.msgid))
        for translation in translations:
            if set(PLACEHOLDER.findall(translation)) != expected:
                problems.append(f"Changed interpolation placeholders: {entry.msgid!r}")
    if problems:
        raise ValueError("\n".join(problems))
    compiled = path.with_suffix(".mo")
    if not check_only:
        catalog.save_as_mofile(str(compiled))
        with compiled.open("rb") as stream:
            gettext.GNUTranslations(stream)
    print(
        f"PASS: {len(active)} German translations {'validated' if check_only else 'validated and compiled'}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Validate PO entries without writing MO output."
    )
    args = parser.parse_args()
    try:
        compile_catalogue(args.check)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Translation check failed: {error}\n")


if __name__ == "__main__":
    main()
