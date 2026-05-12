# Exercício EBAC - Deployment com FastAPI e Podman/Docker

Este repositório contém o deployment de uma aplicação Python utilizando o framework FastAPI. O projeto utiliza Docker e Docker Compose para criar um ambiente de desenvolvimento consistente e replicável, com o gerenciamento de dependências feito através do Poetry.

## 🛠️ Tecnologias Utilizadas

*   **Python 3.12+**
*   **FastAPI** (Framework web)
*   **Poetry** (Gestão de dependências e ambientes virtuais)
*   **Docker** (Containerização)
*   **Docker Compose** (Orquestração de containers)

## 📁 Estrutura do Projeto

*   `Dockerfile`: Instruções para construção da imagem (Instalação do Poetry e dependências).
*   `docker-compose.yml`: Configuração do serviço, mapeamento de portas, volumes e variáveis de ambiente.
*   `main.py`: Código-fonte da aplicação FastAPI.
*   `pyproject.toml` / `poetry.lock`: Arquivos de configuração do Poetry.
*   `.env`: Arquivo de variáveis de ambiente (exemplo)

# 🚀 Instruções Passo a Passo
Siga os comandos abaixo para obter o código e rodar a aplicação no seu ambiente.

1. Clonar o repositório
Abra o seu terminal e clone este repositório:

git clone <https://github.com/Majandsss/Majandsss-ebac_docker.git>

cd <LIVROS.EBAC>

2. Construir e executar a aplicação
Para criar a imagem da aplicação (instalando o Poetry e as dependências) e iniciar os contêineres em segundo plano, execute o comando abaixo na raiz do projeto:

docker-compose up --build -d

Nota: Com os volumes configurados, qualquer alteração feita no código-fonte local será sincronizada automaticamente com o contêiner (hot-reload).
A aplicação poderá ser acessada no navegador através de http://localhost:8000 e a documentação interativa (Swagger) em http://localhost:8000/docs.

3. Parar a aplicação
Para parar a execução e desligar os contêineres corretamente, utilize o seguinte comando:

docker-compose down

## 🛠️ Como Executar o Projeto

Siga os passos abaixo para clonar e rodar a aplicação em sua máquina.

### 1. Clonar o Repositório
```bash
git clone [https://github.com/Majandsss/Majandsss-ebac_docker.git](https://github.com/Majandsss/Majandsss-ebac_docker.git)
cd Majandsss-ebac_docker.git