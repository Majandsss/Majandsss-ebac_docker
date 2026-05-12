from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import secrets
import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(
    title="API de Livros",
    description="API para gerenciar catálogo de livros.",
    version="1.0.0",
    contact={
        "name":"Majari",
        "email":"majaandressa@hotmail.com"
    }
)

MEU_USUARIO = os.getenv("MEU_USUARIO")
MINHA_SENHA = os.getenv("MINHA_SENHA")

security = HTTPBasic()

def autenticar_meu_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    is_username_correct = secrets.compare_digest(credentials.username, MEU_USUARIO)
    is_password_correct = secrets.compare_digest(credentials.password, MINHA_SENHA)

    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Basic"}
        )
    return credentials.username

meus_livroz = {}

class LivroDB(Base):
    __tablename__ = "Livros"
    id = Column(Integer, primary_key=True, index=True)
    nome_livro = Column(String, index=True)
    autor_livro = Column(String, index=True)
    ano_livro = Column(Integer)

class Livro(BaseModel):
    nome_livro: str
    autor_livro: str
    ano_livro: int

Base.metadata.create_all(bind=engine)

def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def hello_world():
    return {"Hello": "World!"}

@app.get("/livros")
def get_livros(page: int = 1, limit: int = 10, db: Session = Depends(sessao_db), usuario: str = Depends, credentials: HTTPBasicCredentials = Depends(autenticar_meu_usuario)):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page or limit inválidos!")
    
    livros = db.query(LivroDB).offset((page - 1) * limit).limit(limit).all()

    if not meus_livroz:
        return {"message": "Não existe nenhum livro!", "livros": []}
    
    total_livros = db.query(LivroDB).count()

    return {
        "page": page,
        "limit": limit,
        "usuario_ativo": usuario,
        "total": total_livros,
        "livros":[{"id": livro.id, "nome_livro": livro.nome-livro, "autor_livro": livro.autor_livro, "ano_livro": livro.ano_livro} for livro in livros]
    }
    
@app.post("/adiciona")
def post_livros(id_livro: int, livro: Livro, usuario: str = Depends(autenticar_meu_usuario)):
    if id_livro in meus_livroz:
        raise HTTPException(status_code=400, detail="Esse ID de livro já está cadastrado!")
    else:
        meus_livroz[id_livro] = livro.model_dump()
        return {"message": f"Livro '{livro.nome_livro}' adicionado por {usuario}!"}
    
@app.put("/atualiza/{id_livro}")
def put_livros(id_livro: int, livro: Livro, usuario: str = Depends(autenticar_meu_usuario)):
    if id_livro not in meus_livroz:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado!")
    else:
        meus_livroz[id_livro] = livro.model_dump()
        return {"message": f"Livro atualizado com sucesso por {usuario}!"}

@app.delete("/deletar/{id_livro}")
def delete_livro(id_livro: int, usuario: str = Depends(autenticar_meu_usuario)):
    if id_livro not in meus_livroz:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado!")
    else:
        del meus_livroz[id_livro]
        return {"message": f"Livro deletado com sucesso por {usuario}!"}