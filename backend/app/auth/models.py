from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    notion_user_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str | None] = mapped_column(String(100), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    workspace_id: Mapped[str | None] = mapped_column(String(64), default=None)
    workspace_name: Mapped[str | None] = mapped_column(String(100), default=None)
    access_token_enc: Mapped[str] = mapped_column(String)
    notion_parent_page_id: Mapped[str | None] = mapped_column(String(64), default=None)