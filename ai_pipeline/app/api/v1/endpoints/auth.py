from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

class LoginRequest(BaseModel):
    officer_id: str
    password: str

class LoginResponse(BaseModel):
    token: str
    officer_id: str
    role: str

router = APIRouter(tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Mock authentication endpoint.
    Accepts any officer ID and password for demonstration purposes.
    In a real system, this would verify securely against a database.
    """
    # Simply check if they provided both
    if not credentials.officer_id or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Officer ID or Password"
        )
        
    return LoginResponse(
        token="mock_jwt_token_for_pramaanx",
        officer_id=credentials.officer_id,
        role="authorized_officer"
    )
