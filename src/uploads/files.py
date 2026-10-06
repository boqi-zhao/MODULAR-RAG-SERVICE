"""本地文件保存：分段写入、校验和、大小限制与临时文件发布。

先写 <根目录>/.tmp/<文档编号>.part，全部读完后发布为
<根目录>/<文档编号>/source.pdf；失败只清理临时文件，正式位置不出现半成品。
"""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

# 分段读取大小；1 MiB 足够减少系统调用，又不会把大文件整体读进内存。
CHUNK_SIZE = 1024 * 1024

# 首批只做初步检查：文件头范围、PDF 标识和默认上限；完整校验留给解析阶段。
HEAD_BYTES = 1024
PDF_MAGIC = b"%PDF-"
DEFAULT_MAX_BYTES = 20 * 1024 * 1024

# 单次请求的份数与总大小默认上限；都可用环境变量覆盖。
DEFAULT_MAX_FILES = 10
DEFAULT_MAX_TOTAL_BYTES = 100 * 1024 * 1024


class UploadFileError(Exception):
    """文件保存可预期失败的基类；路由据此映射成具体 HTTP 状态码。"""


class EmptyFile(UploadFileError):
    """文件没有任何字节。"""


class NotPdf(UploadFileError):
    """前 1024 字节里没有 PDF 文件头。"""


class FileTooLarge(UploadFileError):
    """文件超过配置的大小上限。"""


class TargetExists(UploadFileError):
    """发布目标已存在，为避免覆盖旧文件而拒绝写入。"""


# 上传根目录和大小上限都可用环境变量覆盖；本地开发使用默认值即可。
def upload_root() -> Path:
    """返回上传根目录；不创建目录，保存时才按需创建。"""
    return Path(os.environ.get("UPLOAD_ROOT", "").strip() or "data/uploads")


# 读取正整数配置；未设置用默认值，填非整数或非正数时明确报错。
def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise UploadFileError(f"{name} 必须是整数。") from None
    if value <= 0:
        raise UploadFileError(f"{name} 必须大于 0。")
    return value


def max_upload_bytes() -> int:
    """返回单份文件字节上限；配置非法时给出明确错误而不是猜测默认值。"""
    return _positive_int_env("UPLOAD_MAX_BYTES", DEFAULT_MAX_BYTES)


def max_files() -> int:
    """返回单次请求允许的文件份数上限。"""
    return _positive_int_env("UPLOAD_MAX_FILES", DEFAULT_MAX_FILES)


def max_total_bytes() -> int:
    """返回单次请求允许的文件总大小上限。"""
    return _positive_int_env("UPLOAD_MAX_TOTAL_BYTES", DEFAULT_MAX_TOTAL_BYTES)


def storage_key(document_id: str) -> str:
    """记录里保存的相对路径；换对象存储时只替换存储类型和键前缀。"""
    return f"{document_id}/source.pdf"


def source_path(document_id: str) -> Path:
    """正式文件位置；业务按文档编号访问，不依赖记录里的绝对路径。"""
    return upload_root() / storage_key(document_id)


@dataclass(frozen=True)
class SavedFile:
    """保存结果；大小和 SHA-256 用于补齐上传记录。"""

    size_bytes: int
    sha256: str

    @property
    def storage_type(self) -> str:
        return "local"


def _remove_empty_dir(directory: Path) -> None:
    """失败清理时尝试删除空目录；目录非空或不存在都忽略。"""
    try:
        directory.rmdir()
    except OSError:
        pass


def save_pdf(document_id: str, stream: BinaryIO) -> SavedFile:
    """分段保存 PDF 并返回大小和校验和；失败或目标已存在时不留正式文件。"""
    limit = max_upload_bytes()
    target = source_path(document_id)
    temp_dir = upload_root() / ".tmp"
    digest = hashlib.sha256()
    size = 0
    head_checked = False

    temp_dir.mkdir(parents=True, exist_ok=True)
    # 每次调用用独立临时文件：同编号并发时各自写入，互不干扰。
    fd, temp_name = tempfile.mkstemp(dir=temp_dir, prefix=f"{document_id}.", suffix=".part")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as temp_file:
            while True:
                chunk = stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                # 先用第一段做初步检查，避免明显不合格的文件写满磁盘。
                if not head_checked:
                    if PDF_MAGIC not in chunk[:HEAD_BYTES]:
                        raise NotPdf("前 1024 字节内没有 PDF 文件头")
                    head_checked = True
                size += len(chunk)
                if size > limit:
                    raise FileTooLarge(f"文件超过 {limit} 字节上限")
                digest.update(chunk)
                temp_file.write(chunk)
            if size == 0:
                raise EmptyFile("上传内容为空")

        # 发布：建好文档目录后用硬链接原子创建目标；目标已存在则报错，
        # 不像 rename 那样静默覆盖旧文件。临时目录和正式目录同盘，链接可用。
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(temp_path, target)
        except FileExistsError:
            raise TargetExists("保存位置已存在，拒绝覆盖。") from None
        temp_path.unlink()
    except BaseException:
        # 只清理本次调用自己的临时文件；别人创建的临时文件不受影响。
        temp_path.unlink(missing_ok=True)
        _remove_empty_dir(target.parent)
        _remove_empty_dir(temp_dir)
        raise
    return SavedFile(size_bytes=size, sha256=digest.hexdigest())
