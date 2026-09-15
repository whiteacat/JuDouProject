"""用户反馈路由：提交问题/建议。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])

FEEDBACK_KINDS = ("bug", "suggestion", "other")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    body: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """提交反馈（需登录；内容 1-500 字，类型白名单）。"""
    if body.kind not in FEEDBACK_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="反馈类型不合法"
        )
    db.add(
        Feedback(
            user_id=current_user.id,
            content=body.content.strip(),
            contact=(body.contact or "").strip() or None,
            kind=body.kind,
        )
    )
    await db.commit()
