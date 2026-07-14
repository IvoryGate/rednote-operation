# 数据分析技能

## 适用场景
对采集的数据进行分析，生成可操作的运营洞察。

## 前置条件
- 已完成数据采集（通过爬虫脚本）
- 数据已存储在 database/rednote.db 或 data/ 目录

## 工作流程

### Step 1: 数据汇总
```bash
uv run python scripts/analyze/content_performance.py \
  --from-db \
  --days 30 \
  --top 20 \
  --sort-by likes \
  --output data/reports/performance_summary.md
```

也可 `--input data/.../notes.json` 读本地 JSON。

### Step 2: 竞品对比
```bash
uv run python scripts/analyze/competitor_report.py \
  --compare \
  --days 30 \
  --output data/reports/competitor_analysis.md
```

指定竞品：可多次传入 `-c name1 -c name2`。

### Step 3: 关键词洞察
```bash
uv run python scripts/analyze/keyword_insights.py \
  --from-db \
  --top 50 \
  --output data/reports/keyword_trends.md
```

可选 `--update-db` 回写关键词趋势。

### Step 4: 生成可视化报告
使用 LLM 生成 Markdown 报告，包含数据解读和策略建议。
前端 BI 看板可通过 `uv run python main.py` 查看只读图表。

## 关键指标
- 互动率 = (点赞+收藏+评论) / 曝光量（需有 view_count）
- 收藏率 = 收藏 / 曝光量 ← 最重要的算法信号
- 爆文率 = 点赞>1000 的笔记 / 总笔记数
- CPV (单篇价值) = 综合互动量 / 发布成本

## 参考知识库
- knowledge/prompts/analysis_prompts.md
- knowledge/industry/00_category_overview.md
