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
def get_livros(page: int = 1, limit: int = 10, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page or limit inválidos!")
    
    livros = db.query(LivroDB).offset((page - 1) * limit).limit(limit).all()
    total_livros = db.query(LivroDB).count()

    if total_livros == 0:
        return {"message": "Não existe nenhum livro!", "livros": []}

    return {
        "page": page,
        "limit": limit,
        "usuario_ativo": usuario,
        "total": total_livros,
        "livros":[{"id": livro.id, "nome_livro": livro.nome_livro, "autor_livro": livro.autor_livro, "ano_livro": livro.ano_livro} for livro in livros]
    }
    
@app.post("/adiciona")
def post_livros(livro: Livro, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    novo_livro = LivroDB(
        nome_livro=livro.nome_livro,
        autor_livro=livro.autor_livro,
        ano_livro=livro.ano_livro
    )

    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro)
    
    return {"message": f"Livro '{livro.nome_livro}' adicionado com o ID {novo_livro.id} por {usuario}!"}    
    
@app.put("/atualiza/{id_livro}")
def put_livros(id_livro: int, livro: Livro, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    livro_db = db.query(LivroDB).filter(LivroDB.id == id_livro).first()
    
    if not livro_db:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado!")
    
    livro_db.nome_livro = livro.nome_livro
    livro_db.autor_livro = livro.autor_livro
    livro_db.ano_livro = livro.ano_livro
        
    db.commit()

    return {"message": f"Livro atualizado com sucesso por {usuario}!"}

@app.delete("/deletar/{id_livro}")
def delete_livro(id_livro: int, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    livro_db = db.query(LivroDB).filter(LivroDB.id == id_livro).first()

    if not livro_db:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado!")
    
    db.delete(livro_db)
    db.commit()

    return {"message": f"Livro deletado com sucesso por {usuario}!"}