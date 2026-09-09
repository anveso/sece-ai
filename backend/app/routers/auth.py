"""Registration and login endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import RegisterOut, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Role is deliberately NOT taken from the request payload, even if a
    # client sends one - self-service registration always creates a
    # "student" account. Faculty/admin accounts are promoted manually
    # (e.g. via a one-off SQL UPDATE against the production DB) - see
    # RENDER_DEPLOY.md. This closes off the previous behavior where the
    # frontend's own registration form let anyone pick "Admin" from a
    # dropdown and the backend trusted it outright.
    #
    # is_approved is likewise NOT auto-true: every self-registered account
    # needs an admin to approve it (routers/admin.py) before it can log in
    # - see get_current_user's check in ../auth.py and login() below. This
    # is why registration does NOT return a Token/auto-login the way it used
    # to: an unapproved account has no usable session yet, so there's
    # nothing valid to hand back except a "you're pending" message.
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="student",
        is_approved=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterOut(
        message=(
            "Account created. An administrator needs to approve it before "
            "you can sign in."
        ),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Checked here (clear message right at sign-in) AND in get_current_user
    # (so it's enforced on every subsequent request too, not just at login -
    # see ../auth.py). Admins bypass this - see get_current_user's comment
    # for why that's still safe.
    if not user.is_approved and user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Your account is pending admin approval."
        )

    token = create_access_token(subject=str(user.id))
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
