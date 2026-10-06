# PDF 解析库选择背景

## 已确认的解析方案与定位粒度

已选择 PyMuPDF 统一提取文本与图片；原实现和新增依赖已移除，重写时再安装并锁定版本，见 [实现状态](09-implementation-status.md)。

| 方案 | 可参考的既有经验 | 新项目的额外工作与取舍 |
| --- | --- | --- |
| PyMuPDF 统一提取文本与图片（已选） | 旧项目已用它提取图片 | 同一页内获得文本块/图片区域，减少两套解析结果对齐工作；实际质量需样本验证 |
| MarkItDown 文本转换 + PyMuPDF 图片 | 接近旧项目组合 | 保留转换路径，但需要另做转换文本与原始页/区域的可靠映射，不能靠追加占位符解决 |

PyMuPDF 可返回文本块矩形坐标及图片的多次出现位置，依据 [文本提取](https://pymupdf.readthedocs.io/en/latest/app1.html) 与 [图片定位](https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_image_rects) 官方说明。
选择单一引擎来自本项目的定位和工作量要求，不代表已测出它的文字提取质量更好。

首批保留页码和文本块/图片原始矩形，用于解析排查与核对；逻辑文档版本由后续接入与产物管理绑定。
解析文本内的区间映射另行明确；首批不要求每个字符都具有独立的 PDF 几何坐标。
图片重复出现时保留各自位置；旋转/裁剪页面验证文字、图片与原始位置的提取，展示坐标转换后置。
保留解析引擎输出和处理规则，清理/增强不覆盖原始解析文本；整洁的展示文本可由后续阶段生成。
parse 记录客观图文位置，不直接推断“这张图片属于哪段语义”；图与块的关联规则在 chunk/caption 依赖讨论时确认。

定位验收按 [坐标约定](02-coordinates.md) 执行：指定文字核对页码与大致区域，控制图片四条边各允许最多 1 point 误差。

图片提取可参考字典中的出现记录、透明遮罩，以及跨裁剪边界图片的处理方式；具体写法在对应步骤讲解和确认，依据 [图片块说明](https://pymupdf.readthedocs.io/en/latest/textpage.html#block-dictionaries) 和 [提取范围说明](https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_text)。
具体输入输出与坐标见 [已通过的用例入口](../01-pdf-parse-cases.md)，后续安排见 [解析计划](../../05-pdf-parse-plan.md)。
