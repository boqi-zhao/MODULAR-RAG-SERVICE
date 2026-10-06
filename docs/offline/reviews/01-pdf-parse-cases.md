# PDF parse 首批用例评审入口

状态：01～06 已于 2026-10-06 全部评审通过；独立 PDF 解析模块已按 TDD 实现，56 个测试通过。

- [解析输入输出](pdf-parse/01-contract.md)（已通过）
- [页序与图文坐标](pdf-parse/02-coordinates.md)（已通过）
- [扫描风险判定](pdf-parse/03-scan-policy.md)（已通过）
- [公开 PDF 回归用例](pdf-parse/04-public-cases.md)（已通过）
- [结构与故障控制用例](pdf-parse/05-control-cases.md)（已通过）
- [测试数据与运行要求](pdf-parse/06-test-execution.md)（已通过）

先读输入输出、坐标、扫描风险三份短文，再看公开样本和控制用例。

## 本轮范围

先实现独立解析模块与完整返回结果；随后补齐 parse 版本落盘及重跑，再推进 chunk。
本批公开 PDF 验证格式处理，不要求业务一致；业务 PDF 由用户后续自行补充，本轮不补。
在线检索与 RAG 业务效果不能用本批解析回归代替。
仅评审 parse；FastAPI、数据库、worker 和其他 Stage 不在本组范围。

## 执行顺序

测试数据、失败测试、实现与重构复验已完成，详见 [测试记录](pdf-parse/09-test-results.md)。
输入输出、坐标约定、扫描风险规则、用例 R-01～R-18 与测试运行要求均已通过。
批准样本质量不等于批准用例，也不等于授权全部业务。

调用方式见 [解析使用说明](../05-pdf-parse-usage.md)；版本产物落盘与 Runner 仍待后续设计及用例评审。

[固定样本与校验和](04-doclaynet-sample-20.json) · [前期已确认决定](02-pdf-parse.md)
