#!/usr/bin/env python3
"""Download artifacts from a workflow run and merge coverage.xml files.

Usage: download_and_merge_artifacts.py <run_id> <owner/repo>

Requires env var `GITHUB_TOKEN` with permission to read workflow run artifacts.

The script downloads all artifacts attached to the specified run, extracts any
`coverage.xml` files, reads `lines-covered` and `lines-valid` attributes when
available and sums them to compute an overall coverage percentage. Falls back
to counting <line hits="..."> elements if attributes are missing.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.request import Request, urlopen
import zipfile


def api_get(url: str, token: str):
    req = Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    with urlopen(req) as resp:
        return json.load(resp)


def download_url(url: str, token: str, dest: Path):
    req = Request(url)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    with urlopen(req) as resp, open(dest, "wb") as out:
        out.write(resp.read())


def parse_root_counts(path: Path):
    # return (covered, valid) or None if not present
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(path)
        root = tree.getroot()
        # coverage.py / cobertura style root attrs
        covered = root.attrib.get("lines-covered") or root.attrib.get("lines_covered")
        valid = root.attrib.get("lines-valid") or root.attrib.get("lines_valid")
        if covered is not None and valid is not None:
            return int(covered), int(valid)
        # sometimes line-rate present; try to use lines-valid if available
        lr = root.attrib.get("line-rate") or root.attrib.get("line_rate")
        if lr is not None and (
            valid := root.attrib.get("lines-valid") or root.attrib.get("lines_valid")
        ):
            try:
                v = float(lr)
                return int(float(valid) * v), int(valid)
            except Exception:
                pass
    except Exception:
        return None
    return None


def fallback_count(path: Path):
    # Count <line hits="..."> occurrences
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(path)
        root = tree.getroot()
        total = 0
        covered = 0
        for elem in root.iter():
            if elem.tag.lower().endswith("line") and "hits" in elem.attrib:
                total += 1
                try:
                    if int(elem.attrib.get("hits", "0")) > 0:
                        covered += 1
                except Exception:
                    pass
        return covered, total
    except Exception:
        return 0, 0


def main(argv):
    if len(argv) < 3:
        print("Usage: download_and_merge_artifacts.py <run_id> <owner/repo>", file=sys.stderr)
        return 2
    run_id = argv[1]
    repo = argv[2]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set", file=sys.stderr)
        return 2

    owner, repo_name = repo.split("/", 1)
    artifacts_api = (
        f"https://api.github.com/repos/{owner}/{repo_name}/actions/runs/{run_id}/artifacts"
    )
    data = api_get(artifacts_api, token)
    artifacts = data.get("artifacts", [])
    if not artifacts:
        print("No artifacts found", file=sys.stderr)
        print("unknown")
        return 0

    tmpdir = Path(tempfile.mkdtemp())
    collected = []
    for art in artifacts:
        url = art.get("archive_download_url")
        if not url:
            continue
        dest = tmpdir / f"artifact-{art['id']}.zip"
        download_url(url, token, dest)
        try:
            with zipfile.ZipFile(dest, "r") as z:
                for name in z.namelist():
                    if name.endswith("coverage.xml") or name.endswith("/coverage.xml"):
                        outpath = tmpdir / f"{art['id']}-{Path(name).name}"
                        z.extract(name, tmpdir)
                        extracted = tmpdir / name
                        # move to top-level to simplify path
                        extracted.rename(outpath)
                        collected.append(outpath)
        except zipfile.BadZipFile:
            continue

    # If no coverage.xml files found inside artifacts, try to see if artifact names themselves are coverage.xml
    if not collected:
        # Some workflows may upload coverage.xml directly (artifact name)
        for art in artifacts:
            if art.get("name", "").startswith("coverage"):
                url = art.get("archive_download_url")
                dest = tmpdir / f"artifact-{art['id']}.zip"
                download_url(url, token, dest)
                try:
                    with zipfile.ZipFile(dest, "r") as z:
                        for name in z.namelist():
                            if name.endswith("coverage.xml"):
                                outpath = tmpdir / f"{art['id']}-{Path(name).name}"
                                z.extract(name, tmpdir)
                                extracted = tmpdir / name
                                extracted.rename(outpath)
                                collected.append(outpath)
                except zipfile.BadZipFile:
                    continue

    if not collected:
        print("No coverage.xml files found in artifacts", file=sys.stderr)
        print("unknown")
        return 0

    total_covered = 0
    total_valid = 0
    for c in collected:
        counts = parse_root_counts(c)
        if counts is None:
            counts = fallback_count(c)
        covered, valid = counts
        total_covered += covered
        total_valid += valid

    if total_valid == 0:
        print("unknown")
        return 0
    pct = total_covered / total_valid
    print(f"{round(pct * 100)}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
