# ==========================================
# ARCHIVO: core_logger.py
# ==========================================
import logging

# Configuración centralizada de Logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

def get_logger(name: str) -> logging.Logger:
    """Retorna una instancia de logger configurada con el nombre del módulo."""
    return logging.getLogger(name)