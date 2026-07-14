# 内容创作技能

## 适用场景
AI 辅助生成小红书笔记文案和配图方案。

## 前置条件
- 明确发布主题/关键词
- knowledge/templates/ 中有匹配的品类模板
- 在仓库根目录执行命令（项目依赖通过 `uv sync` 安装）

## 工作流程

### Step 1: 选定模板和参考
从 knowledge/templates/post_templates/ 中选择匹配品类模板
阅读 knowledge/templates/copywriting_frameworks.md 中的文案框架

```bash
uv run python scripts/create/generate_post.py --list-templates
```

### Step 2: 生成创作 brief
脚本输出结构化 JSON brief（标题/正文/标签由 AI agent 基于模板填写，不直接调用 LLM API）：

```bash
uv run python scripts/create/generate_post.py \
  --topic "周末探店推荐" \
  --category food \
  --template "探店打卡" \
  --output data/drafts/2024-01-01-brief.json
```

可选：`--db` 将草稿写入 `content_calendar`。

### Step 3: AI 生成终稿
使用 LLM（Cursor/Codex 自身能力）阅读 brief + knowledge/prompts/copywriting_prompts.md，
填写 brief 中的 `generated.title` / `generated.body` / `generated.tags`，保存为定稿 JSON。

### Step 4: 生成配图方案
```bash
uv run python scripts/create/generate_image.py \
  --brief data/drafts/2024-01-01-brief.json \
  --output data/drafts/2024-01-01-images.json
```

无 brief 时可直接：`--topic "..." --category food`。

### Step 5: 加入发布日程
将定稿加入 `publish_queue`（无独立 `calendar_add.py`）：

```bash
uv run python scripts/publish/schedule_post.py \
  --add \
  --draft data/drafts/2024-01-01-brief.json \
  --time "2024-01-05 10:00" \
  --account main
```

## 质量标准
- 标题 ≤20字, 含关键词
- 正文 200-800字, 段落间有空行
- 图片 3-9张, 首图最重要
- 标签 5-10个, 覆盖大词+精准词+长尾词

## 参考知识库
- knowledge/templates/post_templates/
- knowledge/templates/copywriting_frameworks.md
- knowledge/prompts/copywriting_prompts.md
- knowledge/strategies/01_hashtag_strategy.md
