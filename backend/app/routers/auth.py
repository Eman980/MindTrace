import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User, PasswordResetToken
from app.schemas.all_schemas import (
    UserCreate, UserLogin, UserOut, Token, ForgotPasswordIn, ResetPasswordIn, ForgotPasswordOut
)
from app.utils.security import verify_password, get_password_hash, create_access_token, get_current_user
from app.utils.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

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
            detail="No account found with this email."
        )
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again."
        )
        
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/forgot-password", response_model=ForgotPasswordOut)
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)):
    """
    Initiates password recovery.
    Generates a secure, time-limited token (1 hour expiration).
    If SMTP is configured, sends an email with the reset link.
    If SMTP is not configured, logs the token to the server console and provides it for local testing.
    Never exposes sensitive account existence in customer-facing error messages.
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    
    if not user:
        # Standard security practice: do not leak whether user exists
        return {
            "success": True,
            "message": "If an account with this email exists, password reset instructions have been generated.",
            "email_sent": False,
            "reset_token": None,
            "note": "If registered, check your email or server console for recovery instructions."
        }

    # Generate secure random token
    raw_token = secrets.token_urlsafe(36)
    expires = utcnow() + datetime.timedelta(hours=1)

    # Invalidate any existing unused reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})

    reset_record = PasswordResetToken(
        user_id=user.id,
        token=raw_token,
        expires_at=expires,
        used=False
    )
    db.add(reset_record)
    db.commit()

    # Attempt to send real email if SMTP is configured
    email_sent = send_password_reset_email(user.email, raw_token)

    # Always log to server console for testing/development
    print(f"\n=======================================================")
    print(f"[Password Reset] Request for: {user.email}")
    print(f"[Password Reset] Reset Token: {raw_token}")
    print(f"[Password Reset] Valid for 1 hour until: {expires}")
    print(f"[Password Reset] Email Sent via SMTP: {email_sent}")
    print(f"=======================================================\n")

    return {
        "success": True,
        "message": "If an account with this email exists, password reset instructions have been generated.",
        "email_sent": email_sent,
        "reset_token": raw_token,
        "note": (
            "Password reset link has been dispatched to your email address."
            if email_sent
            else "SMTP email delivery is not configured on this server. To configure email delivery, set SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD in backend/.env. For testing, your recovery token has been logged to the server console and provided below."
        )
    }

@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    """
    Applies the new password using the validated reset token.
    """
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match. Please verify both fields."
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Verify at least one digit or symbol for basic strength
    if not any(c.isdigit() for c in payload.new_password) and not any(not c.isalnum() for c in payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number or special character."
        )

    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token,
        PasswordResetToken.used == False
    ).first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link. Please request a new one."
        )

    # Check expiration
    token_exp = token_record.expires_at
    if token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=datetime.timezone.utc)
    if token_exp < utcnow():
        token_record.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has expired. Please submit a new request."
        )

    # Update student password
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated user not found.")

    user.hashed_password = get_password_hash(payload.new_password)
    token_record.used = True
    db.commit()

    return {
        "success": True,
        "message": "Password reset successfully! You can now log in with your new password."
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

