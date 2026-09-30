#!/usr/bin/env python3
# =============================================================================
# wajue-feeds-proxy · GitHub Actions 抓取脚本
# -----------------------------------------------------------------------------
# 在 GitHub 境外 runner 上定时抓取被 GFW 拦截的 11 个国际媒体 RSS，
# 生成静态 XML 落库到 ./docs/feeds/<id>.xml，再由 GitHub Pages 托管，
# wajue 直接读 https://<USER>.github.io/<REPO>/feeds/<id>.xml 即可（通常不被墙）。
#
# 纯标准库实现（无第三方依赖），适配 GitHub Actions ubuntu-latest。
# 运行：python deploy/gh_rss_proxy/fetch_feeds.py   （在仓库根执行）
# =============================================================================
import json
import os
import socket
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED = REPO_ROOT / "deploy" / "feeds_proxy_shared.json"
OUT_DIR = REPO_ROOT / "docs" / "feeds"
STATUS_FILE = REPO_ROOT / "docs" / "status.json"
INDEX_FILE = REPO_ROOT / "docs" / "index.html"

UA = "Mozilla/5.0 (compatible; wajue-feeds-proxy/1.0)"
TIMEOUT = 20
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url: str) -> tuple[bool, bytes | str]:
    """返回 (ok, body_bytes_or_error_str)。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*", "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
            data = r.read()
            text = data[:200].decode("utf-8", "ignore").lstrip()
            if text.startswith("<") or text.startswith("<?"):
                return True, data
            return False, "non-xml body: " + text[:80]
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main() -> None:
    cfg = json.loads(SHARED.read_text(encoding="utf-8"))
    feeds = cfg["feeds"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    status = {}
    rows = []
    for fid, meta in feeds.items():
        candidates = [meta["url"]]
        if meta.get("fallback"):
            candidates.append(meta["fallback"])
        candidates.extend(meta.get("fallbacks") or [])
        ok = False
        src = None
        err = None
        for u in candidates:
            ok, body = fetch(u)
            if ok:
                src = u
                (OUT_DIR / f"{fid}.xml").write_bytes(body)  # type: ignore[arg-type]
                break
            err = body
        status[fid] = {
            "ok": ok,
            "name": meta["name"],
            "src": src,
            "error": (None if ok else err),
            "tags": meta.get("tags", []),
        }
        state = "OK" if ok else "FAIL"
        print(f"[{state}] {fid:18s} {meta['name']}" + ("" if ok else f"  -> {err}"))
        rows.append(
            f"<tr><td>{fid}</td><td>{meta['name']}</td>"
            f"<td>{'OK' if ok else 'FAIL'}</td>"
            f"<td>{src or '-'}</td>"
            f"<td>{'' if ok else (err or '')}</td>"
            f"<td><a href='feeds/{fid}.xml'>xml</a></td></tr>"
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    STATUS_FILE.write_text(json.dumps({"updated": ts, "status": status}, ensure_ascii=False, indent=2), encoding="utf-8")

    INDEX_FILE.write_text(
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
        f"<title>wajue feeds proxy</title></head><body><h1>wajue 境外媒体代理状态</h1>"
        f"<p>updated: {ts}</p><table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>id</th><th>name</th><th>state</th><th>source</th><th>error</th><th>xml</th></tr>"
        + "".join(rows)
        + "</table></body></html>",
        encoding="utf-8",
    )

    ok_n = sum(1 for s in status.values() if s["ok"])
    print(f"\nDONE: {ok_n}/{len(feeds)} feeds OK -> {OUT_DIR}")


if __name__ == "__main__":
    socket.setdefaulttimeout(TIMEOUT)
    main()
