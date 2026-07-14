# 自动发布技能

## 适用场景
将内容草稿自动发布到小红书，管理发布队列。

## 前置条件
- 账号已配置 (config/accounts.yaml，可从 accounts.yaml.template 复制)
- Playwright 浏览器引擎已安装 (`uv run playwright install chromium`)
- 首次使用需手动登录保存 Cookie：`uv run python scripts/crawl/login.py login --account main`

## 工作流程

### Step 1: 加入发布队列
```bash
uv run python scripts/publish/schedule_post.py \
  --add \
  --draft data/drafts/post-1.json \
  --time "2024-01-05 10:00" \
  --account main
```

查看队列：
```bash
uv run python scripts/publish/manage_queue.py list
uv run python scripts/publish/manage_queue.py list --status failed
```

### Step 2: 立即发布（默认 dry-run）
默认只填表 + 截图，不点提交。确认无误后加 `--no-dry-run`：

```bash
uv run python scripts/publish/publish_now.py \
  --account main \
  --draft data/drafts/post-1.json \
  --no-headless

# 确认后真实发布
uv run python scripts/publish/publish_now.py \
  --account main \
  --draft data/drafts/post-1.json \
  --no-dry-run
```

也可按队列 ID：`--queue-id 1`。

### Step 3: 定时守护发布
```bash
uv run python scripts/publish/schedule_post.py --daemon --interval 60
```

### Step 4: 失败重试 / 移除
```bash
uv run python scripts/publish/manage_queue.py retry --id 1
uv run python scripts/publish/manage_queue.py remove --id 1
```

## 注意事项
- 发布间隔建议 ≥4小时，避免被判定为营销号
- 同一账号每天发布 ≤5篇
- 图片需符合平台规范 (无二维码/水印/联系方式)
- 默认账号名为 `main`（与 login session 名称一致）

## 参考知识库
- knowledge/platform/01_content_rules.md
- knowledge/platform/03_community_guidelines.md
- knowledge/strategies/02_posting_schedule.md
