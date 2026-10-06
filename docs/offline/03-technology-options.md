# 离线技术选型入口

已选 PostgreSQL；其他组件按实际需要评审，尚未安装数据库或实现 worker。

- [目标与边界](design/01-scope.md)：围绕版本产物、独立重跑和多用户需求
- [状态库与并发对比](technology/01-database.md)
- [数据库任务领取与 worker](technology/02-workers.md)
- [Redis 与 Kafka 的启用条件](technology/03-redis-kafka.md)
- [本地文件与对象存储](technology/04-storage.md)
- [工程验证与选型顺序](technology/05-validation.md)

先实现当前 parse 范围，不因列出 Redis/Kafka 候选而引入这些组件。

选择组件时优先考虑实际故障与并发需求、可复现验证，以及本机开发维护成本；不用组件数量证明工程深度。
