# 首次本地跑通（账号 → 登录 → 双探针）

工程能力已齐；本页把**本机第一次可用**压成可复制命令。
目标：完成账号配置、保存登录态、跑通发布选择器 live smoke 与 view_count 探针。

## 0. 环境

```bash
uv sync
uv run playwright install chromium
uv run alembic upgrade head   # 或已有库: uv run alembic stamp head
```

可选体检（不打开浏览器）：

```bash
uv run python scripts/ops/preflight.py
```

有账号文件会检查 session；没有会提示 `cp` 命令。离线冒烟也会跑一遍。

## 1. 配置账号

```bash
cp config/accounts.yaml.template config/accounts.yaml
```

编辑 `config/accounts.yaml`：

- `name`：与后续 `--account` 一致（默认 `main`）
- `phone`：仅备忘，脚本不拿它自动登录
- `cookies_path`：session 目录，默认 `./.browser-data/main`
- `enabled: true`：至少一个启用账号

`config/accounts.yaml` 已在 `.gitignore`，不要提交。

确认：

```bash
uv run python scripts/crawl/login.py list
```

## 2. 手动登录并保存 session

需要图形界面（本机显示器；无头环境无法完成扫码/验证）。

```bash
uv run python scripts/crawl/login.py login --account main
# 浏览器打开创作者登录页 → 手动登录成功 → 回终端按 Enter
```

校验：

```bash
uv run python scripts/crawl/login.py status --account main
```

应看到 `Logged in: 'main'`。过期则：

```bash
uv run python scripts/crawl/login.py login --account main --force
```

## 3. 实机双探针

### 3a. 发布选择器 live smoke

```bash
uv run python scripts/publish/smoke_selectors.py --live --account main --headless
```

失败时看 `data/screenshots/failures/` 证据包，并对照 `config/publish_selectors.yaml`。

### 3b. view_count 命中率

```bash
uv run python scripts/crawl/probe_view_count.py --live -k 美食 -n 20 --account main --headless
```

关注 `view_count` 的 `hit_rate` / `positive_rate`。列表页常不展示浏览数，命中率低不一定是解析崩了——可对照同次输出的 `like_count`。

离线复盘导出 JSON：

```bash
uv run python scripts/crawl/search_trending.py -k 美食 -n 20 -o exports/search.json --account main --headless
uv run python scripts/crawl/probe_view_count.py --input exports/search.json
```

## 4. （可选）工作流 API token

前端或远程触发工作流时：

```bash
# config/config.yaml → security.api_token，或：
export REDNOTE_API_TOKEN=your-secret
```

Workflows 页填同一 token。真发需 `dry_run=false` 且 `confirm_publish: "I_CONFIRM_PUBLISH"`。

## 5. （可选）干跑发布链路

保持 dry-run，确认队列/草稿路径，不要 `--no-dry-run`：

```bash
uv run python scripts/publish/publish_now.py --account main --draft path/to/draft.json --dry-run --headless
# 或通过 API workflows：publish.now，默认 dry_run=true
```

## 判定清单

| 步骤 | 成功信号 |
|------|----------|
| accounts | `login.py list` 能看到启用账号 |
| login | `login.py status` → Logged in |
| publish smoke | `SMOKE OK (live)` |
| view probe | `PROBE OK` + 打印 hit_rate |
| API（可选） | 带 token 的 `POST /api/workflows/.../run` 返回 200 |

全部勾完后，再按 `skills/SKILL_operation_workflow.md` 做周更运营闭环。
