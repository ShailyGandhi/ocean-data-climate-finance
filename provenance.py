"""Cached, provenance-recording downloads shared by all scripts.

Source data are NOT redistributed with this package: every source is openly available from its provider and is
downloaded on first use. Each cache folder (data_raw/) holds:

  manifest.csv  the versions used for the paper: URL, retrieval time (UTC), size and SHA-256 (part of the package;
                a run never changes existing rows; a row is added only when the code requests a source that is not
                listed yet, i.e., when the analysis itself is extended)
  run_log.csv   the versions used in the current run, and whether each is identical to the paper's version
                (written by every run; not part of the package)

If a provider has updated a file since the paper's retrieval, the run continues with the current version, warns, and
logs it as UPDATED; check_reported_values.py then shows whether any reported value changes. Set STRICT_SOURCES=1 to
stop instead. Downloads are retried on transient network errors and written to a temporary file that is renamed only
when complete.
"""
import csv
import datetime as dt
import hashlib
import os
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
FIELDS = ["file", "url", "retrieved_utc", "bytes", "sha256", "note"]
LOG_FIELDS = ["file", "retrieved_utc", "bytes", "sha256", "status"]


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path, key="file"):
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {row[key]: row for row in csv.DictReader(fh)}


def _write(path, rows, fields):
    tmp = path + ".part"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))
    os.replace(tmp, path)


def _download(url, path, name, timeout):
    tmp = path + ".part"
    for attempt in range(1, 5):  # retry transient network errors (timeouts, resets, HTTP 5xx)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r, \
                    open(tmp, "wb") as fh:
                fh.write(r.read())
            break
        except (OSError, TimeoutError) as err:  # URLError and HTTPError are OSError subclasses
            if attempt == 4 or getattr(err, "code", 500) < 500:
                raise
            print(f"download of {name} failed ({err}); retry {attempt} of 3 in {10 * attempt} s")
            time.sleep(10 * attempt)
    os.replace(tmp, path)


def fetch(url, name, cache_dir, timeout=600):
    """Return the local path of `name` in `cache_dir`, downloading `url` if it is not cached yet."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, name)
    manifest, log = os.path.join(cache_dir, "manifest.csv"), os.path.join(cache_dir, "run_log.csv")
    downloaded = not os.path.exists(path)
    if downloaded:
        _download(url, path, name, timeout)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    when = now if downloaded else dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    digest, size = _sha256(path), os.path.getsize(path)
    paper = _read(manifest)
    if name in paper:
        if paper[name]["url"] != url:
            raise RuntimeError(f"{name}: the code requests {url}, but the paper's version came from "
                               f"{paper[name]['url']} (see {manifest})")
        if paper[name]["sha256"] == digest:
            status = "identical to the paper's version"
        else:
            status = (f"UPDATED: differs from the paper's version (retrieved {paper[name]['retrieved_utc']}, "
                      f"sha256 {paper[name]['sha256'][:12]}...)")
            if os.environ.get("STRICT_SOURCES") == "1":
                if downloaded:
                    os.remove(path)
                raise RuntimeError(f"{name} {status}; STRICT_SOURCES=1 is set, so the run stops")
            print(f"WARNING: {name} has been updated by its provider since the paper's retrieval; using the current "
                  "version (see run_log.csv and check_reported_values.py)")
    else:  # a source not yet in the manifest (author workflow): record it as a paper version
        paper[name] = {"file": name, "url": url, "retrieved_utc": when, "bytes": size, "sha256": digest, "note": ""}
        _write(manifest, paper, FIELDS)
        status = "new source added to manifest.csv"
    runs = _read(log)
    runs[name] = {"file": name, "retrieved_utc": when, "bytes": size, "sha256": digest, "status": status}
    _write(log, runs, LOG_FIELDS)
    return path
