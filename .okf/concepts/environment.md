---
type: environment
title: "Verified local Anki and Python environment"
description: "Machine state confirmed at the time of writing: Anki 25.09, pyenv Python 3.10.16, edge-tts 7.3.1, no genanki, no AnkiConnect."
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
- **`genanki` is not installed** in the default interpreter; **`genanki==0.13.1` is
  installed in the repo-local `.venv`** (`requirements.txt`), which is what
  `tools/build_decks.py` uses.
- **`edge-tts` 7.3.1 is installed** (`/Users/julio/.pyenv/shims/edge-tts`), imported by the
  pyenv global 3.10.16 interpreter. The user installed it there; it works, but it bends the
  rule below, so pin `edge-tts==7.3.1` in the repo `.venv` before relying on it.
- Implication: create a repo-local `.venv` and pin dependencies. Never `pip install`
  into the pyenv global interpreter, and do not assume a `pyproject.toml`/lockfile
  exists yet.

## Audio tooling

- `edge-tts --list-voices` reports the `en-US` female neural voices used for cards:
  `AvaNeural`, `AriaNeural`, `JennyNeural`, `EmmaNeural`, `MichelleNeural`, plus
  `AnaNeural` (a child voice — not used). Pinned voice: `en-US-AvaNeural`, `--rate=-10%`.
- Synthesis is a **network call** to Microsoft's service; it fails offline and is not
  guaranteed byte-identical between runs, so generated mp3s are committed artifacts.
- `ffmpeg`, `lame` and `afinfo` exist on this machine. They are **not** part of the
  pipeline: one edge-tts call per card already yields the target + definition + dialog in
  one file. Keep them optional so the build does not grow a dependency for nothing.
- Verified end-to-end on 2026-11-05: the three-part script for one card produced a
  ~53 KB, 8.9 s mp3.

## Portability note

These are facts about one laptop, not project requirements. Keep the generator runnable
with plain `python3 -m venv` + `pip install -r requirements.txt` so it is not silently
bound to this machine's pyenv setup.
