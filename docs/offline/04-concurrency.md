# 并发设计入口

目标：至少 10 用户同时操作。用户并发与内部文档处理并发分开；尚未完成实测。

- [用户并发与内部处理额度](concurrency/01-limits.md)
- [批次进度与推送](concurrency/02-progress.md)
- [内部额度与公平调度](concurrency/03-scheduling.md)
- [10 用户验收范围](concurrency/04-acceptance.md)

这些是后续服务与 Runner 的设计材料，不属于当前 parse 模块开发授权。
