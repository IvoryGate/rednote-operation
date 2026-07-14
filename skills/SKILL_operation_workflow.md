# 全流程运营工作流

## 适用场景
从竞品调研 → 内容创作 → 定时发布 → 数据复盘 的完整运营周期。

## 前置条件
- 已完成项目初始化 (`./setup.sh` 或 `uv sync` + `playwright install chromium`)
- 知识库已就绪 (knowledge/)
- 账号已配置 (`config/accounts.yaml`) 且已登录 (`scripts/crawl/login.py login --account main`)

## 完整工作流

### Phase 1: 调研 (周一)
1. 执行 SKILL_competitor_research.md 分析 3-5 个竞品
2. 提取爆文类型和高频标签
3. 确定本周内容方向

### Phase 2: 策划 (周二)
1. 根据调研结果规划 5-7 篇笔记主题
2. 使用 knowledge/strategies/02_posting_schedule.md 制定发布计划
3. 创建内容日历

### Phase 3: 创作 (周三-周四)
1. 执行 SKILL_content_creation.md 批量生成内容
2. AI 生成初稿 → 人工/AI 优化 → 定稿
3. 准备配图素材

### Phase 4: 发布 (周五-周日)
1. 执行 SKILL_publishing.md 定时发布
2. 监控发布状态，处理异常

### Phase 5: 复盘 (下周一)
1. 执行 SKILL_data_analysis.md 分析上周数据
2. 记录运营日志到 knowledge/learnings/
3. 调整下周策略

## 生产规范
| 环节 | 频率 | 工具/脚本 |
|------|------|-----------|
| 竞品监测 | 每周1次 | monitor_account.py |
| 关键词追踪 | 每周1次 | keyword_insights.py |
| 内容创作 | 每周2-3次 | generate_post.py |
| 内容发布 | 每日1-2次 | publish_now.py / schedule_post.py |
| 数据复盘 | 每周1次 | content_performance.py |
| 经验记录 | 每次复盘后 | 写入 knowledge/learnings/ |
