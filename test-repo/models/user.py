"""User model for the application."""
import uuid
from datetime import datetime, timezone


class User:
    """Represents a system user with authentication details."""

    def __init__(self, id: uuid.UUID, email: str, hashed_password: str, is_active: bool = True):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.created_at = datetime.now(timezone.utc)

    @classmethod
    def create(cls, email: str, password: str) -> "User":
        """Create a new user with a hashed password."""
        from auth.service import hash_password
        return cls(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
        )

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        from auth.service import verify_password_hash
        return verify_password_hash(password, self.hashed_password)
