"""SQLAlchemy ORM 基类。所有领域模型继承自 Base。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
