import uuid
import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from core.database import SessionLocal, User

SECRET_KEY = "aimind-secret-2026"
ALGORITHM = "HS256"

def register_user(email: str, password: str):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return None, "Email déjà utilisé"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        user = User(id=str(uuid.uuid4()), email=email, password_hash=hashed.decode())
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, "✓ Compte créé"
    finally:
        db.close()

def login_user(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return None, "Email ou mot de passe incorrect"
        token = jwt.encode({"sub": user.id, "exp": datetime.utcnow() + timedelta(days=30)}, SECRET_KEY, algorithm=ALGORITHM)
        return token, "✓ Connecté"
    finally:
        db.close()

def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        db = SessionLocal()
        user = db.query(User).filter(User.id == payload["sub"]).first()
        db.close()
        return user
    except:
        return None
