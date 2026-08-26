"""Main application entry point."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from auth.service import login, get_current_user
from models.user import User


app = FastAPI(title="Test Application")


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@app.post("/auth/login", response_model=LoginResponse)
async def login_endpoint(request: LoginRequest):
    """Login endpoint for user authentication."""
    result = login(request.email, request.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


@app.get("/auth/me")
async def get_me(token: str):
    """Get current user from token."""
    user = get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"id": str(user.id), "email": user.email}


@app.post("/users/create")
async def create_user(email: str, password: str):
    """Create a new user."""
    user = User.create(email, password)
    return {"id": str(user.id), "email": user.email}
