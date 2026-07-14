# 2026-07-14 — 接管计划执行进度

## 已合入 main
| PR | 内容 |
|----|------|
| #15 | DB 契约对齐 / config.yaml 加载 / 静态挂载顺序 / 测试 |
| #16 | Skills CLI 文档同步 |
| #17 | 接管审计记录 |
| #18 | 爬虫 note_id、headless、频率限制、退避、UA 池 |
| #19 | accounts.yaml 加载器 + 真实登录态检测 |
| #20 | hatchling 打包，scripts 无需 PYTHONPATH |
| #21 | 发布选择器 registry + 多策略解析 + 失败证据包 |

## 反爬策略（已落地，无 IP 池）
- `config.crawl`：min/max interval、backoff_factor、jitter
- 导航前 `RateLimiter.wait()`；拒识页面 `on_reject()` 指数退避；成功 `on_success()` 回落
- `HeaderPool` 轮换 UA + Accept-Language（无代理/IP 池）

## 发布抗改版（已落地）
- `config/publish_selectors.yaml` 外置策略
- 失败写入 `data/screenshots/failures/<control>_<ts>/`

## 仍待（P2）
- 分析指标深化、创作闭环自动化、API 触发工作流、Alembic 迁移
