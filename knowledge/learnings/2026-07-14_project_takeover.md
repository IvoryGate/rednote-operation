# 2026-07-14 — 项目接管审计与修复启动

## 背景
Cloud agent「项目接管」接手 rednote-operation。仓库骨架完整（14 个历史 PR 已合入 main），端到端尚不可靠。

## 现状判定
| 模块 | 状态 |
|------|------|
| src/core + scripts + FastAPI + Vue BI | 可运行脚手架 |
| knowledge/ | 较完整 |
| skills/ | 命令示例曾过时（已出 PR #16） |
| DB schema.sql vs ORM | 曾严重不一致（已出 PR #15） |
| 爬虫解析 / 发布自动化 | 脆弱，依赖 DOM |

## 已开 PR
1. #15 `fix(db): align schema with ORM and harden bootstrap`
2. #16 `docs(skills): sync skill CLI examples with actual scripts`

## 后续优先级
1. 爬虫最小可用：抽取 `note_id`，修复 `monitor_account` KeyError，`--headless` 生效
2. 配置：`accounts.yaml` 加载器；默认账号名与模板对齐
3. `session.check_login_status` 真实实现
4. 打包/`PYTHONPATH`：让 `uv run python scripts/...` 无需手动设路径
5. skills 命令回归测试（`--help` / 文档一致性）

## 经验
接管时先以 DB 契约与文档可用性打底，再扩爬虫/发布能力，避免在错误 schema 上堆功能。
