import sys
import os

# Adiciona o diretório pai (a raiz do projeto) ao caminho de busca do Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))