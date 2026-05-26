# 📚 API de Livros com Cache em Redis (Exercício EBAC)

Esta é uma API RESTful construída com **FastAPI** e **SQLAlchemy** (banco de dados SQLite), com foco em otimização de desempenho utilizando **Redis** como camada de cache.

O projeto aplica o conceito de **Cache Invalidation** (Invalidação de Cache): a lista de livros é armazenada em cache (com TTL de 60 segundos) durante a leitura (`GET`), mas o cache é automaticamente limpo sempre que há uma operação de escrita (`POST`, `PUT`, `DELETE`), garantindo consistência de dados.

---

## 🚀 1. Configuração do Ambiente e Redis

### Pré-requisitos
* Python 3.9+
* Ambiente virtual (venv) ativo
* Docker ou Podman para rodar o servidor Redis

### Subindo o servidor Redis
Antes de iniciar a API, você precisa ter um servidor Redis rodando localmente na porta `6379`. Execute o comando abaixo no seu terminal:

```bash
# Usando Docker ou Podman
podman run --name meu-redis -p 6379:6379 -d redis
```

### Instalando as dependências
Com o seu ambiente virtual ativado, instale os pacotes necessários:
```bash
pip install fastapi uvicorn pydantic sqlalchemy redis
```

---

## ⚙️ 2. Executando a API

Inicie o servidor de desenvolvimento do Uvicorn com o comando:
```bash
uvicorn main:app --reload
```
A API estará acessível em: `http://127.0.0.1:8000`
A documentação interativa (Swagger UI) estará em: `http://127.0.0.1:8000/docs`

> **Aviso de Autenticação:** A API utiliza segurança **HTTP Basic**. 
> Usuário: `admin` | Senha: `1234`

---

## 🧪 3. Como Testar a Implementação (Exemplos cURL)

Abra um novo terminal para executar os testes abaixo e observe o comportamento do Cache.

### A. Adicionar um Livro (POST)
*Irá salvar no SQLite e invalidar/limpar o cache do Redis para manter a consistência.*
```bash
curl -X 'POST' \
  '[http://127.0.0.1:8000/adiciona](http://127.0.0.1:8000/adiciona)' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46MTIzNA==' \
  -H 'Content-Type: application/json' \
  -d '{
  "nome_livro": "O Problema dos Três Corpos",
  "autor_livro": "Cixin Liu",
  "ano_livro": 2008
}'
```

### B. Listar Livros e Testar o Cache (GET)
*Execute este comando duas vezes. Na primeira vez, a API buscará no SQLite e salvará no Redis. Na segunda vez, a resposta será instantânea a partir do cache.*
```bash
curl -X 'GET' \
  '[http://127.0.0.1:8000/livros?page=1&limit=10](http://127.0.0.1:8000/livros?page=1&limit=10)' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46MTIzNA=='
```

### C. Verificar o conteúdo do Redis diretamente (GET)
*Este é um endpoint de depuração criado para visualizar exatamente quais chaves estão no cache no momento.*
```bash
curl -X 'GET' \
  '[http://127.0.0.1:8000/debug/redis](http://127.0.0.1:8000/debug/redis)' \
  -H 'accept: application/json'
```

### D. Atualizar um Livro (PUT)
*Atualiza o banco de dados e invalida o cache antigo.*
```bash
curl -X 'PUT' \
  '[http://127.0.0.1:8000/atualiza/1](http://127.0.0.1:8000/atualiza/1)' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46MTIzNA==' \
  -H 'Content-Type: application/json' \
  -d '{
  "nome_livro": "O Problema dos Três Corpos - Edição Especial",
  "autor_livro": "Cixin Liu",
  "ano_livro": 2010
}'
```

### E. Deletar um Livro (DELETE)
*Remove o livro do banco e apaga o cache do Redis.*
```bash
curl -X 'DELETE' \
  '[http://127.0.0.1:8000/deletar/1](http://127.0.0.1:8000/deletar/1)' \
  -H 'accept: application/json' \
  -H 'Authorization: Basic YWRtaW46MTIzNA=='
```