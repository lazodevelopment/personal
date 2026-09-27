#!/usr/bin/env python3
"""
test_classifier.py — runs the resume classifier locally against real files.
Same prompt, same model as the deployed parse_resume — but instant, no
deploys, no app. Point it at your junk documents and real resumes and see
exactly what Claude decides.

USAGE
  python test_classifier.py "C:\\path\\to\\price-sheet.pdf" "C:\\path\\to\\ein-letter.pdf" "C:\\path\\to\\real-resume.pdf"
  (prompts once for the Anthropic API key — hidden, not stored)
"""

import base64
import getpass
import json
import sys

import requests

PROMPT = """You are parsing a document uploaded to a hiring platform as \
a resume. FIRST decide whether this document actually IS a resume/CV. \
"isResume" is true ONLY if the document presents a person's employment \
history — at least one job or role they have held. Price sheets, invoices, \
brochures, contracts, menus, flyers, marketing materials, government letters, \
tax documents, IRS/EIN letters, certificates, and ID documents are NOT \
resumes, even when they contain a person's name. THEN, only if it truly is a \
resume, extract ONLY what is actually present. Never invent, never upgrade \
titles, never guess employers or dates. If a field is not clearly present, \
use null. Respond with ONLY a JSON object, no preamble, no markdown fences:
{
  "isResume": boolean,
  "documentType": string,
  "fullName": string|null,
  "email": string|null,
  "phone": string|null,
  "location": string|null,
  "yearsExperience": number|null,
  "roles": [{"title": string, "company": string|null, "startYear": number|null,
             "endYear": number|null, "summary": string|null}],
  "skills": [string],
  "certifications": [string],
  "lowConfidence": [string]
}"""

MEDIA = {"pdf": "application/pdf", "png": "image/png",
         "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}


def run(path, key):
    ext = path.rsplit(".", 1)[-1].lower()
    media = MEDIA.get(ext)
    if not media:
        print(f"  skip (unsupported type .{ext})")
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    block = "document" if media == "application/pdf" else "image"
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-sonnet-4-5", "max_tokens": 2000,
              "messages": [{"role": "user", "content": [
                  {"type": block, "source": {"type": "base64",
                                             "media_type": media, "data": b64}},
                  {"type": "text", "text": PROMPT}]}]},
        timeout=90)
    if r.status_code != 200:
        print(f"  API {r.status_code}: {r.text[:200]}")
        return
    text = "".join(b.get("text", "") for b in r.json().get("content", [])
                   if b.get("type") == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        p = json.loads(text)
    except Exception:
        print(f"  UNPARSEABLE response: {text[:200]}")
        return
    is_resume = p.get("isResume")
    roles = p.get("roles") or []
    skills = p.get("skills") or []
    print(f"  isResume: {is_resume}   documentType: {p.get('documentType')!r}")
    print(f"  roles: {len(roles)}  skills: {len(skills)}  name: {p.get('fullName')!r}")
    if not is_resume:
        verdict = "REJECTED by classifier"
    elif not roles and not skills:
        verdict = "REJECTED by structural backstop (no work history)"
    else:
        verdict = "ACCEPTED — would parse"
    print(f"  VERDICT: {verdict}")
    if is_resume and roles:
        for role in roles[:4]:
            print(f"    - {role.get('title')} @ {role.get('company')} "
                  f"({role.get('startYear')}-{role.get('endYear')})")


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python test_classifier.py "file1.pdf" ["file2.pdf" ...]')
    key = getpass.getpass("Anthropic API key (hidden): ").strip()
    for path in sys.argv[1:]:
        print(f"\n=== {path}")
        try:
            run(path, key)
        except FileNotFoundError:
            print("  file not found")


if __name__ == "__main__":
    main()
