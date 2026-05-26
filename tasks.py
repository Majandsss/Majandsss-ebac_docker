from celery_app import celery_app
import time

@celery_app.task(name="tasks.somar")
def somar(a, b):
    time.sleep(3)
    return a + b

@celery_app.task(name="tasks.fatorial")
def fatorial(n):
    time.sleep(3)
    if n < 0:
        raise ValueError("Número negativo não permitido")
    
    resultado = 1

    for i in range(2, n + 1):
        resultado *= i

    return resultado



#def minha_tarefa1():
#   return "tarefa 1"
#
#def minha_tarefa2():
#    return "tarefa 2"