"""头像上传服务：字节校验 + 落盘（uploads/avatars/）。"""

from __future__ import annotations

import re
import secrets

from app.core.config import get_settings

# 仅放行白名单后缀；内容魔数二次校验
ALLOWED_EXTENSIONS = {"png": b"\x89PNG", "jpg": b"\xff\xd8", "jpeg": b"\xff\xd8"}
MAX_SIZE = 2 * 1024 * 1024  # 2MB（前端已裁剪压缩，上限仅作兜底）


def validate_avatar_bytes(filename: str, data: bytes) -> str:
    """校验头像文件，返回扩展名（png/jpg）；非法时抛 ValueError。"""
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 PNG/JPG 格式头像")
    if len(data) > MAX_SIZE:
        raise ValueError("头像文件不能超过 2MB")
    if not data.startswith(ALLOWED_EXTENSIONS[ext]):
        raise ValueError("文件内容与格式不符")
    return ext


def save_avatar(data: bytes, ext: str) -> str:
    """落盘到 uploads/avatars/{随机名}.{ext}，返回 URL 路径（/uploads/avatars/...）。"""
    from pathlib import Path

    settings = get_settings()
    avatars_dir = Path(settings.uploads_dir) / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(12)}.{ext}"
    (avatars_dir / name).write_bytes(data)
    return f"/uploads/avatars/{name}"


def avatar_url_to_abs(url: str) -> str | None:
    """把相对头像 URL 转为绝对 URL（供前端跨域展示）；非本服务路径原样返回。"""
    if not url:
        return None
    if url.startswith("/uploads/"):
        # 域名前缀由调用方按 BASE_URL 拼接
        return url
    return url
