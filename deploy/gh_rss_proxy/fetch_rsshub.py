#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_rsshub.py —— wajue 路线 B(RSSHub) 的 GitHub Pages 抓取器。
在 GitHub Actions runner(境外网络) 服务端抓取公共 RSSHub 实例的路由，
把生成的 RSS XML 发布到 gh-pages 的 docs/rsshub/<id>.xml，
供 wajue 采集器(用户侧) 经 https://<user>.github.io/wajue-rss-proxy/rsshub/<id>.xml 消费。

与 fetch_feeds.py 的区别：这里抓的是 RSSHub 路由(网页转 RSS)，不是原生 RSS。
"""
import json
import os
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (compatible; wajue-rss-proxy/1.0; +https://github.com/happi1204-666/wajue-rss-proxy)"
# 多公共 RSSHub 实例容错：rsshub.app 会封 GitHub 云 IP，故逐个尝试镜像，谁通用谁
INSTANCES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://hub.slarker.me",
    "https://rsshub.pseudoyu.com",
    "https://rsshub.woodland.cafe",
]


def repo_root():
    # 本文件位于 <repo>/deploy/gh_rss_proxy/fetch_rsshub.py
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def load_routes():
    rp = os.path.join(repo_root(), "deploy", "rsshub_routes.json")
    with open(rp, encoding="utf-8") as f:
        return json.load(f)["routes"]


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            # 关键：禁用压缩，避免某些 RSSHub 实例返回 gzip 乱码(早期 MEE 踩过的坑)
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
        ct = r.headers.get("Content-Type", "")
        return data, ct


def looks_like_feed(data):
    head = data[:2000].lstrip()
    return (
        head[:5].lower().startswith(b"<?xml")
        or b"<rss" in head[:800]
        or b"<feed" in head[:800]
    )


def main():
    routes = load_routes()
    out_dir = os.path.join(repo_root(), "docs", "rsshub")
    os.makedirs(out_dir, exist_ok=True)
    status = {}
    for rid, meta in routes.items():
        route = meta["route"]
        ok = False
        err = None
        src = None
        tried = []
        for base in INSTANCES:
            url = base + route
            try:
                data, ct = fetch(url)
                tried.append([url, "len=%d ct=%s" % (len(data), ct)])
                if looks_like_feed(data):
                    xml = data.decode("utf-8", "replace")
                    with open(os.path.join(out_dir, rid + ".xml"), "w", encoding="utf-8") as f:
                        f.write(xml)
                    ok = True
                    src = url
                    break
                else:
                    err = "non-feed ct=%s len=%d" % (ct, len(data))
                    tried.append([url, "NON_FEED:%s" % ct])
            except Exception as e:  # noqa: BLE001
                err = "%s: %s" % (type(e).__name__, e)
                tried.append([url, err])
        status[rid] = {
            "ok": ok,
            "name": meta["name"],
            "route": route,
            "conf": meta.get("conf", "?"),
            "src": src,
            "error": None if ok else err,
            "tried": tried,
        }
        print(("OK   " if ok else "FAIL ") + rid + " | " + meta["name"] + " | " + (src or err or "")[:90])

    summary = {
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": RSSHUB,
        "status": status,
        "ok_count": sum(1 for v in status.values() if v["ok"]),
        "total": len(status),
    }
    with open(os.path.join(out_dir, "_status.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== %d/%d RSSHub routes OK ===" % (summary["ok_count"], summary["total"]))


if __name__ == "__main__":
    main()
