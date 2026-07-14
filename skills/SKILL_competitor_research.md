# 竞品调研技能

## 适用场景
分析竞争对手账号的内容策略、表现数据和运营手法。

## 前置条件
- 已登录并保存 session：`uv run python scripts/crawl/login.py login --account main`
- 明确要分析的竞品账号列表（小红书 user_id）

## 工作流程

### Step 1: 登记并采集竞品
新增监测账号：
```bash
uv run python scripts/crawl/monitor_account.py \
  --name <competitor_name> \
  --user-id <xhs_user_id> \
  --category food \
  --account main
```

更新数据（含近期笔记）：
```bash
uv run python scripts/crawl/monitor_account.py \
  --name <competitor_name> \
  --update \
  --days 30 \
  --account main \
  --output data/competitors/<name>/notes.json
```

列出已监测账号：`uv run python scripts/crawl/monitor_account.py --list`

### Step 2: 内容表现分析
```bash
uv run python scripts/analyze/content_performance.py \
  --input data/competitors/<name>/notes.json \
  --output data/competitors/<name>/report.md \
  --top 20 \
  --sort-by likes
```

关注指标: 平均点赞/收藏/评论、Top 笔记互动。

### Step 3: 关键词和标签分析
```bash
uv run python scripts/analyze/keyword_insights.py \
  --input data/competitors/<name>/notes.json \
  --top 50 \
  --output data/competitors/<name>/keywords.md
```

### Step 4: 生成竞品报告
```bash
uv run python scripts/analyze/competitor_report.py \
  --competitor <name> \
  --days 30 \
  --output data/reports/<name>_report.md
```

多账号对比：`--compare`（分析所有 `is_active` 竞品）。

## 输出解读
- 高收藏相对点赞的内容类型 = 用户愿意保存的"干货"
- 高频标签 = 该赛道的流量入口
- 发布时间分布 = 竞品的运营习惯

## 参考知识库
- knowledge/strategies/00_content_strategy.md
- knowledge/strategies/01_hashtag_strategy.md
