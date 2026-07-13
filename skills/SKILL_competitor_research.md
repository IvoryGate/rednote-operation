# 竞品调研技能

## 适用场景
分析竞争对手账号的内容策略、表现数据和运营手法。

## 前置条件
- 已配置小红书账号 Cookie (config/accounts.yaml)
- 明确要分析的竞品账号列表

## 工作流程

### Step 1: 采集竞品笔记数据
```
python scripts/crawl/monitor_account.py --account <competitor_name> --days 30
```
输出: `data/competitors/<name>/notes.json`

### Step 2: 内容表现分析
```
python scripts/analyze/content_performance.py --input data/competitors/<name>/notes.json --output data/competitors/<name>/report.json
```
关注指标: 点赞中位数, 收藏率(收藏/曝光), 评论互动率

### Step 3: 关键词和标签分析
```
python scripts/analyze/keyword_insights.py --input data/competitors/<name>/notes.json
```
提取高频标签, 内容主题聚类

### Step 4: 生成竞品报告
```
python scripts/analyze/competitor_report.py --competitor <name> --output data/reports/<name>_report.md
```

## 输出解读
- 高收藏率(>5%)的内容类型 = 用户愿意保存的"干货"
- 高频标签 = 该赛道的流量入口
- 发布时间分布 = 竞品的运营习惯

## 参考知识库
- knowledge/strategies/00_content_strategy.md
- knowledge/strategies/01_hashtag_strategy.md
