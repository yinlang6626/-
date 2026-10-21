from typing import Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db


class CurrentUser:
    """占位当前用户。

    TODO: 待 BE-A 实现 JWT 鉴权与 User 模型后，
    将 get_current_user 替换为从 token 解析真实用户。
    """

    def __init__(self, id: int = 1, username: str = "placeholder") -> None:
        self.id = id
        self.username = username


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    return CurrentUser()