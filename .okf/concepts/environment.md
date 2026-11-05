---
type: environment
title: "Verified local Anki and Python environment"
description: "Machine state confirmed at the time of writing: Anki 25.09, pyenv Python 3.10.16, no genanki, no AnkiConnect."
status: active
verified:
  - by: "OpenCode session"
    at: "2026-11-05"
sources:
  - uri: "local://machine-inspection"
    credibility: high
stale_after: "2027-02-05"
---

# Verified local Anki and Python environment

Checked on this machine on 2026-11-05. Re-verify before relying on any line; Anki and
pyenv versions drift, and missing tooling is the usual cause of a failed first run.

## Anki

- Desktop **25.09** at `/Applications/Anki.app`.
- Profile `User 1`; data under `~/Library/Application Support/Anki2/`.
- **No `anki` binary on `PATH`** (the CLI lives inside the app bundle). Do not write
  scripts that shell out to `anki`; produce a file and let the user import it.
- Add-ons installed: **AwesomeTTS**, **Review Heatmap**.
- **AnkiConnect is not installed**, so nothing listens on `127.0.0.1:8765`. Adding
  notes directly to a live collection over HTTP is not available unless the user
  installs it — do not build an AnkiConnect workflow by default, and do not install the
  add-on without asking.

## Python

- `python3` resolves through pyenv to **3.10.16** (global default); **3.11.5** is also
  installed.
- **No `uv`, no `pipx`.**
- **`genanki` is not installed** in the default interpreter.
- Implication: create a repo-local `.venv` and pin dependencies. Never `pip install`
  into the pyenv global interpreter, and do not assume a `pyproject.toml`/lockfile
  exists yet.

## Portability note

These are facts about one laptop, not project requirements. Keep the generator runnable
with plain `python3 -m venv` + `pip install -r requirements.txt` so it is not silently
bound to this machine's pyenv setup.
