"""Authentication and authorization service."""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from models.user import User


SECRET_KEY = "super-secret-key-123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password_hash(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    salt, hash_value = hashed_password.split(":")
    check_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return check_hash == hash_value


def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate a user with email and password."""
    from services.database import get_session, create_database_engine

    engine = create_database_engine()
    session = get_session(engine)

    # Find user by email
    user = session.query(User).filter(User.email == email).first()
    if user is None:
        return None

    if not user.verify_password(password):
        return None

    return user


def create_access_token(user: User) -> str:
    """Create a JWT access token for a user."""
    import jwt

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str) -> User | None:
    """Get the current user from an access token."""
    import jwt

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return _load_user_by_id(user_id)
    except jwt.PyJWTError:
        return None


def _load_user_by_id(user_id: str) -> User | None:
    """Load a user by ID from the database."""
    from services.database import get_session, create_database_engine

    engine = create_database_engine()
    session = get_session(engine)
    return session.query(User).filter(User.id == user_id).first()


def login(email: str, password: str) -> dict | None:
    """Login a user and return an access token."""
    user = authenticate_user(email, password)
    if user is None:
        return None

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
        },
    }
