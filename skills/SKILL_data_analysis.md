# 数据分析技能

## 适用场景
对采集的数据进行分析，生成可操作的运营洞察。

## 前置条件
- 已完成数据采集（通过爬虫脚本）
- 数据已存储在 database/rednote.db 或 data/ 目录

## 工作流程

### Step 1: 数据汇总
```
python scripts/analyze/content_performance.py --from-db --days 30 --output data/reports/performance_summary.json
```

### Step 2: 竞品对比
```
python scripts/analyze/competitor_report.py --compare --accounts account1,account2 --output data/reports/competitor_analysis.md
```

### Step 3: 关键词洞察
```
python scripts/analyze/keyword_insights.py --from-db --top 50 --output data/reports/keyword_trends.json
```

### Step 4: 生成可视化报告
使用 LLM 生成 Markdown 报告，包含数据解读和策略建议。

## 关键指标
- 互动率 = (点赞+收藏+评论) / 曝光量
- 收藏率 = 收藏 / 曝光量 ← 最重要的算法信号
- 爆文率 = 点赞>1000 的笔记 / 总笔记数
- CPV (单篇价值) = 综合互动量 / 发布成本

## 参考知识库
- knowledge/prompts/analysis_prompts.md
- knowledge/industry/00_category_overview.md
