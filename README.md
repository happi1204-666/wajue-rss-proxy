# wajue-feeds-proxy · GitHub Actions + Pages 方案

用你**现有的 GitHub 账号**，无需注册任何新服务、无需自有 VPS，解锁被 GFW 拦截的 11 个国际媒体 RSS。

## 原理
GitHub Actions 的 runner 运行在境外（美国），能 `fetch` 这些被墙媒体。脚本定时抓取 → 生成静态 XML → 推到 `gh-pages` 分支 → 用 GitHub Pages（`*.github.io`，通常不被墙）托管。wajue 直接读 Pages URL 即可。

## 前置条件
- 一个 GitHub 账号 + 把本仓库 push 到 GitHub（公开或私有均可）
- 仓库开启 Actions（默认开）+ Pages 选 `gh-pages` 分支

## 部署步骤
1. 把本仓库推到 GitHub（若尚未）：
   ```bash
   git remote add origin git@github.com:<你的用户名>/<仓库名>.git
   git push -u origin main
   ```
2. 仓库 **Settings → Pages → Build and deployment → Source 选 `Deploy from a branch`**，
   Branch 选 **`gh-pages`** / `(root)`，Save。
   （首次推送 gh-pages 后此分支才出现，先跑一次 workflow 即可。）
3. 手动触发一次：Actions 页 → wajue-feeds-proxy → Run workflow。
   或等 cron 自动跑（每 30 分）。
4. 部署成功后访问：
   `https://<你的用户名>.github.io/<仓库名>/feeds/gl.dw.xml`
   应能看到 DW 的 RSS 内容。

## 验证与排错
- 状态页：`https://<用户名>.github.io/<仓库名>/` 列出每源 OK/FAIL 与出错原因。
- 若某源 FAIL：编辑 `deploy/feeds_proxy_shared.json` 里该源 `url`/`fallback`，
  提交后等下次 cron 或手动 Run。
- 若整个 `*.github.io` 在你的网络不稳定：可考虑 Cloudflare Worker 方案（见同级 cf_rss_proxy/README.md）。

## 接入 wajue
把 `config/sources/_candidate_intl_proxy_gh.yaml` 里的
`<GH_USER>` 和 `<GH_REPO>` 换成真实值，然后：
- 逐项 `enabled: true`（或整文件 `defaults.enabled: true`）
- 跑 `wajue.py check` 复验

## 限制（诚实标注）
- **非实时**：默认 30 分钟一抓，突发新闻有延迟（够宏观/地缘研判，不够秒级）。
- **GitHub 频率**：免费版 Actions 有月度额度（私有仓 2000 分钟/月），11 源 × 30 分 ≈ 每月 ~45 分钟，远未触顶；公开仓无限。
- **体积**：单源 RSS 通常 < 200KB，11 源合计 < 2MB/次，gh-pages 无压力。
- runner IP 可能被个别源的反爬（如 Cloudflare 挑战）挡——脚本已做 fallback + 容错，
  挡了的源会在状态页标 FAIL，不影响其他源。
