import asyncio
import functools
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List

from colorama import Fore, Style, init as colorama_init

from app.config import settings
from app.core.logging import get_logger, setup_logging

# Inicializar logging
setup_logging()
logger = get_logger("worker")

# Inicializar colorama
colorama_init(autoreset=True)

# Cola de tareas en memoria (en una aplicación real usaríamos Redis, RabbitMQ, etc.)
task_queue = asyncio.Queue()

# Registro de tareas disponibles
registered_tasks: Dict[str, Callable] = {}


def register_task(task_name: str):
    """
    Decorador para registrar una tarea.
    
    Args:
        task_name: Nombre de la tarea a registrar
    """
    def decorator(func: Callable):
        registered_tasks[task_name] = func
        logger.info(f"Tarea registrada: {task_name}")
        return func
    return decorator


async def execute_task(task_name: str, *args, **kwargs) -> Any:
    """
    Ejecuta una tarea de forma síncrona o asíncrona según su tipo.
    
    Args:
        task_name: Nombre de la tarea a ejecutar
        *args: Argumentos posicionales para la tarea
        **kwargs: Argumentos con nombre para la tarea
        
    Returns:
        Resultado de la tarea
    """
    task_func = registered_tasks.get(task_name)
    
    if not task_func:
        logger.error(f"Tarea no encontrada: {task_name}")
        raise ValueError(f"Tarea desconocida: {task_name}")
    
    try:
        # Verificar si la tarea es una corrutina
        if asyncio.iscoroutinefunction(task_func):
            return await task_func(*args, **kwargs)
        else:
            # Si es una función síncrona, ejecutarla en un hilo
            with ThreadPoolExecutor() as executor:
                return await asyncio.get_event_loop().run_in_executor(
                    executor, 
                    functools.partial(task_func, *args, **kwargs)
                )
    except Exception as e:
        logger.exception(f"Error al ejecutar la tarea {task_name}: {str(e)}")
        raise


async def enqueue_task(task_name: str, *args, **kwargs) -> None:
    """
    Encola una tarea para su ejecución asíncrona.
    
    Args:
        task_name: Nombre de la tarea a encolar
        *args: Argumentos posicionales para la tarea
        **kwargs: Argumentos con nombre para la tarea
    """
    if task_name not in registered_tasks:
        logger.error(f"Intento de encolar tarea desconocida: {task_name}")
        raise ValueError(f"Tarea desconocida: {task_name}")
    
    await task_queue.put({
        "task_name": task_name,
        "args": args,
        "kwargs": kwargs
    })
    logger.debug(f"Tarea encolada: {task_name}")


async def worker_process() -> None:
    """
    Proceso de trabajo que consume tareas de la cola y las ejecuta.
    """
    logger.info(f"{Fore.GREEN}Iniciando worker de tareas en segundo plano{Style.RESET_ALL}")
    
    while True:
        try:
            # Esperar una tarea de la cola
            task_data = await task_queue.get()
            task_name = task_data["task_name"]
            args = task_data["args"]
            kwargs = task_data["kwargs"]
            
            logger.info(f"Ejecutando tarea: {task_name}")
            
            # Ejecutar la tarea
            await execute_task(task_name, *args, **kwargs)
            
            # Marcar tarea como completada
            task_queue.task_done()
            logger.info(f"Tarea completada: {task_name}")
            
        except asyncio.CancelledError:
            logger.info("Worker cancelado")
            break
        except Exception as e:
            logger.exception(f"Error en worker: {str(e)}")


async def start_worker(num_workers: int = 3) -> List[asyncio.Task]:
    """
    Inicia múltiples workers para procesar tareas en paralelo.
    
    Args:
        num_workers: Número de workers a iniciar
        
    Returns:
        Lista de tareas de worker
    """
    workers = []
    for i in range(num_workers):
        worker = asyncio.create_task(worker_process())
        workers.append(worker)
        logger.info(f"Worker {i+1} iniciado")
    
    return workers


async def shutdown_worker(workers: List[asyncio.Task]) -> None:
    """
    Cierra los workers de forma segura.
    
    Args:
        workers: Lista de tareas de worker a cerrar
    """
    logger.info(f"{Fore.YELLOW}Cerrando workers...{Style.RESET_ALL}")
    
    # Esperar a que la cola se vacíe
    if not task_queue.empty():
        logger.info("Esperando a que se completen las tareas pendientes...")
        await task_queue.join()
    
    # Cancelar todos los workers
    for worker in workers:
        worker.cancel()
    
    # Esperar a que todos los workers se cierren
    await asyncio.gather(*workers, return_exceptions=True)
    logger.info("Workers cerrados correctamente")


if __name__ == "__main__":
    """
    Punto de entrada para ejecutar el worker directamente.
    """
    import importlib
    
    # Importar tareas registradas
    from app.tasks import *
    
    # Número de workers
    num_workers = int(os.getenv("NUM_WORKERS", "3"))
    
    # Configurar manejo de señales
    loop = asyncio.get_event_loop()
    workers = []
    
    async def shutdown(signal_type=None):
        """Cierra los workers y el bucle de eventos de forma segura."""
        logger.info(f"Recibida señal de cierre: {signal_type}")
        if workers:
            await shutdown_worker(workers)
        loop.stop()
    
    # Registrar manejadores de señales
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            signal_name, 
            lambda s=signal_name: asyncio.create_task(shutdown(s))
        )
    
# Iniciar workers
    async def main():
        global workers
        workers = await start_worker(num_workers)
        # Mantener la ejecución para que los workers sigan funcionando
        while True:
            await asyncio.sleep(3600)  # 1 hora
    
    try:
        print(f"{Fore.CYAN}Worker de Control de Equipos{Style.RESET_ALL}")
        print(f"Iniciando {num_workers} workers...")
        loop.create_task(main())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupción manual")
    finally:
        loop.close()
        logger.info("Worker terminado")
