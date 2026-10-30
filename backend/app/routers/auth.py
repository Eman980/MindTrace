from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User
from app.schemas.all_schemas import UserCreate, UserLogin, UserOut, Token
from app.utils.security import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=Token)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )
    user = User(
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role="student"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account exists with this email address. Please sign up to create an account."
        )
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again."
        )
        
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
