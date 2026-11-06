"""Generate requested destination images with Cloudflare Workers AI (FLUX.1 schnell, free daily allocation).

Reads requests/*.json written by the CTC Vacation Alerts agent:
  {"file": "cancun-mexico-3.jpg", "prompt": "...", "city": "...", "country": "..."}
Writes img/<file> (16:9, 1024x576 JPEG), refreshes manifest.json, and moves each request to
requests/done/ (or requests/failed/ with the error). Existing images are never overwritten.
Secrets: CF_ACCOUNT_ID and CF_API_TOKEN (GitHub Actions repository secrets). Never printed.
"""
import base64
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODEL = "@cf/black-forest-labs/flux-1-schnell"


def generate(prompt: str) -> bytes:
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/ai/run/{MODEL}"
    body = json.dumps({"prompt": prompt[:2048], "steps": 8}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {os.environ['CF_API_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = json.loads(r.read())
    if not payload.get("success", True):
        raise RuntimeError(f"Cloudflare error: {payload.get('errors')}")
    return base64.b64decode(payload["result"]["image"])


def to_16x9(raw: bytes, width: int = 1024) -> bytes:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    th = round(w * 9 / 16)
    if th <= h:
        top = (h - th) // 2
        im = im.crop((0, top, w, top + th))
    else:
        tw = round(h * 16 / 9)
        left = (w - tw) // 2
        im = im.crop((left, 0, left + tw, h))
    im = im.resize((width, round(width * 9 / 16)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
    return out.getvalue()


def main() -> int:
    reqs = sorted((ROOT / "requests").glob("*.json"))
    (ROOT / "img").mkdir(exist_ok=True)
    for sub in ("done", "failed"):
        (ROOT / "requests" / sub).mkdir(parents=True, exist_ok=True)
    made = 0
    for p in reqs:
        job = json.loads(p.read_text())
        name = job.get("file", "")
        if not re.fullmatch(r"[a-z0-9\-]+\.jpg", name):
            (ROOT / "requests" / "failed" / p.name).write_text(json.dumps({**job, "error": "bad file name"}, indent=2))
            p.unlink()
            continue
        dest = ROOT / "img" / name
        if dest.exists():
            p.rename(ROOT / "requests" / "done" / p.name)
            continue
        try:
            dest.write_bytes(to_16x9(generate(job["prompt"])))
            p.rename(ROOT / "requests" / "done" / p.name)
            made += 1
            print(f"generated {name}")
        except (urllib.error.URLError, RuntimeError, KeyError, OSError) as err:
            msg = str(err).replace(os.environ.get("CF_API_TOKEN", "§"), "[REDACTED]")
            (ROOT / "requests" / "failed" / p.name).write_text(json.dumps({**job, "error": msg[:300]}, indent=2))
            p.unlink()
            print(f"failed {name}: {msg[:200]}")
        time.sleep(1)
    names = sorted(x.name for x in (ROOT / "img").glob("*.jpg"))
    (ROOT / "manifest.json").write_text(json.dumps({"images": names}, indent=2))
    print(f"{made} image(s) generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
