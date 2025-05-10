import re
from datetime import datetime

class ApacheParser:
    def __init__(self):
        # Patrón común para logs de acceso Apache
        self.access_pattern = re.compile(
            r'(\S+) \S+ \S+ \[([^:]+):(\d+:\d+:\d+) ([^\]]+)\] "(\S+) (.*?) (\S+)" (\d+) (\S+) "([^"]*)" "([^"]*)"(?: (\d+))?'
        )
        
        # Patrón mejorado para logs de error Apache que soporta el formato mostrado
        self.error_pattern = re.compile(
            r'\[(.*?)\] \[([^:]+):([^\]]+)\] \[(?:pid (\d+)(?::tid (\d+))?)?\] (.+)'
        )
        
    def parse_date(self, date_str, time_str=None, timezone=None):
        """Convierte la fecha y hora del log a formato datetime"""
        try:
            # Si es un formato de error log con fecha y hora juntos
            if time_str is None and ' ' in date_str:
                # Patrones comunes de fecha/hora en logs de error
                error_formats = [
                    '%a %b %d %H:%M:%S.%f %Y',  # Sat May 10 00:02:52.587159 2025
                    '%a %b %d %H:%M:%S %Y',     # Sat May 10 00:02:52 2025
                    '%Y-%m-%d %H:%M:%S.%f',     # 2025-05-10 00:02:52.587159
                    '%Y-%m-%d %H:%M:%S'         # 2025-05-10 00:02:52
                ]
                
                for fmt in error_formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            
            # Formatos comunes en logs de acceso Apache
            if time_str is not None:
                date_formats = [
                    '%d/%b/%Y:%H:%M:%S',  # Formato común: 10/Oct/2023:13:55:36
                    '%d/%b/%Y %H:%M:%S',  # Alternativa: 10/Oct/2023 13:55:36
                ]
                
                # Intentar con diferentes formatos
                for fmt in date_formats:
                    try:
                        if ':' in date_str:  # Si la fecha ya incluye la hora
                            return datetime.strptime(date_str, fmt)
                        else:  # Si la fecha y hora están separadas
                            datetime_str = f"{date_str}:{time_str}"
                            return datetime.strptime(datetime_str, fmt)
                    except ValueError:
                        continue
            
            # Última alternativa: analizar manualmente el formato de acceso
            months = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            # Para formato "10/Oct/2023:13:55:36"
            if time_str is not None and '/' in date_str:
                parts = date_str.split(':')
                date_part = parts[0]
                time_part = time_str
                
                day, month, year = date_part.split('/')
                month = months.get(month, 1)
                
                hour, minute, second = time_part.split(':')
                
                return datetime(int(year), month, int(day), 
                              int(hour), int(minute), int(second))
            
            return datetime.now()  # Fallback si no se puede analizar
            
        except Exception as e:
            print(f"Error al parsear fecha: {e}")
            return datetime.now()  # En caso de error, usar fecha actual
            
    def parse_access_log(self, filepath):
        """Parsea un archivo de log de acceso de Apache"""
        entries = []
        
        try:
            with open(filepath, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Intentar con el patrón regular
                        match = self.access_pattern.match(line)
                        
                        if match:
                            ip, date, time, timezone, method, path, protocol, status, bytes_sent, referer, user_agent, response_time = match.groups()
                            
                            # Convertir campos numéricos
                            status = int(status) if status and status != '-' else 0
                            bytes_sent = int(bytes_sent) if bytes_sent and bytes_sent != '-' else 0
                            response_time = float(response_time) if response_time and response_time != '-' else 0.0
                            
                            # Crear datetime
                            fecha_hora = self.parse_date(date, time, timezone)
                            
                            entry = {
                                'ip': ip,
                                'fecha_hora': fecha_hora,
                                'metodo': method,
                                'ruta': path,
                                'protocolo': protocol,
                                'codigo_estado': status,
                                'bytes_enviados': bytes_sent,
                                'referer': referer,
                                'user_agent': user_agent,
                                'tiempo_respuesta': response_time
                            }
                            entries.append(entry)
                        else:
                            # Intentar extraer campos clave si el patrón no coincide
                            # Este es un enfoque de respaldo que intenta extraer al menos algunos datos
                            parts = line.split()
                            if len(parts) >= 10:
                                ip = parts[0]
                                
                                # Buscar fecha y hora
                                date_time = None
                                for part in parts:
                                    if '[' in part and ']' in part:
                                        date_time = part.strip('[]')
                                        break
                                
                                # Extraer método, ruta y protocolo
                                method = None
                                path = None
                                protocol = None
                                for i, part in enumerate(parts):
                                    if part in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD']:
                                        method = part
                                        if i+1 < len(parts):
                                            path = parts[i+1]
                                        if i+2 < len(parts):
                                            protocol = parts[i+2]
                                        break
                                
                                # Extraer código de estado
                                status = 0
                                for part in parts:
                                    if part.isdigit() and len(part) == 3:
                                        status = int(part)
                                        break
                                
                                # Crear entry con valores predeterminados
                                entry = {
                                    'ip': ip,
                                    'fecha_hora': datetime.now() if not date_time else datetime.now(),
                                    'metodo': method or 'UNKNOWN',
                                    'ruta': path or '/',
                                    'protocolo': protocol or 'HTTP/1.1',
                                    'codigo_estado': status,
                                    'bytes_enviados': 0,
                                    'referer': '',
                                    'user_agent': '',
                                    'tiempo_respuesta': 0.0
                                }
                                entries.append(entry)
                    except Exception as e:
                        print(f"Error al procesar línea de log de acceso: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error al abrir o leer el archivo de log: {e}")
            
        return entries
        
    def parse_error_log(self, filepath):
        """Parsea un archivo de log de errores de Apache"""
        entries = []
        
        try:
            with open(filepath, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Intentar con el patrón regular actualizado
                        match = self.error_pattern.match(line)
                        
                        if match:
                            date_time, module, level, pid, tid, message = match.groups()
                            
                            # Crear datetime
                            fecha_hora = self.parse_date(date_time)
                            
                            # Extraer información de archivo y línea si está presente en el mensaje
                            file_info = None
                            line_number = 0
                            
                            # Buscar patrones comunes de archivo:línea en el mensaje
                            file_match = re.search(r'(?:in|at) ([^:]+):(\d+)', message)
                            if file_match:
                                file_info = file_match.group(1)
                                try:
                                    line_number = int(file_match.group(2))
                                except:
                                    line_number = 0
                            
                            # Extraer código de error de Apache (AH00xxx)
                            error_code = ""
                            code_match = re.search(r'(AH\d+)', message)
                            if code_match:
                                error_code = code_match.group(1)
                            
                            entry = {
                                'fecha_hora': fecha_hora,
                                'modulo': module,
                                'nivel_error': level,
                                'pid': int(pid) if pid else 0,
                                'tid': tid or '',
                                'codigo_error': error_code,
                                'mensaje': message,
                                'archivo': file_info or '',
                                'linea': line_number
                            }
                            entries.append(entry)
                        else:
                            # Enfoque alternativo si el patrón no coincide
                            # Buscar fechas y horas entre corchetes
                            date_parts = re.findall(r'\[(.*?)\]', line)
                            fecha_hora = datetime.now()
                            module = ''
                            level = 'unknown'
                            
                            if date_parts:
                                # Primer corchete suele ser la fecha
                                try:
                                    fecha_hora = self.parse_date(date_parts[0])
                                except:
                                    pass
                                
                                # Segundo corchete suele ser módulo:nivel
                                if len(date_parts) > 1 and ':' in date_parts[1]:
                                    module_level = date_parts[1].split(':', 1)
                                    module = module_level[0]
                                    level = module_level[1] if len(module_level) > 1 else 'unknown'
                            
                            # Buscar una dirección IP
                            client_ip = None
                            ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                            ip_match = re.search(ip_pattern, line)
                            if ip_match:
                                client_ip = ip_match.group(0)
                                
                            entry = {
                                'fecha_hora': fecha_hora,
                                'modulo': module,
                                'nivel_error': level,
                                'pid': 0,
                                'tid': '',
                                'codigo_error': '',
                                'mensaje': line,
                                'archivo': '',
                                'linea': 0
                            }
                            entries.append(entry)
                    except Exception as e:
                        print(f"Error al procesar línea de log de error: {e} - Línea: {line}")
                        continue
                        
        except Exception as e:
            print(f"Error al abrir o leer el archivo de log: {e}")
            
        return entries
    
    def parse_log(self, filepath):
        """Determina automáticamente el tipo de log y lo parsea"""
        try:
            # Utilizar el detector de tipo de log mejorado
            log_type = self.detect_log_type(filepath)
            
            if log_type == 'apache_error':
                print("Detectado archivo de logs de error")
                return self.parse_error_log(filepath)
            elif log_type == 'apache_access':
                print("Detectado archivo de logs de acceso")
                return self.parse_access_log(filepath)
            else:
                print(f"No se pudo determinar el tipo de log: {log_type}")
                return []
                
        except Exception as e:
            print(f"Error al procesar el archivo: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
            
    def detect_log_type(self, filepath):
        """Versión mejorada para detectar el tipo de log de Apache"""
        try:
            with open(filepath, 'r', errors='ignore') as f:
                # Leer múltiples líneas para mejor contexto
                sample_lines = []
                for _ in range(10):  # Leer hasta 10 líneas
                    try:
                        line = next(f).strip()
                        if line:
                            sample_lines.append(line)
                    except StopIteration:
                        break
                
            if not sample_lines:
                raise ValueError("Archivo vacío o no se pudo leer")
                
            # Contar patrones específicos para determinar el tipo de log
            error_count = 0
            access_count = 0
            
            for line in sample_lines:
                # Verificar patrones de error
                if line.startswith('[') and ']' in line:
                    # Buscar patrón [fecha] [módulo:nivel] [pid:tid]
                    if re.search(r'\[.*?\] \[.*?:.*?\]', line):
                        error_count += 2  # Dar más peso a coincidencias fuertes
                    # Buscar niveles comunes de error
                    elif any(level in line.lower() for level in ['notice', 'error', 'warn', 'info', 'debug', 'crit']):
                        error_count += 1
                    # Buscar códigos AH
                    elif 'AH' in line and re.search(r'AH\d+', line):
                        error_count += 1
                
                # Verificar patrones de acceso
                if '"GET' in line or '"POST' in line or '"PUT' in line or '"DELETE' in line:
                    access_count += 2  # Dar más peso a coincidencias fuertes
                elif ' 200 ' in line or ' 404 ' in line or ' 500 ' in line:  # Códigos HTTP comunes
                    access_count += 1
                elif re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line) and '"' in line:
                    access_count += 1
            
            # Determinar el tipo basado en los conteos
            if error_count > access_count:
                return 'apache_error'
            elif access_count > error_count:
                return 'apache_access'
            elif error_count > 0:
                return 'apache_error'  # Predecir error si hay alguna coincidencia
            elif access_count > 0:
                return 'apache_access'
            
            # Si todavía no está claro, verificar el formato más detalladamente
            content = '\n'.join(sample_lines)
            if '[' in content and ']' in content:
                if re.search(r'\[pid \d+', content) or re.search(r'\[.*?:.*?\]', content):
                    return 'apache_error'
            
            # Si llegamos aquí, no pudimos determinar el tipo
            raise ValueError("No se pudo determinar el tipo de log")
                
        except Exception as e:
            raise ValueError(f"Error al detectar tipo de log: {str(e)}")