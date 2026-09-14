"""站内通知服务：模板渲染 + 批量写入。

设计原则（见 miniprogram/NOTIFY_DESIGN.md）：
- 文案由服务端渲染，前端只展示成品
- notify() 静默失败：通知异常绝不影响主业务流程
- 配置开关（app_settings）控制：总开关 / 成员变动 / 评价通知
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.services.app_setting_service import get_setting_bool

logger = logging.getLogger(__name__)

# 文案模板：占位符由 _render 填充，缺失占位符时保留原样
TEMPLATES: dict[str, dict[str, str]] = {
    "event_confirmed": {
        "title": "活动已确认",
        "content": "「{event_title}」已确认：{time_text} 在 {location} 集合，请准时参加",
    },
    "event_cancelled": {
        "title": "活动已取消",
        "content": "「{event_title}」已被{actor_name}取消，原因：{reason}",
    },
    "event_completed": {
        "title": "活动已完成",
        "content": "「{event_title}」已完成，感谢参与！去写评价分享你的聚餐体验吧",
    },
    "member_joined": {
        "title": "新成员加入",
        "content": "{actor_name} 加入了你的活动「{event_title}」，当前 {count_text} 人",
    },
    "member_left": {
        "title": "成员退出",
        "content": "{actor_name} 退出了活动「{event_title}」，当前 {count_text} 人",
    },
    "new_review": {
        "title": "新评价",
        "content": "{actor_name} 给「{event_title}」留下了 {score_text} 评价：{snippet}",
    },
    "system": {
        "title": "系统通知",
        "content": "{text}",
    },
}


def _render(template: str, **kwargs) -> str:
    """安全渲染：缺失占位符保留原样（不抛异常）。"""
    try:
        return template.format_map(_DefaultDict(kwargs))
    except Exception:  # noqa: BLE001
        return template


class _DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


async def _notify_enabled(db: AsyncSession) -> bool:
    return await get_setting_bool(db, "notify_enabled")


async def notify(
    db: AsyncSession,
    user_ids: list[int],
    ntype: str,
    *,
    event: dict | None = None,
    actor_id: int | None = None,
    actor_name: str | None = None,
    reason: str | None = None,
    count_text: str | None = None,
    score_text: str | None = None,
    snippet: str | None = None,
    text: str | None = None,
    target_type: str = "event",
    target_id: int | None = None,
) -> None:
    """向一组用户写入同类通知。

    - 排除触发者本人（actor_id）
    - 总开关关闭时静默跳过
    - 任何异常仅记录日志，不向外抛
    """
    if not user_ids:
        return
    try:
        if not await _notify_enabled(db):
            return
        template = TEMPLATES.get(ntype)
        if template is None:
            logger.warning("未知通知类型 %s，已跳过", ntype)
            return

        params = {
            "event_title": (event or {}).get("title", "活动"),
            "time_text": (event or {}).get("time_text", ""),
            "location": (event or {}).get("location", "待定地点"),
            "actor_name": actor_name or "对方",
            "reason": reason or "未说明",
            "count_text": count_text or "",
            "score_text": score_text or "好评",
            "snippet": snippet or "",
            "text": text or "",
        }
        content = _render(template["content"], **params)
        title = template["title"]

        recipients = [u for u in set(user_ids) if u != actor_id]
        if not recipients:
            return
        db.add_all(
            Notification(
                user_id=uid,
                type=ntype,
                title=title,
                content=content,
                target_type=target_type,
                target_id=target_id,
                actor_id=actor_id,
                actor_name=actor_name,
            )
            for uid in recipients
        )
        await db.flush()
    except Exception:  # noqa: BLE001
        logger.exception("通知写入失败（已忽略，不影响主流程）")


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> bool:
    """单条标记已读；非本人通知视为不存在。"""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        return False
    if not notification.is_read:
        notification.is_read = True
        await db.flush()
    return True


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    """全部标记已读，返回受影响条数。"""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .with_for_update()
    )
    notifications = result.scalars().all()
    for notification in notifications:
        notification.is_read = True
    await db.flush()
    return len(notifications)


async def unread_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
    )
    return int(result.scalar_one())
