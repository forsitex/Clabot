import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

security = HTTPBearer(auto_error=False)
settings = get_settings()

TOKEN_EXPIRE_HOURS = 24


def create_token(username: str) -> str:
    """Creează un JWT token."""
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> Optional[str]:
    """Verifică un JWT token și returnează username-ul."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def authenticate(username: str, password: str) -> Optional[str]:
    """Autentifică un utilizator și returnează token-ul."""
    if username == settings.auth_username and password == settings.auth_password:
        return create_token(username)
    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Dependency pentru a obține utilizatorul curent din token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token lipsă",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = verify_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid sau expirat",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return username
