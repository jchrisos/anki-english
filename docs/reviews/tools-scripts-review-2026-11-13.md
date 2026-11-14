I reviewed all six scripts in `tools/`. Overall risk is moderate, and the security risk is low. The most serious problem is that an mp3 left incomplete by a failed edge-tts call passes as present, so a silent or truncated clip can reach a deck. That breaks the "audio never silent" rule. The `.apkg` write and the merge into `src/` can also leave a damaged file if a run is interrupted. The `--test` switch is sound in `build_decks.py`, `lint_content.py`, `build_audio.py` and `prepare_media.py`, which all use absolute paths from the repo root. `merge_batch.py` is the exception: it has no test mode and uses paths relative to the current directory. Note GUIDs and deck/model ids are pinned and stable. No `image` or `sense` value can be used to reach a path outside the media folder.

| ID | Severity | Class | Confidence | Location | Summary |
|---|---|---|---|---|---|
| F1 | High | bug | Confirmed | `tools/build_audio.py:40-43`, `tools/build_decks.py:409-411` | A failed TTS call leaves an empty or truncated mp3; later runs skip it and the build accepts it |
| F2 | Medium | bug | Confirmed | `tools/build_decks.py:490-495` | The `.apkg` is written in place, so a crash or Ctrl-C leaves a truncated package where the last good one was |
| F3 | Medium | bug | Confirmed | `tools/merge_batch.py:36-38, 169-173` | Two non-atomic writes to `src/` with paths relative to the current directory and no `--test` mode |
| F4 | Low | bug | Confirmed | `tools/prepare_media.py:27-47` | Overwrites an existing `.jpg` with no warning; a `.png` and `.webp` with the same name lose an image |
| F5 | Low | perf | Confirmed | `tools/build_decks.py:316-326` | The rewrite loads the whole package into memory and compresses it a second time |
| F6 | Low | bug | Likely | `tools/deck_common.py:151-154` | 32-bit media key, and nothing checks two entries don't share one |
| F7 | Low | bug | Confirmed | `tools/build_decks.py:349-411, 421` | The build doesn't enforce the sense format, the manifest, or a trimmed phrase, which all feed the GUID |
| F8 | Low | bug | Confirmed | `tools/deck_common.py:176-182` | `image_for` accepts any file as the image; a named `.png` wins over a converted `.jpg` |
| F9 | Low | bug | Confirmed | `tools/build_decks.py:428-430` | Definition, phrase and pronunciation go into HTML fields unescaped (none of the current text contains `<`, `>` or `&`) |
| F10 | Low | perf | Confirmed | genanki `package.py:30` (called from `tools/build_decks.py:492`) | Every build leaves a temporary sqlite file behind in `$TMPDIR` |

### F1 — A partial mp3 is accepted as finished (High)
- **What happens:** edge-tts's `save()` opens the target file for writing before any audio arrives (`communicate.py:612`: `with metadata, open(audio_fname, "wb") as audio: async for message in self.stream(): ...`). If the network drops, the 60 s receive timeout fires, `NoAudioReceived` is raised or the run is interrupted, an empty or partial file stays at the final path. `build_audio.py` exits 1 for that run. The next run prints `skip ... (exists)` because of line 40 (`if path.exists() and not force`). `validate()` only checks `path.exists()` (line 410), so the build passes and the card plays a silent or cut-off clip.
- **Fix:** save to `path.with_name(path.name + ".part")`, then `os.replace` on success, and delete the `.part` file in `except`/`finally`. In both the skip check and `validate()`, require `path.stat().st_size > 0`.
- **Test:** make `Communicate.stream` yield one chunk and then raise. Check that the target mp3 doesn't exist, and that `validate()` rejects a 0-byte mp3.

### F2 — The `.apkg` write isn't atomic (Medium)
- **What happens:** `genanki.Package(...).write_to_file(str(path), ...)` opens `decks/<kind>.apkg` in `'w'` mode, which truncates the previous good package first. It then streams every mp3 and image into it. Only the rewrite in `_make_zip_hermetic` goes through a temp file (`tmp.replace(path)`). An exception or Ctrl-C in genanki's write leaves a truncated zip at the real filename. A failure in the rewrite leaves a stray `<kind>.tmp` file. `main()` reports `FileNotFoundError` but doesn't remove either file.
- **Fix:** have genanki write to a temp file in `lay.out`, do the rewrite into a second temp file, `os.replace` it into place, and delete both temp files in `finally`.
- **Test:** make `zipfile.ZipFile.write` raise partway through. Check that the earlier `.apkg` is unchanged byte for byte and that no `.tmp` file remains.

### F3 — `merge_batch.py` writes are non-atomic and depend on the current directory (Medium)
- **What happens:** `MANIFEST_PATH = Path("src/index.csv")` and the other two paths are relative to the current directory, not built from `REPO_ROOT`/`layout()`. The order of operations is:
  1. `append_manifest(plan)` appends to `index.csv`.
  2. `SOURCE_PATH.write_text(...)` rewrites about 5,500 entries in place.

  If you interrupt it or the disk fills during step 2, `vocabulary.json` is left truncated (invalid JSON) and `index.csv` already has the 50 new rows. Lint reports a parse traceback rather than an `error:` line. Run from `tools/`, the script fails with an uncaught `FileNotFoundError`. Run from any other folder that has a `src/`, it writes there. There's no `--test`, so you can't rehearse it without touching production `src/`.
- **Smaller issue:** plan errors are labelled `index.csv:N` (by `check_manifest`) when they're really `plan.csv` lines.
- **Fix:** build the paths from `REPO_ROOT` (or add `layout(args.test)`). Write both files to temp files and `os.replace` them, source first, then manifest.
- **Test:** run with the working directory set to `tools/`, and with `write_text` made to raise. Check that `src/` is unchanged.

### F4 — `prepare_media.py` can overwrite images (Low)
- **What happens:** `target = source.with_suffix(".jpg")` replaces an existing `foo.jpg` without warning. If both `foo.png` and `foo.webp` exist, both write `foo.jpg` and both are deleted, so the first image is lost. sips output goes to `DEVNULL`, so a failure shows only as `CalledProcessError`, with no cause.
- **Fix:** skip, or fail, when the target already exists.

### F5 — The package is compressed twice (Low)
- **What happens:** `entries = [(info.filename, src.read(...)) ...]` holds every uncompressed mp3 and image in memory. Because genanki writes `ZIP_STORED`, the package is also written uncompressed once and then compressed again.
- **Fix:** stream each entry with `src.open(info)` and `out.open(zinfo, "w")` plus `shutil.copyfileobj`. This fits naturally into the F2 change.

### F6 — Media-key collisions go unnoticed (Low, Likely)
- **What happens:** `hexdigest()[:8]` is 32 bits. With 5,500 entries the chance of at least one collision is about 0.35%. If two notes share a key, they share mp3 filenames: the second note plays the first one's audio, and `build_audio` skips it as already existing. Nothing checks keys are unique.
- **Current data:** I found no duplicate `image` values in the three source files, and `merge_batch` sets `image` to the media key. I couldn't hash every entry because running Python was denied.
- **Fix:** check key uniqueness for each kind in `validate`/lint. Don't lengthen the key, because that would rename every existing media file.

### F7 — The build trusts lint for GUID inputs (Low)
- **What happens:** `guid = f"{prefix}:{entry['phrase']}:{entry['sense']}"` uses the raw values. `validate()` only checks that they aren't blank. The kebab-case sense rule (`SENSE_RE`), the lowercase phrase rule and the manifest match exist only in `lint_content.py`. So a build after a skipped lint accepts:
  - `"phrase": "run "`, which gets a new GUID, so the card starts over;
  - a `:` inside phrase or sense, which makes GUIDs ambiguous.
- **Fix:** apply `SENSE_RE`, `phrase == phrase.strip()` and the lowercase rule in `validate()`.

### F8 — `image_for` file matching (Low)
- **What happens:** `candidates = [path]` accepts any existing file, including a non-image, as `<img src>`. An authored `foo.png` is found before a converted `foo.jpg`, which contradicts the comment at `deck_common.py:47`.
- **Fix:** try the stem with each extension in `IMAGE_EXTS` order.

### F9 — Unescaped text in HTML fields (Low, latent)
- **What happens:** the fields are HTML because `bold_markup` emits `<b>`, but the text goes in as-is. A future definition containing `a < b` or `&` would render wrongly.
- **Fix:** run `html.escape` on the text before `bold_markup` (marking `**` doesn't involve any HTML characters).

### F10 — Temp sqlite file left behind (Low)
- **What happens:** genanki creates its database with `tempfile.mkstemp()` and never deletes it, so every build leaves a file in `$TMPDIR`. It's a library bug, not ours.
- **Workaround:** set `tempfile.tempdir` to a `TemporaryDirectory` around the call.

### By axis
- **Concurrency/resources:** F1 and F10. `build_audio` uses `gather(return_exceptions=True)` behind a semaphore and edge-tts's default 10 s connect / 60 s read timeouts. All files are opened in `with` blocks.
- **Security: no findings.**
  - `subprocess` (`sips`) gets a list of arguments, no shell, and an absolute path, so a filename can't be read as an option.
  - No eval, pickle, YAML or SQL.
  - The only network call is edge-tts to its fixed endpoint.
  - `sense` and `phrase` reach filenames only through a SHA-1 hash.
  - `image` is checked against `Path(name).name` in the build and against `/` in lint. `..` passes that check but resolves to a directory, so `is_file()` rejects it.
  - SHA-1 is used only as a naming key, not for security.
  - `--chunk-dir` is only read from.
- **Docstrings vs .gitignore:** two docstrings are out of date. `build_decks.py:18` and the comment on `_make_zip_hermetic` say packages are committed, and `build_audio.py:9-11` says mp3s are committed. `.gitignore` excludes both `*.apkg` and `*.mp3`, so this is wording only, with no effect on behaviour.

### Coverage
- **Read in full:** all six scripts, `AGENTS.md`, `.gitignore` and `requirements.txt` (pinned `genanki==0.13.1`, `edge-tts==7.3.1`). I also read the relevant parts of genanki's `package.py` and edge-tts's `communicate.py`, and searched the source JSON for HTML characters and duplicate `image` values.
- **Interpreter:** `.venv` Python 3.10 (going by `.venv/bin/python3.10`).
- **Gates — none ran.** Bash was denied for running Python, for `compileall`, and for checking whether ruff, flake8, mypy, bandit or pip-audit are installed. Only `grep` was allowed. There is no test suite, no lint config and no CI.
- **Not reviewed:** the `.okf/` design notes, the authored content itself, and the rest of the third-party libraries.

## 2026-11-13 — revalidation

> Appended by the calling session: the reviewer's own shell was denied in this round, so no
> gate ran inside the review. The gates listed below were run separately, after the fixes.

I couldn't write the revalidation into the file. This session denied every Bash command and the Edit tool, so `tee -a`, `compileall`, the lint and the `--test` build were all blocked. I stopped there rather than look for another way to write the file. Everything below comes from reading the six scripts, `.gitignore` and genanki's `package.py`. **No gate ran.**

**Result:** reading the code, all of F1–F10 are fixed. The fixes added four Low issues and no security or performance problems.

| ID | Status | Code checked |
|---|---|---|
| F1 | Fixed | `tools/build_audio.py:52-65` (`.mp3.part`, size check, cleanup on Ctrl-C), `tools/build_decks.py:465-467` (rejects 0-byte mp3s). A non-empty clip cut short *before* this fix would still pass; I couldn't list `media/` to check for one. |
| F2 | Fixed | `tools/build_decks.py:333-362`: write to `.build`, copy to `.tmp`, then `replace`; both removed in `finally`. |
| F3 | Fixed, see N2 | `tools/merge_batch.py:174-181, 188-197, 227-228`: paths built from the repo root, `--test` added, each file replaced in one step. Plan errors now point at `plan.csv` (`tools/lint_content.py:118-124`). |
| F4 | Fixed | `tools/prepare_media.py:33-36, 37-65`: skips an existing `.jpg`, stages the output, shows sips' error. |
| F5 | Fixed | `tools/build_decks.py:349-358`: entries are copied in streamed chunks, not held in memory. |
| F6 | Fixed in the build only | `tools/build_decks.py:454-456`. Neither the lint nor `merge_batch` checks it, but a collision still fails the build loudly. |
| F7 | Fixed, see N3 | `tools/deck_common.py:153-172`, `tools/build_decks.py:406-408, 563-569`, `tools/lint_content.py:135-137, 212-214`. |
| F8 | Fixed | `tools/deck_common.py:204-210`: only the stem plus an image extension is tried, in order. |
| F9 | Fixed | `tools/build_decks.py:470-482, 499-501, 515, 522`: text is HTML-escaped before the bold markup is added. |
| F10 | Fixed | `tools/build_decks.py:336-347`. genanki's `package.py:30` calls `mkstemp()` without a folder, so the temporary-directory swap catches its file. |

**New findings (all Low):**
- **N1 (Likely):** the new staging files aren't in `.gitignore`. They are `*.apkg.build` / `*.apkg.tmp`, `*.mp3.part`, `src/*.tmp` and `media/*.part.jpg`. A hard kill (where the cleanup never runs) leaves one behind, and `git add -A` would commit it. A leftover `.part.jpg` looks like real committed art. **Fix:** add `*.build`, `*.tmp`, `*.part` and `*.part.jpg` to `.gitignore`.
- **N2 (Confirmed):** `tools/merge_batch.py:227-228` writes the source before the manifest. Its own docstring (`:16-19`) argues for the opposite order, and the comment at `:225-226` describes the opposite order's outcome. If the second write fails, rerunning the merge appends the same 50 entries again: the duplicate check (`:134-138`) only looks at the manifest. **Fix:** write the manifest first, and also reject phrase/sense pairs already in the source.
- **N3 (Confirmed):** the lint strips spaces from every manifest cell (`tools/lint_content.py:112`, and `tools/merge_batch.py:78` for the plan). Its trailing-space check on the manifest can therefore never fire. The build doesn't strip (`tools/build_decks.py:542`), so a row like `run ` passes the lint and then fails the build as "not in index.csv".
- **N4 (Confirmed):** an entry with no `phrase` or `sense` key crashes the build with a raw Python error at `tools/build_decks.py:562/566`, before the field checks run. `main()` only reports its own error types (`:613`).

**Not verified:** that the five re-synthesized mp3s are non-empty, that the current content passes the new identity rules (lowercase phrase, kebab-case sense), and whether ruff or mypy are installed.

To get the section into the file, either:
- allow Bash or Edit and ask me again, and I'll append it with `tee -a`, keeping the original findings above it; or
- run the append yourself. I can give you the full section text as a `tee -a` heredoc.
