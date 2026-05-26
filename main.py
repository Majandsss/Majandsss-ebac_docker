import asyncio
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import secrets
import os
import redis
import json
from fastapi import BackgroundTasks
from tasks import fatorial, somar
from celery_app import celery_app
from celery.result import AsyncResult

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./livros.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Conexão com o Redis (reutilizável para toda a aplicação)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

app = FastAPI(
    title="API de Livros",
    description="API para gerenciar catálogo de livros.",
    version="1.0.0",
    contact={
        "name":"Majari",
        "email":"majaandressa@hotmail.com"
    }
)

MEU_USUARIO = os.getenv("MEU_USUARIO", "admin")
MINHA_SENHA = os.getenv("MINHA_SENHA", "1234")
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

# --- MÉTODOS REDIS ---
async def salvar_livros_redis(chave_cache: str, dados: dict):
    """
    Método assíncrono para salvar a lista de livros no Redis.
    Utiliza um TTL (Time To Live) de 60 segundos.
    """
    # setex = set com expiration (expiração)
    redis_client.setex(chave_cache, 60, json.dumps(dados))

async def deletar_livro_redis():
    """
    Método assíncrono para remover as chaves correspondentes aos livros.
    Limpa todos os caches de paginação para garantir a consistência.
    """
    # Encontra todas as chaves que começam com 'livros:' e as deleta
    chaves = redis_client.keys("livros:*")
    if chaves:
        redis_client.delete(*chaves)

# --- ENDPOINTS ---

@app.get("/")
def hello_world():
    return {"Hello": "World!"}

@app.post("/calcular/soma")
def calcular_soma(a: int, b: int):
    print("🚨 [1] ROTA INICIADA!")
    tarefa = somar.delay(a, b)

    print(f"🚨 [2] TAREFA CRIADA COM ID: {tarefa.id}")

    redis_client.lpush("tarefas_ids", tarefa.id)
    redis_client.ltrim("tarefas_ids", 0, 49)

    print("🚨 [3] SALVO NO REDIS COM SUCESSO!")

    return {
        "task_id": tarefa.id,
        "message":"Tarefa de soma enviada para execução!"
    }

@app.post("/calcular/fatorial")
def calcular_fatorial(n: int):
    print(f"🚨 [FATORIAL] Rota iniciada para o número {n}!")
    tarefa = fatorial.delay(n)
    
    # MUITA ATENÇÃO AO UNDERLINE AQUI:
    redis_client.lpush("tarefas_ids", tarefa.id)
    redis_client.ltrim("tarefas_ids", 0, 49)
    
    print(f"🚨 [FATORIAL] ID salvo no Redis: {tarefa.id}")
    
    return {
        "task_id": tarefa.id,
        "message": "Tarefa de fatorial enviada!"
    }

@app.get("/tarefas/recentes")
def listar_tarefas_recentes():
    ids = redis_client.lrange("tarefas_ids", 0, -1)

    print(f"IDS encontrados no Redis: {ids}")
    
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
    cache_key = f"livros:page={page}&limit={limit}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)
    
    # 2. SE NÃO ESTIVER, BUSCA NO BANCO DE DADOS
    livros = db.query(LivroDB).offset((page - 1) * limit).limit(limit).all()

    if not livros:
        return {"message": "Não existe livro nenhum!"}
    
    total_livros = db.query(LivroDB).count()

    resposta = {
        "page": page,
        "limit": limit,
        "total": total_livros,
        "fonte": "Banco de Dados SQLite", # Para você debugar e ter certeza que veio do banco
        "livros": [
            {
                "id": livro.id,
                "nome_livro": livro.nome_livro,
                "autor_livro": livro.autor_livro,
                "ano_livro": livro.ano_livro
            } for livro in livros
        ]
    }

    # 3. SALVA O RESULTADO NO REDIS
    await salvar_livros_redis(cache_key, resposta)

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

# Invalida o cache porque um novo livro foi inserido (consistência)
    await deletar_livro_redis()

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