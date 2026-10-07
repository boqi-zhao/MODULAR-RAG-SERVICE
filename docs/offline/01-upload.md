# 文档上传

状态：原上传行为已实现、真实 PostgreSQL/磁盘/HTTP 验证并获用户评审；批次模型补齐已实现、验证，待本次代码评审。上传完成后不自动解析。

## 接口与结果

`POST /documents` 接收 multipart 表单，重复使用 `files` 字段上传多份 PDF，结果按请求顺序返回。
每份独立保存文件和数据库记录，某份失败不回滚其他成功项。

| 条件 | 行为 |
| --- | --- |
| 至少一份成功 | HTTP 201，逐份列出成功和失败 |
| 全部失败 | HTTP 400；全部因数据库故障失败时为 503 |
| 未提供 files | HTTP 422 |
| 超出份数或总大小 | HTTP 413，整单拒绝，不写文件/记录 |
| 单份为空、错格式、超限或保存失败 | 该份失败，继续处理其余文件 |

默认限制可由环境变量调整：`UPLOAD_MAX_FILES=10`、`UPLOAD_MAX_BYTES=20971520`（20 MiB）、`UPLOAD_MAX_TOTAL_BYTES=104857600`（100 MiB）。
总大小预检使用调用方提供的大小；单份大小仍在分段写入时核对，不能将未知大小当成已验证。
每份初步检查非空、扩展名 `.pdf`、前 1024 字节中有 `%PDF-`；这些检查不证明正文完整或解析质量。

```json
{
  "succeeded": 1,
  "failed": 1,
  "documents": [
    {"filename": "a.pdf", "status": "uploaded", "document_id": "doc_<UUID>", "source_format": "pdf", "size_bytes": 123, "sha256": "<64位摘要>"},
    {"filename": "b.txt", "status": "failed", "error": "首批只接收 PDF 文件，文件名需以 .pdf 结尾。"}
  ]
}
```

成功项有编号、正数大小和摘要；失败项只有文件名和原因，不返回编号或服务器绝对路径。
每份分配新的 `doc_` 加 UUID 十六进制编号；相同名称或字节仍是两次独立上传，不覆盖、不自动更新旧文档。
这是接入编号，与解析模块的摘要型 ID 不同；正式文档/产物身份衔接待 [03](03-stage-artifacts.md) 评审。

## 保存过程

1. 短事务创建 `uploading` 记录，结束事务后再接收文件。
2. 分段写入本次独有的临时文件，同时累计大小和 SHA-256。
3. 使用硬链接原子创建 `data/uploads/<document_id>/source.pdf`；目标存在则拒绝覆盖。
4. 另一个短事务条件更新 `uploading → uploaded`，补齐大小、摘要和完成时间；提交后才报告成功。

根目录可由 `UPLOAD_ROOT` 设置；数据库存相对存储键，原文件名只用于展示，不参与保存路径拼接。
不同调用各有临时文件，同编号并发只允许一个发布成功；清理只删除本次临时文件。
校验/写入失败尽量更新为 `failed`；文件已发布但 PG 更新失败时保留文件供排查，响应不报告成功。
文件和 PG 不共享事务，进程中断可能留下 `uploading` 或孤立文件；自动对账/恢复尚未实现。
上传状态与解析状态分开；后续解析失败不能把原文件改成“上传失败”，只有 uploaded 记录可交给后续接入层。

## 上传表与约束

`public.document_uploads` 一条记录表示一次上传；PDF 字节不放进数据库，也不重复保存上传 metadata.json。

| 字段 | 规则 |
| --- | --- |
| document_id | text 主键，服务生成编号 |
| filename / source_format | 非空白 text，当前格式为 pdf |
| size_bytes / sha256 | 未知时 NULL；已知时非负大小、64 位小写 SHA-256 |
| storage_type / storage_key | 非空白 text，当前 local；组合唯一 |
| status | uploading / uploaded / failed |
| created_at / completed_at | 数据库时间，timestamptz；结束不得早于开始 |
| error_message | 失败说明；不保存凭据、绝对路径或底层敏感异常 |

uploading：结束时间/错误为空；uploaded：大小 > 0、摘要和结束时间齐全、错误为空；failed：结束时间和非空白错误齐全。
文本空白检查涵盖 Unicode 空白；SHA-256 不唯一，相同内容可独立上传。
状态结束更新同时匹配编号与 `status=uploading`，检查只更新一条；并发成功/失败更新只能有一个完成。
数据库约束只证明记录合法，文件存在性和摘要仍需实际检查。迁移说明见 [06](06-local-runtime.md)。

## 代码与验收

| 文件 | 职责 |
| --- | --- |
| [api/documents.py](../../src/api/documents.py) | HTTP 输入、业务异常映射、Pydantic 响应 |
| [uploads/service.py](../../src/uploads/service.py) | 批次预检、逐份编排、结果统计；可独立调用 |
| [uploads/files.py](../../src/uploads/files.py) | 分段保存、限额、摘要、拒绝覆盖及清理 |
| [uploads/schemas.py](../../src/uploads/schemas.py) | 成功/失败、service 批次和 HTTP 模型；文件流仍用 UploadInput |
| [db/upload_records.py](../../src/db/upload_records.py) / [ORM 模型](../../src/db/models/document_upload.py) | 短事务读写及字段约束 |

已有测试覆盖真实 PG 约束/事务、磁盘字节、同名重复上传、同编号顺序/并发拒绝覆盖、混合失败、限额及 OpenAPI。
service 返回 UploadBatchResult，由 Pydantic 校验结构和计数；failed 从结果数与成功数计算，database_errors 仅用于 HTTP 映射，不进入响应。
最新全套验证见 [TASKS.md](../../TASKS.md)；跳过数据库测试不等于验证通过。
用户认证、自动恢复、存储桶和 10 用户完整流水线验收尚未实现。
