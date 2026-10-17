#!/usr/bin/env python3
"""Seed the GenVM runner bundle into the Direct Mode cache.

`genlayer-test` 0.29.2 downloads its runner bundle from

    https://github.com/genlayerlabs/genvm/releases/download/<ver>/genvm-universal.tar.xz

but the v0.3.0-rc releases ship that asset as `genvm-runners-all.tar.xz`.
On a machine whose `~/.cache/gltest-direct` is already warm nothing notices;
on a fresh CI runner the request 404s and **every Direct Mode test errors at
import**, which looks exactly like a broken contract and is not one.

This downloads whichever asset the release actually has, checks that the
archive opens, and moves it into the cache under the name the test runner
looks for. It touches only `~/.cache/gltest-direct`: `genvm-linter` already
tries both asset names and resolves its own bundle, so seeding its cache
could only pin it to the wrong one.

    python scripts/fetch_genvm_bundle.py
    python scripts/fetch_genvm_bundle.py --version v0.3.0-rc7
"""

import argparse
import pathlib
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request


RELEASES = "https://github.com/genlayerlabs/genvm/releases"
DEFAULT_VERSION = "v0.3.0-rc7"
ASSET_NAMES = ["genvm-universal.tar.xz", "genvm-runners-all.tar.xz"]
CACHE = pathlib.Path.home() / ".cache" / "gltest-direct"


def download(version: str, destination: pathlib.Path) -> str:
    last_error = None
    for asset in ASSET_NAMES:
        url = "%s/download/%s/%s" % (RELEASES, version, asset)
        print("trying %s" % url, flush=True)
        request = urllib.request.Request(
            url, headers={"User-Agent": "claimcourt-bundle-seed"})
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                with destination.open("wb") as handle:
                    shutil.copyfileobj(response, handle, 1024 * 1024)
            return asset
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            last_error = error
            print("  not published under that name (404)", flush=True)
    raise SystemExit("no runner bundle asset found for %s (%s)"
                     % (version, last_error))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=DEFAULT_VERSION)
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / ("genvm-universal-%s.tar.xz" % args.version)
    if target.exists():
        # Both tools treat "the file exists" as "the file is good", so an
        # interrupted download would poison the cache until deleted by hand.
        # That is why this writes to a temp file and moves it into place.
        print("already cached: %s (%d bytes)"
              % (target, target.stat().st_size))
        return 0

    with tempfile.NamedTemporaryFile(dir=str(CACHE), suffix=".part",
                                     delete=False) as handle:
        partial = pathlib.Path(handle.name)
    try:
        asset = download(args.version, partial)
        with tarfile.open(partial, "r:xz") as archive:
            members = sum(1 for _ in archive)
        partial.replace(target)
        print("seeded %s from %s: %d bytes, %d entries"
              % (target, asset, target.stat().st_size, members))
    finally:
        if partial.exists():
            partial.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
