from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, d: RegisterData, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=d.username).first():
        raise HTTPException(400, "Username already exists")
    hashed = get_password_hash(d.password)
    logger.info(f"Hash gerado para {d.username}: {hashed[:50]}...")
    db.add(User(
        username=d.username,
        email=d.email,
        password_hash=hashed,
        xp=0,
        is_invisible=0,
        role="fundador" if db.query(User).count() == 0 else "membro"
    ))
    db.commit()
    return {"status": "ok"}


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Rota de fallback para compatibilidade (caso algum cliente use /login)

@router.post("/login")
async def login_legacy(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return await login_for_access_token(form_data, db)


@router.post("/auth/forgot-password")
def forgot_password(d: ForgotPasswordData, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=d.email).first()
    if user:
        token = create_reset_token(user.email)
        logger.info(f"RESGATE: https://for-glory.onrender.com/?token={token}")
    return {"status": "ok"}


@router.post("/auth/reset-password")
def reset_password(d: ResetPasswordData, db: Session = Depends(get_db)):
    email = verify_reset_token(d.token)
    if not email:
        raise HTTPException(400, "Token inválido ou expirado")
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    new_hash = get_password_hash(d.new_password)
    logger.info(f"Novo hash gerado para {email}")
    user.password_hash = new_hash
    db.commit()
    return {"status": "ok"}


