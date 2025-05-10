from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename
from models.database import Database
from parsers.apache_parser import ApacheParser
from parsers.ftp_parser import FTPParser
import config
import re

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = config.SECRET_KEY

db = Database()


def before_first_request():
    """Limpiar la base de datos antes de la primera solicitud"""
    clear_database()

def clear_database():
    """Limpia las tablas de la base de datos"""
    try:
        db.clear_all_logs()  # Método que debes implementar en tu clase Database
        print("Base de datos limpiada")
    except Exception as e:
        print(f"Error al limpiar la base de datos: {e}")

# Asegurar que el directorio de uploads exista
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/logs/view')
def logs_view():
    return render_template('logs_view.html')

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'logfile' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(request.referrer)
    
    file = request.files['logfile']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(request.referrer)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            # Detectar el tipo de log y procesarlo
            log_type = detect_log_type(filepath)
            process_log_file(filepath, log_type)
            
            flash(f'Archivo {filename} cargado y procesado correctamente como {log_type}', 'success')
            return redirect(url_for('view_log', filename=filename, log_type=log_type))
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            return redirect(request.referrer)
    else:
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(request.referrer)

def detect_log_type(filepath):
    """Detecta el tipo de log basado en su contenido"""
    try:
        # Leer las primeras líneas para análisis
        with open(filepath, 'r', errors='ignore') as f:
            # Leer más líneas para tener una muestra más representativa
            sample_lines = ''.join([f.readline() for _ in range(20)])
        
        # Patrones específicos para vsftpd.log y otros logs de FTP
        # Primero verificar si es un log de FTP
        if 'vsftpd' in sample_lines.lower() or 'ftp' in sample_lines.lower():
            return 'ftp_log'
        
        # Verificar patrones específicos de FTP
        if re.search(r'(STOR|RETR|DELE|MKD|RMD|CWD|USER|PASS|QUIT)', sample_lines):
            return 'ftp_log'
        
        # Verificar patrones de transferencia FTP
        if ('bytes sent' in sample_lines.lower() or 
            'bytes received' in sample_lines.lower() or
            re.search(r'(\d+ bytes|download|upload|transfer complete)', sample_lines.lower())):
            return 'ftp_transfer'
            
        # Verificar si es un log de acceso de Apache
        if re.search(r'"(GET|POST|PUT|DELETE|HEAD|OPTIONS) .+? HTTP/\d', sample_lines):
            return 'apache_access'
            
        # Verificar si es un log de error de Apache
        if '[' in sample_lines and ']' in sample_lines:
            # Patrones específicos de logs de error de Apache
            if any(module in sample_lines for module in ['mpm_', 'core:', 'ssl:', 'auth']):
                return 'apache_error'
            # Buscar niveles de error comunes
            elif any(level in sample_lines.lower() for level in ['notice', 'error', 'warn', 'info', 'debug', 'crit']):
                return 'apache_error'
            # Buscar códigos AH
            elif 'AH' in sample_lines and re.search(r'AH\d+', sample_lines):
                return 'apache_error'
                
        # Análisis secundario para FTP si aún no se ha detectado
        # vsftpd produce logs con patrón de fecha específico seguido de nombre de servidor
        if re.search(r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}.*?ftp', sample_lines, re.IGNORECASE):
            return 'ftp_log'
            
        # Si llegamos aquí y vemos un patrón común de log con IP, podría ser FTP
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        if re.search(ip_pattern, sample_lines):
            # Si hay IPs y alguna actividad que parece FTP
            if any(word in sample_lines.lower() for word in ['login', 'user', 'session', 'connection', 'failed', 'anonymous']):
                return 'ftp_log'
                
        # Si llegamos aquí e intentamos un último esfuerzo por detectar logs de Apache
        if (sample_lines.startswith('[') and 
            any((':' in line) for line in sample_lines.split('\n'))):
            return 'apache_error'
                
        # Todavía no se ha detectado, usar ApacheParser como último recurso
        try:
            apache_parser = ApacheParser()
            log_type = apache_parser.detect_log_type(filepath)
            return log_type
        except:
            # Si todo falla, asumir que es un log FTP si el nombre lo sugiere
            if 'ftp' in filepath.lower() or 'vsftpd' in filepath.lower():
                return 'ftp_log'
            
        raise ValueError("No se pudo determinar el tipo de log")
            
    except Exception as e:
        # Si hay error al abrir o procesar, intentamos inferir por el nombre del archivo
        if 'ftp' in filepath.lower() or 'vsftpd' in filepath.lower():
            return 'ftp_log'
        elif 'access' in filepath.lower():
            return 'apache_access'
        elif 'error' in filepath.lower():
            return 'apache_error'
        else:
            raise ValueError(f"No se pudo determinar el tipo de log: {str(e)}")

def process_log_file(filepath, log_type):
    """Procesa el archivo de log según su tipo"""
    if log_type == 'apache_access':
        parser = ApacheParser()
        entries = parser.parse_access_log(filepath)
        for entry in entries:
            db.insert_access_log(entry)
    elif log_type == 'apache_error':
        parser = ApacheParser()
        entries = parser.parse_error_log(filepath)
        for entry in entries:
            db.insert_error_log(entry)
    elif log_type == 'ftp_log':
        parser = FTPParser()
        entries = parser.parse_ftp_log(filepath)
        for entry in entries:
            db.insert_ftp_log(entry)
    elif log_type == 'ftp_transfer':
        parser = FTPParser()
        entries = parser.parse_ftp_transfer(filepath)
        for entry in entries:
            db.insert_ftp_transfer(entry)

@app.route('/view/<log_type>/<filename>')
def view_log(log_type, filename):
    """Muestra los logs procesados según su tipo"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    if log_type == 'apache_access':
        logs = db.get_access_logs(page, per_page)
        total = db.count_access_logs()
    elif log_type == 'apache_error':
        logs = db.get_error_logs(page, per_page)
        total = db.count_error_logs()
    elif log_type == 'ftp_log':
        logs = db.get_ftp_logs(page, per_page)
        total = db.count_ftp_logs()
    elif log_type == 'ftp_transfer':
        logs = db.get_ftp_transfers(page, per_page)
        total = db.count_ftp_transfers()
    else:
        flash('Tipo de log no válido', 'danger')
        return redirect(url_for('index'))
    
    # Asegúrate de que total no sea None o 0 antes de calcular total_pages
    total = total or 0  # Si total es None o 0, se asigna 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return render_template('logs_view.html', 
                           logs=logs, 
                           log_type=log_type, 
                           filename=filename,
                           page=page,
                           total_pages=total_pages)

@app.route('/api/logs/<log_type>')
def api_get_logs(log_type):
    """API para obtener logs en formato JSON"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    if log_type == 'apache_access':
        logs = db.get_access_logs(page, per_page)
    elif log_type == 'apache_error':
        logs = db.get_error_logs(page, per_page)
    elif log_type == 'ftp_log':
        logs = db.get_ftp_logs(page, per_page)
    elif log_type == 'ftp_transfer':
        logs = db.get_ftp_transfers(page, per_page)
    else:
        return jsonify({'error': 'Tipo de log no válido'}), 400
    
    return jsonify({'logs': logs})


@app.route('/clear_database', methods=['POST'])
def clear_database_route():
    """Limpiar la base de datos desde la interfaz"""
    try:
        db.clear_all_logs()  # Limpia los registros
        flash('Base de datos limpiada correctamente', 'success')
    except Exception as e:
        flash(f'Error al limpiar la base de datos: {e}', 'danger')
    
    return redirect(url_for('index'))  # Redirige a la página de inicio

# Si quieres probar el parser de error directamente
@app.route('/test_parser', methods=['POST'])
def test_parser():
    """Prueba el parser con un archivo subido sin guardarlo en la BD"""
    if 'logfile' not in request.files:
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    file = request.files['logfile']
    
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            # Detectar tipo de log
            log_type = detect_log_type(filepath)
            
            # Parsear según el tipo
            if log_type == 'apache_error':
                parser = ApacheParser()
                entries = parser.parse_error_log(filepath)
            elif log_type == 'apache_access':
                parser = ApacheParser()
                entries = parser.parse_access_log(filepath)
            elif log_type == 'ftp_log':
                parser = FTPParser()
                entries = parser.parse_ftp_log(filepath)
            elif log_type == 'ftp_transfer':
                parser = FTPParser()
                entries = parser.parse_ftp_transfer(filepath)
            else:
                return jsonify({'error': f'Tipo no soportado: {log_type}'}), 400
                
            # Mostrar resultados para las primeras 5 entradas
            result = {
                'type': log_type,
                'entries_count': len(entries),
                'sample': entries[:5] if entries else []
            }
            
            return jsonify(result), 200
            
        except Exception as e:
            return jsonify({'error': f'Error al procesar: {str(e)}'}), 500
            
    else:
        return jsonify({'error': 'Tipo de archivo no permitido'}), 400

if __name__ == '__main__':
    app.run(debug=True)