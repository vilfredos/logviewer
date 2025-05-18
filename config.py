import os

# Configuración general
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_segura_predeterminada')
DEBUG = True
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'log', 'txt', 'log.gz', 'log.bz2', 'gz', 'bz2'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB límite de subida

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'gabriel',
    'password': 'gabo123',
    'database': 'bdlogs2',
}

# Configuración de paginación
PAGE_SIZE = 50