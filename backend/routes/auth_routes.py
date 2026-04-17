"""
Rotas de Autenticação JWT - EditMind
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import uuid
import re

# JWT
from jose import JWTError, jwt
from passlib.context import CryptContext

# Database
from database import get_db_session, Usuario
from sqlalchemy.orm import Session

router = APIRouter()

# ==========================================
# CONFIGURAÇÃO JWT
# ==========================================
SECRET_KEY = "editmind_secret_key_2026_change_in_production"  # MUDAR EM PRODUÇÃO!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ==========================================
# SCHEMAS
# ==========================================
class UsuarioCadastro(BaseModel):
    nome: str
    email: EmailStr
    senha: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class UsuarioResponse(BaseModel):
    id: str
    nome: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

# ==========================================
# UTILS
# ==========================================

def _hash_senha(senha: str) -> str:
    # Passlib/bcrypt espera str — encoding interno é feito pelo passlib
    # Truncamos em 72 chars (limite UTF-8 do bcrypt) antes de passar
    return pwd_context.hash(senha[:72])

def _verificar_senha(senha: str, hash: str) -> bool:
    # Mesma truncagem aplicada na verificação para consistência
    return pwd_context.verify(senha[:72], hash)

def _criar_token(user_id: str, email: str) -> str:
    """Gera JWT token."""
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _decode_token(token: str) -> Optional[dict]:
    """Decodifica e valida JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Usuario:
    """Dependência para proteger rotas."""
    token = credentials.credentials
    payload = _decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    with get_db_session() as db:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )
        return user

# ==========================================
# ROTAS PÚBLICAS
# ==========================================

@router.post("/api/auth/cadastrar", response_model=TokenResponse)
async def cadastrar(dados: UsuarioCadastro):
    """
    Cadastra novo usuário e retorna token JWT.
    """
    # Validações
    if len(dados.senha) < 6:
        raise HTTPException(
            status_code=400,
            detail="Senha deve ter no mínimo 6 caracteres"
        )
    
    if len(dados.nome) < 2:
        raise HTTPException(
            status_code=400,
            detail="Nome deve ter no mínimo 2 caracteres"
        )
    
    with get_db_session() as db:
        # Verifica email único
        existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
        if existente:
            raise HTTPException(
                status_code=400,
                detail="Email já cadastrado"
            )
        
        # Cria usuário
        user_id = str(uuid.uuid4())
        novo_usuario = Usuario(
            id=user_id,
            nome=dados.nome,
            email=dados.email,
            senha_hash=_hash_senha(dados.senha)
        )
        db.add(novo_usuario)
    
    # Gera token
    access_token = _criar_token(user_id, dados.email)
    
    return TokenResponse(
        access_token=access_token,
        usuario=UsuarioResponse(
            id=user_id,
            nome=dados.nome,
            email=dados.email
        )
    )

@router.post("/api/auth/login", response_model=TokenResponse)
async def login(dados: UsuarioLogin):
    """
    Autentica usuário e retorna token JWT.
    """
    with get_db_session() as db:
        usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
        
        if not usuario or not _verificar_senha(dados.senha, usuario.senha_hash):
            raise HTTPException(
                status_code=401,
                detail="Email ou senha incorretos"
            )
        
        # Gera token
        access_token = _criar_token(usuario.id, usuario.email)
        
        return TokenResponse(
            access_token=access_token,
            usuario=UsuarioResponse(
                id=usuario.id,
                nome=usuario.nome,
                email=usuario.email
            )
        )

# ==========================================
# ROTAS PROTEGIDAS
# ==========================================

@router.get("/api/auth/me", response_model=UsuarioResponse)
async def me(usuario: Usuario = Depends(get_current_user)):
    """
    Retorna dados do usuário logado.
    Requer token JWT válido.
    """
    return UsuarioResponse(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email
    )

@router.post("/api/auth/logout")
async def logout():
    """
    Logout - apenas informativo (token deve ser removido no cliente).
    """
    return {"mensagem": "Logout realizado com sucesso"}

@router.get("/api/auth/setup-dev")
async def setup_dev():
    """
    Cria usuário de desenvolvimento para testes.
    SÓ USE EM DESENVOLVIMENTO!
    """
    with get_db_session() as db:
        # Verifica se já existe
        existente = db.query(Usuario).filter(Usuario.email == "dev@test.com").first()
        if existente:
            # Retorna token do existente
            token = _criar_token(existente.id, existente.email)
            return {
                "sucesso": True,
                "mensagem": "Usuário dev já existe",
                "access_token": token,
                "credenciais": {"email": "dev@test.com", "senha": "123456"}
            }
        
        # Cria novo usuário dev
        user_id = "dev-user-001"
        novo = Usuario(
            id=user_id,
            nome="Dev User",
            email="dev@test.com",
            senha_hash=_hash_senha("123456")
        )
        db.add(novo)
    
    token = _criar_token(user_id, "dev@test.com")
    return {
        "sucesso": True,
        "mensagem": "Usuário dev criado!",
        "access_token": token,
        "credenciais": {"email": "dev@test.com", "senha": "123456"}
    }
