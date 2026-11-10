from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/guest")
def create_guest(db: Session = Depends(get_db)) -> dict:
    """비회원 토큰 발급. 비회원도 users 행을 하나 가진다 (is_guest=True)."""
    user = User(is_guest=True)
    db.add(user)
    db.commit()
    token, expires_in = create_access_token(user.id, "guest")
    return {"access_token": token, "kind": "guest", "expires_in": expires_in}
