# 内容创作技能

## 适用场景
AI 辅助生成小红书笔记文案和配图方案。

## 前置条件
- 明确发布主题/关键词
- knowledge/templates/ 中有匹配的品类模板

## 工作流程

### Step 1: 选定模板和参考
从 knowledge/templates/post_templates/ 中选择匹配品类模板
阅读 knowledge/templates/copywriting_frameworks.md 中的文案框架

### Step 2: AI 生成文案
使用 LLM (Cursor/Codex 自身能力) 基于模板和框架生成文案。
参考知识库中的 prompts 来引导生成。

### Step 3: 格式化输出
```
python scripts/create/generate_post.py --title "..." --content "..." --template food --output data/drafts/2024-01-01-post.md
```

### Step 4: 生成配图方案
```
python scripts/create/generate_image.py --input data/drafts/2024-01-01-post.md --output data/drafts/2024-01-01-images.json
```

### Step 5: 加入内容日历
```
python scripts/create/calendar_add.py --date 2024-01-05 --draft data/drafts/2024-01-01-post.md
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
