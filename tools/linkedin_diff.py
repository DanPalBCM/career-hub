#!/usr/bin/env python3
"""Generate a manual LinkedIn sync checklist from the canonical career-hub files.

This is a CHECKLIST GENERATOR and nothing else. It reads publications.bib,
software.bib, and cv/cv.yaml from disk and prints a Markdown checklist grouped
by LinkedIn section. It never opens a network connection, never scrapes
LinkedIn, and never automates anything against LinkedIn.

Usage:
    python tools/linkedin_diff.py                # print to stdout
    python tools/linkedin_diff.py -o linkedin.md # write to a file
    python tools/linkedin_diff.py --repo-root /path/to/career-hub

Dependencies: Python standard library, pyyaml, bibtexparser.
    python -m pip install pyyaml bibtexparser
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

STATUS_FIELD = "(status: ____)"

MISSING_DEPS_MESSAGE = """
Missing dependency: {name}

tools/linkedin_diff.py needs two third-party packages beyond the standard
library. Install them with:

    python -m pip install pyyaml bibtexparser

(Or, if you prefer an isolated environment:
    python -m venv .venv && source .venv/bin/activate
    python -m pip install pyyaml bibtexparser)
"""

# ---------------------------------------------------------------------------
# Dependency loading, with a clear message instead of a traceback
# ---------------------------------------------------------------------------

def _require(module_name: str, friendly_name: str):
    try:
        return __import__(module_name)
    except ImportError:
        sys.stderr.write(MISSING_DEPS_MESSAGE.format(name=friendly_name))
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# BibTeX loading (works with bibtexparser v1 and v2)
# ---------------------------------------------------------------------------

def _clean(value: Any) -> str:
    """Normalize a BibTeX field value to a single-line string."""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.strip().strip("{}").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def load_bib(path: Path) -> List[Dict[str, str]]:
    """Return a list of dicts with lowercase field names plus ID and ENTRYTYPE."""
    bibtexparser = _require("bibtexparser", "bibtexparser")

    if not path.is_file():
        sys.stderr.write(f"Not found: {path}\n")
        raise SystemExit(1)

    text = path.read_text(encoding="utf-8")
    entries: List[Dict[str, str]] = []

    if hasattr(bibtexparser, "parse_string"):
        # bibtexparser v2
        library = bibtexparser.parse_string(text)
        for entry in library.entries:
            record: Dict[str, str] = {
                "ID": entry.key,
                "ENTRYTYPE": entry.entry_type.lower(),
            }
            for field in entry.fields:
                record[field.key.lower()] = _clean(field.value)
            entries.append(record)
    else:
        # bibtexparser v1
        database = bibtexparser.loads(text)
        for raw in database.entries:
            record = {}
            for key, value in raw.items():
                if key in ("ID", "ENTRYTYPE"):
                    record[key] = str(value)
                else:
                    record[key.lower()] = _clean(value)
            record.setdefault("ID", "")
            record.setdefault("ENTRYTYPE", "")
            record["ENTRYTYPE"] = record["ENTRYTYPE"].lower()
            entries.append(record)

    return entries


def load_yaml(path: Path) -> Dict[str, Any]:
    yaml = _require("yaml", "pyyaml")

    if not path.is_file():
        sys.stderr.write(f"Not found: {path}\n")
        raise SystemExit(1)

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.stderr.write(f"Expected a mapping at the top level of {path}\n")
        raise SystemExit(1)
    return data


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def item(out: io.StringIO, text: str, sub: Optional[Iterable[str]] = None) -> None:
    out.write(f"- [ ] {text} {STATUS_FIELD}\n")
    for line in sub or []:
        out.write(f"  - {line}\n")


def heading(out: io.StringIO, text: str, level: int = 2) -> None:
    out.write(f"\n{'#' * level} {text}\n\n")


def note(out: io.StringIO, text: str) -> None:
    out.write(f"> {text}\n\n")


def keywords_of(entry: Dict[str, str]) -> List[str]:
    raw = entry.get("keywords", "")
    return [k.strip().lower() for k in raw.split(",") if k.strip()]


def date_range(obj: Dict[str, Any]) -> str:
    start = obj.get("start_date")
    end = obj.get("end_date")
    if start and end:
        return f"{start}–{end}"
    if start:
        return f"{start}–present"
    if obj.get("date"):
        return str(obj["date"])
    return ""


def authors_short(entry: Dict[str, str], limit: int = 3) -> str:
    raw = entry.get("author", "")
    if not raw:
        return ""
    parts = [p.strip() for p in raw.split(" and ") if p.strip()]
    shown = parts[:limit]
    tail = " et al." if len(parts) > limit else ""
    return "; ".join(shown) + tail


def cv_sections(cv: Dict[str, Any]) -> Dict[str, Any]:
    inner = cv.get("cv")
    if not isinstance(inner, dict):
        sys.stderr.write("cv.yaml has no top-level cv: key.\n")
        raise SystemExit(1)
    sections = inner.get("sections")
    if not isinstance(sections, dict):
        sys.stderr.write("cv.yaml has no cv.sections: mapping.\n")
        raise SystemExit(1)
    return sections


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def section_experience(out: io.StringIO, sections: Dict[str, Any]) -> None:
    heading(out, "Experience")
    entries = sections.get("experience") or []
    if not entries:
        note(out, "No experience section found in cv/cv.yaml.")
        return
    for job in entries:
        position = job.get("position", "TODO(human): position")
        company = job.get("company", "TODO(human): company")
        location = job.get("location", "")
        when = date_range(job)
        bits = [b for b in (location, when) if b]
        suffix = f" ({' · '.join(bits)})" if bits else ""
        item(out, f"{position} — {company}{suffix}")


def section_education(out: io.StringIO, sections: Dict[str, Any]) -> None:
    heading(out, "Education")
    entries = sections.get("education") or []
    if not entries:
        note(out, "No education section found in cv/cv.yaml.")
        return
    for edu in entries:
        degree = edu.get("degree", "")
        area = edu.get("area", "")
        institution = edu.get("institution", "TODO(human): institution")
        when = date_range(edu)
        label = ", ".join(b for b in (degree, area) if b)
        suffix = f" ({when})" if when else ""
        item(out, f"{label or 'Degree'} — {institution}{suffix}")


def section_publications(out: io.StringIO, pubs: List[Dict[str, str]]) -> None:
    heading(out, "Publications")
    note(
        out,
        "Manuscripts under review with no public preprint are metadata only: "
        "title, authors, venue, status. Do not post findings or numbers.",
    )

    groups = [
        ("published", "Published"),
        ("under-review", "Under review"),
        ("preprint", "Preprints"),
    ]
    seen = set()

    for key, label in groups:
        matching = [p for p in pubs if key in keywords_of(p)]
        heading(out, label, level=3)
        if not matching:
            note(out, "None.")
            continue
        for pub in matching:
            seen.add(pub.get("ID", ""))
            title = pub.get("title", "TODO(human): title")
            venue = pub.get("journal") or pub.get("howpublished") or ""
            year = pub.get("year", "")
            doi = pub.get("doi", "")
            sub = []
            if venue or year:
                sub.append(" ".join(b for b in (venue, f"({year})" if year else "") if b))
            authors = authors_short(pub)
            if authors:
                sub.append(f"Authors: {authors}")
            if doi:
                sub.append(f"DOI: {doi}")
            repo = pub.get("companion-repo", "")
            if repo:
                sub.append(f"Companion repo: {repo}")
            item(out, title, sub)

    leftovers = [p for p in pubs if p.get("ID", "") not in seen]
    if leftovers:
        heading(out, "Ungrouped (fix `keywords` in publications.bib)", level=3)
        for pub in leftovers:
            item(out, pub.get("title", pub.get("ID", "?")))


def section_projects(out: io.StringIO, software: List[Dict[str, str]]) -> None:
    heading(out, "Projects")
    note(
        out,
        "Forks stay forks and private repositories stay private. Repeat the "
        "fork/private status in the LinkedIn description; do not present a "
        "fork as original work.",
    )
    if not software:
        note(out, "No entries found in software.bib.")
        return
    for repo in software:
        title = repo.get("title", repo.get("ID", "?"))
        url = repo.get("url", "")
        kws = ", ".join(keywords_of(repo)) or "TODO(human): keywords"
        sub = [f"Status: {kws}"]
        if url:
            sub.append(f"URL: {url}")
        license_field = repo.get("license", "")
        if license_field:
            sub.append(f"License: {license_field}")
        related = repo.get("related-doi", "")
        if related:
            sub.append(f"Related DOI: {related}")
        if "private" in keywords_of(repo):
            sub.append("Private: link only; do not describe internal detail.")
        item(out, f"{title}", sub)


def section_honors(out: io.StringIO, sections: Dict[str, Any]) -> None:
    heading(out, "Honors & Awards")
    entries = sections.get("awards_and_honors") or []
    if not entries:
        note(out, "No awards_and_honors section found in cv/cv.yaml.")
        return
    for award in entries:
        if isinstance(award, dict) and "label" in award:
            item(out, f"{award.get('details', '')} ({award.get('label', '')})")
        elif isinstance(award, dict) and "bullet" in award:
            item(out, str(award["bullet"]))
        else:
            item(out, str(award))

    grants = sections.get("grants") or []
    if grants:
        heading(out, "Grants (list under Honors on LinkedIn)", level=3)
        for grant in grants:
            if isinstance(grant, dict):
                item(out, f"{grant.get('label', '')} — {grant.get('details', '')}")
            else:
                item(out, str(grant))


def section_certifications(out: io.StringIO, sections: Dict[str, Any]) -> None:
    heading(out, "Licenses & Certifications")
    entries = sections.get("certifications_and_training") or []
    if not entries:
        note(out, "No certifications_and_training section found in cv/cv.yaml.")
        return
    for cert in entries:
        if isinstance(cert, dict):
            item(out, f"{cert.get('label', '')} — {cert.get('details', '')}")
        else:
            item(out, str(cert))


def section_profile(out: io.StringIO, cv: Dict[str, Any]) -> None:
    heading(out, "Profile basics")
    inner = cv.get("cv", {})
    item(out, f"Name: {inner.get('name', 'TODO(human)')}")
    item(out, f"Location: {inner.get('location', 'TODO(human)')}")
    item(out, f"Contact email: {inner.get('email', 'TODO(human)')}")
    item(out, f"Website link: {inner.get('website', 'TODO(human)')}")
    item(out, "Featured: link the current CV PDF (assets/cv/cv-latest.pdf)")
    summary = inner.get("sections", {}).get("summary") or []
    if summary:
        item(out, "About section matches the CV summary", [str(summary[0])])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_checklist(repo_root: Path) -> str:
    pubs = load_bib(repo_root / "publications.bib")
    software = load_bib(repo_root / "software.bib")
    cv = load_yaml(repo_root / "cv" / "cv.yaml")
    sections = cv_sections(cv)

    out = io.StringIO()
    out.write("# LinkedIn sync checklist\n\n")
    out.write(
        "Generated from `publications.bib`, `software.bib`, and `cv/cv.yaml`. "
        "This file is a worksheet: open LinkedIn, work down the list by hand, "
        "and write what you did in each `(status: ____)` field "
        "(for example `added`, `updated`, `already correct`, `skipped`).\n\n"
    )
    out.write(
        "This script does not contact LinkedIn and does not automate anything "
        "against it.\n"
    )

    section_profile(out, cv)
    section_experience(out, sections)
    section_education(out, sections)
    section_publications(out, pubs)
    section_projects(out, software)
    section_honors(out, sections)
    section_certifications(out, sections)

    out.write("\n---\n\n")
    out.write(
        "Reminder: nothing here should include PHI, patient-level data, "
        "unpublished numbers, or claims that are not in a published paper, a "
        "submitted manuscript, a preprint, or the CV.\n"
    )
    return out.getvalue()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print a manual LinkedIn sync checklist from career-hub sources.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root (default: the parent of tools/).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write the checklist to this file instead of stdout.",
    )
    args = parser.parse_args(argv)

    checklist = build_checklist(args.repo_root.resolve())

    if args.output:
        args.output.write_text(checklist, encoding="utf-8")
        sys.stderr.write(f"Wrote {args.output}\n")
    else:
        sys.stdout.write(checklist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
