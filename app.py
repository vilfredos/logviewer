from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
from datetime import datetime, timedelta

from werkzeug.utils import secure_filename
from models.database import Database
from parsers.apache_parser import ApacheParser
from parsers.ftp_parser import FTPParser
from utils.report_analyzer import ReportAnalyzer
from utils.alerts_handler import get_alerts
from utils.alertas_2 import AlertasClass
from utils.reportes_2 import ReportAnalyzer2
import config
import re

from flask import request, send_file
import pandas as pd
import io
import base64

app = Flask(__name__)
app.config.from_object('config')
app.secret_key = config.SECRET_KEY

@app.context_processor
def inject_log_subido():
    return dict(log_subido=session.get('log_subido', False))
    
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
    return render_template('search.html', log_subido=log_subido)

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
            session['log_subido'] = True

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
        
        # Verificar primero si es un xferlog (formato específico de transferencia FTP)
        # El formato típico es: día-semana mes-nombre día-mes hora:min:seg año tiempo host bytes archivo tipo _ dirección modo usuario servicio resto
        xferlog_pattern = r'^\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}\s+\d+\s+\S+\s+\d+\s+\S+\s+[abcABC]\s+\_\s+[ioIO]\s+\S+\s+\S+\s+\S+'
        if re.search(xferlog_pattern, sample_lines, re.MULTILINE):
            return 'ftp_transfer'
            
        # Si el archivo se llama xferlog.log o tiene formato similar, es probable que sea un log de transferencia
        if 'xferlog' in filepath.lower() or re.search(r'(xfer|transfer)\.log', filepath.lower()):
            # Verificar si el contenido coincide con el formato general de xferlog
            if re.search(r'\d{4}\s+\d+\s+\S+\s+\d+\s+\/\S+\s+[abcABC]\s+\_\s+[ioIO]', sample_lines):
                return 'ftp_transfer'
        
        # Patrones específicos para vsftpd.log y otros logs de FTP
        if 'vsftpd' in sample_lines.lower() or 'ftp' in sample_lines.lower():
            # Verificar primero si parece un log de transferencia
            if re.search(r'bytes sent|bytes received|\d+\s+bytes|transfer complete', sample_lines.lower()):
                # Si tiene menciones de transferencia pero no es xferlog, sigue siendo un log de transferencia
                if re.search(r'(STOR|RETR)\s+\S+.*\d+\s+bytes', sample_lines):
                    return 'ftp_transfer'
            return 'ftp_log'
        
        # Verificar patrones específicos de FTP
        if re.search(r'(STOR|RETR|DELE|MKD|RMD|CWD|USER|PASS|QUIT)', sample_lines):
            return 'ftp_log'
            
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
            # Si todo falla, intentamos inferir por el nombre del archivo
            if 'xferlog' in filepath.lower():
                return 'ftp_transfer'
            elif 'ftp' in filepath.lower() or 'vsftpd' in filepath.lower():
                return 'ftp_log'
            
        raise ValueError("No se pudo determinar el tipo de log")
            
    except Exception as e:
        # Si hay error al abrir o procesar, intentamos inferir por el nombre del archivo
        if 'xferlog' in filepath.lower():
            return 'ftp_transfer'
        elif 'ftp' in filepath.lower() or 'vsftpd' in filepath.lower():
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
    per_page = 10
    
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
                           total_pages=total_pages,
                           total=total)

@app.route('/api/logs/<log_type>')
def api_get_logs(log_type):
    """API para obtener logs en formato JSON"""
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
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
    
@app.route('/search_logs')
def search_logs():
    """Busca en los logs según los criterios especificados"""
    # Obtener parámetros de búsqueda
    search_term = request.args.get('searchTerm', '')
    is_advanced = request.args.get('advancedSearch') == 'on'
    log_type = request.args.get('log_type', 'apache_access')  # Por defecto, usar apache_access
    
    # Parámetros de búsqueda avanzada
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    term1 = request.args.get('term1', '')
    operator = request.args.get('operator', 'AND')
    term2 = request.args.get('term2', '')
    filter_field = request.args.get('filterField', '')
    filter_value = request.args.get('filterValue', '')
    
    # Construir consulta según si es búsqueda básica o avanzada
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    try:
        if is_advanced:
            # Preparar los parámetros para búsqueda avanzada
            search_params = {
                'start_date': start_date,
                'end_date': end_date,
                'term1': term1,
                'operator': operator,
                'term2': term2,
                'filter_field': filter_field,
                'filter_value': filter_value
            }
            
            if log_type == 'apache_access':
                logs = db.search_access_logs_advanced(search_params, page, per_page)
                total = db.count_search_access_logs_advanced(search_params)
            elif log_type == 'apache_error':
                logs = db.search_error_logs_advanced(search_params, page, per_page)
                total = db.count_search_error_logs_advanced(search_params)
            elif log_type == 'ftp_log':
                logs = db.search_ftp_logs_advanced(search_params, page, per_page)
                total = db.count_search_ftp_logs_advanced(search_params)
            elif log_type == 'ftp_transfer':
                logs = db.search_ftp_transfers_advanced(search_params, page, per_page)
                total = db.count_search_ftp_transfers_advanced(search_params)
            else:
                flash('Tipo de log no válido para búsqueda', 'danger')
                return redirect(url_for('logs_view'))
        else:
            # Búsqueda básica (solo término)
            if log_type == 'apache_access':
                logs = db.search_access_logs(search_term, page, per_page)
                total = db.count_search_access_logs(search_term)
            elif log_type == 'apache_error':
                logs = db.search_error_logs(search_term, page, per_page)
                total = db.count_search_error_logs(search_term)
            elif log_type == 'ftp_log':
                logs = db.search_ftp_logs(search_term, page, per_page)
                total = db.count_search_ftp_logs(search_term)
            elif log_type == 'ftp_transfer':
                logs = db.search_ftp_transfers(search_term, page, per_page)
                total = db.count_search_ftp_transfers(search_term)
            else:
                flash('Tipo de log no válido para búsqueda', 'danger')
                return redirect(url_for('logs_view'))
        
        # Asegurar que total tenga un valor válido
        total = total or 0
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        # Mostrar resultados usando la misma plantilla logs_view.html
        return render_template('logs_view.html',
                               logs=logs,
                               log_type=log_type,
                               filename=None,  # No hay archivo específico
                               page=page,
                               total_pages=total_pages,
                               search_term=search_term,
                               is_advanced=is_advanced,
                               search_params=request.args)
                               
    except Exception as e:
        flash(f'Error al realizar la búsqueda: {str(e)}', 'danger')
        return redirect(url_for('logs_view'))   

## inicio CBRV 
@app.route('/reportes', methods=['GET'])
def reportes():

    db_config = config.DB_CONFIG
    report_analyzer2 = ReportAnalyzer2(db_config)
    resultados = report_analyzer2.get_todo("", 'todo', '', '')  # Carga inicial

    return render_template("reportes/reportes.html", resultados=resultados)


@app.route('/filtros_registro/<tipo_log>', methods=['POST'])
def filtros_registro(tipo_log):
    db_config = config.DB_CONFIG
    report_analyzer2 = ReportAnalyzer2(db_config)

    texto = request.form.get("texto", "").lower().strip()
    modo = request.form.get("modo")
    desde = request.form.get("desde")
    hasta = request.form.get("hasta")

    resultados = report_analyzer2.get_todo(texto, modo, desde, hasta)
    #vsftpd
    #xfer
    #apache
    #apache_error
    if tipo_log == "vsftpd":
        return render_template("partials/reportes_ftp.html", resultados=resultados['ftp'])
    elif tipo_log == "xfer":
        return render_template("partials/reportes_xfer.html", resultados=resultados['xfer'])
    elif tipo_log == "apache":
        return render_template("partials/reportes_apache.html", resultados=resultados['apache'])
    elif tipo_log == "apache_error":
        return render_template("partials/reportes_apache_error.html", resultados=resultados['apache_error'])
    else:
        return "", 400



@app.route('/alertas', methods=['GET'])
def alertas():
    db_config = config.DB_CONFIG
    alertas = AlertasClass(db_config)
    resultados = alertas.get_todo("", 'todo', '', '')  # Carga inicial

    return render_template("reportes/alertas.html", resultados=resultados)

@app.route('/filtros_alertas/<tipo_log>', methods=['POST'])
def filtros_alertas(tipo_log):
    db_config = config.DB_CONFIG
    alertas = AlertasClass(db_config)

    texto = request.form.get("texto", "").lower().strip()
    modo = request.form.get("modo")
    desde = request.form.get("desde")
    hasta = request.form.get("hasta")

    resultados = alertas.get_todo(texto, modo, desde, hasta)

    if tipo_log == "vsftpd":
        return render_template("partials/alertas_ftp.html", filas=resultados['ftp']['tabla'])
    elif tipo_log == "error_apache":
        return render_template("partials/alertas_apache.html", filas=resultados['apache']['tabla'])
    else:
        return "", 400



@app.route('/exportar_excel', methods=['POST'])
def exportar_excel():

    
    filtros = request.json  


    db_config = config.DB_CONFIG
    report_analyzer2 = ReportAnalyzer2(db_config)

    texto = filtros['texto']
    modo = filtros['modo']
    desde = filtros['desde']
    hasta = filtros['hasta']
    tipo = filtros['tipo']
    data = {'datos':[], 'imagenes':[]}
    if tipo == 'vsftpd':
        demas = report_analyzer2.get_demas_graficos_ftp(texto, modo, desde, hasta)
        data['datos'] = report_analyzer2.get_ftp_filtrado(texto, modo, desde, hasta)
        data['imagenes'] = [
            {'nombre':'Conteo de entradas',
             'imagen': report_analyzer2.get_ftp_filtrado_grafico(texto, modo, desde, hasta)},
             {'nombre':'Tipos de Acciones',
             'imagen': demas['action_chart']},
             {'nombre':'Inicios de sesion',
             'imagen': demas['login_stats_chart']},
             {'nombre':'Los usuarios mas activos',
             'imagen': demas['active_users_chart']},
             {'nombre':'Las IPs mas activas',
             'imagen': demas['active_ips_chart']},
             {'nombre':'Los archivos mas accedidos',
             'imagen': demas['accessed_files_chart']},
        ]

    elif tipo == 'xfer':
        demas = report_analyzer2.get_demas_graficos_xfer(texto, modo, desde, hasta)
        data['datos'] = report_analyzer2.get_xfer_filtrado(texto, modo, desde, hasta)
        data['imagenes'] = [
            {'nombre':'Conteo de entradas',
             'imagen': report_analyzer2.get_xfer_filtrado_grafico(texto, modo, desde, hasta)},
             {'nombre':'Direcciones',
             'imagen': demas['direction_chart']},
             {'nombre':'Servicios',
             'imagen': demas['services_chart']},
             {'nombre':'Metodos de autentificacion',
             'imagen': demas['auth_methods_chart']},
             {'nombre':'Los Usuarios mas activos',
             'imagen': demas['active_users_chart']},
             {'nombre':'Las IPs mas activas',
             'imagen': demas['active_ips_chart']},
             {'nombre':'Tamaño de los Archivo',
             'imagen': demas['size_chart']},
             {'nombre':'Promedios de duracion',
             'imagen': demas['avg_duration_chart']},
        ]

    elif tipo == 'apache':
        data['datos'] = report_analyzer2.get_apache_filtrado(texto, modo, desde, hasta)

        demas = report_analyzer2.get_demas_graficos_apache(texto, modo, desde, hasta)

        data['imagenes'] = [
            {'nombre':'Conteo de entradas',
             'imagen': report_analyzer2.get_apache_filtrado_grafico(texto, modo, desde, hasta)},
             {'nombre':'Las 10 Rutas más Populares',
             'imagen': demas['populares_chart']},
             {'nombre':'Métodos HTTP Usados',
             'imagen': demas['http_methods_chart']},
             {'nombre':'Respuestas HTTP Enviadas',
             'imagen': demas['status_codes_chart']},
             {'nombre':'URLs de Referencia',
             'imagen': demas['top_referrers_chart']},
             {'nombre':'Usuarios Utilizados',
             'imagen': demas['top_user_agents_chart']},
             {'nombre':'Tamaño de Bytes Enviados',
             'imagen': demas['response_sizes_chart']},
             {'nombre':'Las 10 IPs más Activas',
             'imagen': demas['top_ips_chart']},
             {'nombre':'Tiempo de Respuesta (mín, promedio, máx)',
             'imagen': demas['response_time_stats_chart']},
        ]
    elif tipo == 'apache_error':
        demas = report_analyzer2.get_demas_graficos_apache_error(texto, modo, desde, hasta)

        data['datos'] = report_analyzer2.get_apache_error_filtrado(texto, modo, desde, hasta)
        data['imagenes'] = [
            {'nombre':'Conteo de entradas',
             'imagen': report_analyzer2.get_apache_error_filtrado_grafico(texto, modo, desde, hasta)},
             {'nombre':'Severidad de los errores',
             'imagen': demas['error_level_chart']},
             {'nombre':'Mensajes de error Comunes',
             'imagen': demas['common_errors_chart']},
             {'nombre':'Los Archivos con mas Errores',
             'imagen': demas['error_files_chart']},
             {'nombre':'Los Clientes que causaron mas Errores',
             'imagen': demas['error_clients_chart']},
        ]
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Convertir a DataFrame sin la imagen
    df = []
    if tipo == "vsftpd":
        
        df = pd.DataFrame([{
        "Fecha y hora": row["fecha_hora"],
        "Usuario": row["usuario"],
        "IP": row["ip"],
        "Acción": row["accion"],
        "Archivo": row["archivo"],
        "Detalles": row["detalles"]
        } for row in data['datos']])
    elif tipo == "xfer":
        df = pd.DataFrame([{
        "Fecha y hora": row["fecha_hora"],
        "Tiempo de Transferencia": row["duracion"],
        "Host remoto": row["servidor"],
        "Tamaño del archivo": row["tamaño_archivo"],
        "Nombre del archivo": row["archivo"],
        "Tipo de transferencia": row["tipo_transferencia"],
        "Acción especial": row["accion_especial"],
        "Direccion": row["direccion"],
        "Usuario": row["usuario"],
        "Servicio": row["servicio"],
        "Método de autenticación": row["metodo_autenticacion"],
        "Usuario autenticado": row["usuario_id"]
        } for row in data['datos']])
    elif tipo == "apache":
        df = pd.DataFrame([{
        "IP": row["ip"],
        "Fecha y hora": row["fecha_hora"],
        "Metodo": row["metodo"],
        "Ruta": row["ruta"],
        "Protocolo": row["protocolo"],
        "Bytes enviados": row["bytes_enviados"],
        "Referencia": row["referer"],
        "Cliente": row["user_agent"],
        "Tiempo de Respuesta": row["tiempo_respuesta"],
        } for row in data['datos']])
    elif tipo == "apache_error":
        df = pd.DataFrame([{
        "Fecha y hora": row["fecha_hora"],
        "Severidad": row["nivel_error"],
        "Cliente": row["cliente"],
        "Mensaje": row["mensaje"],
        "archivo": row["archivo"],
        "Linea de Codigo": row["linea"],
        } for row in data['datos']])
    else:
        return "", 400
    
    df.to_excel(writer, index=False, sheet_name='Datos')
    workbook = writer.book
    sheet = workbook.add_worksheet('Imagenes')
    writer.sheets['Imagenes'] = sheet

    col_count = 2
    row_spacing = 30 

    for i, row in enumerate(data['imagenes']):
        fila_titulo = i * row_spacing
        fila_imagen = fila_titulo + 1

        # Título en columna 0
        sheet.write(fila_titulo, 0, row['nombre'])

        # Imagen
        imagen_b64 = row['imagen'].split(',')[1] if ',' in row['imagen'] else row['imagen']
        img_data = base64.b64decode(imagen_b64)
        img_io = io.BytesIO(img_data)

        sheet.insert_image(fila_imagen, 0, f"imagen_{i}.png", {
            'image_data': img_io,
            'x_scale': 0.5,
            'y_scale': 0.5
        })

    writer.close()
    output.seek(0)

    nombre_archivo = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return send_file(output, download_name=nombre_archivo, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)