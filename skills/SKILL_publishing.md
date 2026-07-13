# 自动发布技能

## 适用场景
将内容草稿自动发布到小红书，管理发布队列。

## 前置条件
- 账号已配置 (config/accounts.yaml)
- Playwright 浏览器引擎已安装 (uv run playwright install chromium)
- 首次使用需手动登录保存 Cookie

## 工作流程

### Step 1: 准备发布队列
```
python scripts/publish/manage_queue.py --add --draft data/drafts/post-1.md --schedule "2024-01-05 10:00"
python scripts/publish/manage_queue.py --list
```

### Step 2: 执行发布
```
python scripts/publish/publish_now.py --account main_account --draft data/drafts/post-1.md
```

### Step 3: 定时发布
```
python scripts/publish/schedule_post.py --queue --daemon
```

### Step 4: 查看发布状态
```
python scripts/publish/manage_queue.py --status
```

## 注意事项
- 发布间隔建议 ≥4小时，避免被判定为营销号
- 同一账号每天发布 ≤5篇
- 图片需符合平台规范 (无二维码/水印/联系方式)

## 参考知识库
- knowledge/platform/01_content_rules.md
- knowledge/platform/03_community_guidelines.md
- knowledge/strategies/02_posting_schedule.md
