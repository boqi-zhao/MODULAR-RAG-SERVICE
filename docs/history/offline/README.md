# 离线历史记录

这里保留已被替代的解析设计、验收用例和未采用的分块建议，供追溯，不是当前开发入口。
当前方案见 [PDF MVP](../../offline/02-pdf-parse.md)，详细选型/撤回过程仍在 [decisions](../../decisions/README.md)。

- [01 解析方案与开发过程](01-pdf-history.md)：原 PyMuPDF 模型、规则、旧项目核对和 A/B/C 验证。
- [02 原解析验收用例](02-pdf-cases.md)：已评审的 R-01～R-18，注明哪些要求不在当前 MVP。
- [03 原分块建议](03-chunk-proposal.md)：尚未批准，不自动启用依赖坐标的策略。
- [04 固定公开样本清单](04-doclaynet-sample-20.json)：原 JSON 字节保留，样本文件仍在本机 data/。

2026-10-07 文档整理前共有 50 份 Markdown、2258 行；原文已完整备份到本机 `data/history/offline-docs-20261007-155755/before.tar.gz`，附 inventory.json 摘要清单。
备份含未提交文档，不随 Git 克隆；这里的摘要和样本清单供跨机器追溯，Git 另保留已提交历史。
本次仅提交重排后的文档，解析代码仍在工作区。调优/产物的有效约束已合并至当前 [产物](../../offline/03-stage-artifacts.md) 与 [执行](../../offline/04-execution.md) 文档，不作为废弃内容归档。
