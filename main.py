from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import asyncio
import secrets
import os
import redis
import json
from fastapi import BackgroundTasks
from tasks import fatorial, somar
from celery_app import celery_app
from celery.result import AsyncResult
from kafka_producer import enviar_evento_kafka

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./livros.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Conexão com o Redis (reutilizável para toda a aplicação)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

app = FastAPI(
    title="API de Livros",
    description="API para gerenciar catálogo de livros.",
    version="1.0.0",
    contact={
        "name":"Majari",
        "email":"majaandressa@hotmail.com"
    }
)

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

MEU_USUARIO = os.getenv("MEU_USUARIO", "")
MINHA_SENHA = os.getenv("MINHA_SENHA", "")

security = HTTPBasic()

meus_livroz = {}

def autenticar_meu_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    is_username_correct = secrets.compare_digest(credentials.username, MEU_USUARIO)
    is_password_correct = secrets.compare_digest(credentials.password, MINHA_SENHA)

    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Usuário não autorizado! Credenciais inválidas!",
            headers={"WWW-Authenticate": "Basic"}
        )
    
    return credentials.username

class LivroDB(Base):
    __tablename__ = "livros"
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

# --- MÉTODOS REDIS ---
def salvar_livro_redis(livro_id: int, livro: Livro):
    redis_client.set(f"livro:{livro_id}", json.dumps(livro.model_dump()))

def deletar_livro_redis(livro_id: int):
    redis_client.delete(f"livro:{livro_id}")

# --- ENDPOINTS ---

@app.get("/")
def hello_world():
    return {"Hello": "World!"}

@app.post("/calcular/soma")
def calcular_soma(a: int, b: int):
    tarefa = somar.delay(a,b)
    redis_client.lpush("tarefas.ids", tarefa.id)
    redis_client.ltrim("tarefas_ids", 0, 49)

    return {
        "task_id": tarefa.id,
        "message":"Tarefa de soma enviada para execução!"
    }

@app.post("/calcular/fatorial")
def calcular_fatorial(n: int):
    tarefa = fatorial.delay(n)
    redis_client.lpush("tarefas.ids", tarefa.id)
    redis_client.ltrim("tarefas_ids", 0, 49)

    return {
        "task_id": tarefa.id,
        "message":"Tarefa de fatorial enviada para execução!"
    }

@app.get("/tarefas/recentes")
def listar_tarefas_recentes():
    ids = redis_client.lrange("tarefas_ids", 0, -1)
    tarefas = []

    for task_id in ids:
        resultado = AsyncResult(task_id, app=celery_app)
        tarefas.append({
            "task_id": task_id,
            "status": resultado.status,
            "resultado": resultado.result if resultado.successful() else None
        })

    return {
        "tarefas": tarefas
    }

@app.get("/debug/redis")
def ver_livros_redis():
    chaves = redis_client.keys("livros:*")
    livros = []

    for chave in chaves:
        valor = redis_client.get(chave)
        ttl = redis_client.ttl(chave)
        livros.append({"chave": chave, "valor": json.loads(valor), "ttl":ttl})

    return livros

@app.get("/livros")
async def get_livros(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(sessao_db),
    credentials: HTTPBasicCredentials = Depends(autenticar_meu_usuario)
):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page or limit inválidos")
    
    # 1. VERIFICA SE ESTÁ NO REDIS PRIMEIRO
    # cache_key = f"livros:page={page}&limit={limit}"
    # cached = redis_client.get(cache_key)

    #if cached:
    #    return json.loads(cached)
    
    # 2. SE NÃO ESTIVER, BUSCA NO BANCO DE DADOS
    livros = db.query(LivroDB).offset((page - 1) * limit).limit(limit).all()

    if not livros:
        return {"message": "Não existe livro nenhum!"}
    
    total_livros = db.query(LivroDB).count()

    resposta = {
        "page": page,
        "limit": limit,
        "total": total_livros,
        "livros": [
            {
                "id": livro.id,
                "nome_livro": livro.nome_livro,
                "autor_livro": livro.autor_livro,
                "ano_livro": livro.ano_livro
            } for livro in livros
        ]
    }

    #redis_client.setex(cache_key, 30, json.dumps(resposta))

    return resposta
    
@app.post("/adiciona")
async def post_livros(livro: Livro, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    db_livro = db.query(LivroDB).filter(
        LivroDB.nome_livro == livro.nome_livro, 
        LivroDB.autor_livro == livro.autor_livro, 
        LivroDB.ano_livro == livro.ano_livro
    ).first()
    
    if db_livro:
        raise HTTPException(status_code=400, detail="Esse livro já existe aqui!")
    
    novo_livro = LivroDB(
        nome_livro=livro.nome_livro,
        autor_livro=livro.autor_livro,
        ano_livro=livro.ano_livro
    )

    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro)

    salvar_livro_redis(novo_livro.id, livro)

    enviar_evento_kafka("livros_eventos", {
        "acao": "criar",
        "livro": livro.model_dump()
    })

    return {"message": f"Livro '{livro.nome_livro}' adicionado com o ID {novo_livro.id} por {usuario}!"}    

@app.put("/atualiza/{id_livro}")
async def put_livros(id_livro: int, livro: Livro, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    db_livro = db.query(LivroDB).filter(LivroDB.id == id_livro).first()   
    if not db_livro:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado!")
    
    db_livro.nome_livro = livro.nome_livro
    db_livro.autor_livro = livro.autor_livro
    db_livro.ano_livro = livro.ano_livro
        
    db.commit()
    db.refresh(db_livro)

    # Invalida o cache porque os dados de um livro mudaram (consistência)
    await deletar_livro_redis()

    return {"message": f"Livro atualizado com sucesso por {usuario}!"}

@app.delete("/deletar/{id_livro}")
async def delete_livro(id_livro: int, db: Session = Depends(sessao_db), usuario: str = Depends(autenticar_meu_usuario)):
    db_livro = db.query(LivroDB).filter(LivroDB.id == id_livro).first()

    if not db_livro:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado!")
    
    db.delete(db_livro)
    db.commit()

    # Invalida o cache porque um livro foi removido (consistência)
    await deletar_livro_redis()

    return {"message": f"Livro deletado com sucesso por {usuario}!"}