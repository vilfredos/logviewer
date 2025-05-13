import re
from datetime import datetime

class FTPParser:
    def __init__(self):
        # Patrón común para logs de FTP
        self.ftp_pattern = re.compile(
            r'(\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} \d{4}) (\S+) \((\S+)\): (.+)'
        )
        
        # Patrón para logs de transferencia FTP (formato xferlog estándar)
        self.xferlog_pattern = re.compile(
            r'(\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} \d{4}) (\d+) (\S+) (\d+) (\S+) ([abcABC]) (\_) ([ioIO]) (\S+) (\S+) (\S+) (\S+) (.*)'
        )
        
        # Patrón alternativo para transferencias más genérico
        self.transfer_pattern = re.compile(
            r'(\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} \d{4}) (\d+) (\S+) (\S+) (\d+) (.+) (\w+) (\S+) (\w+) (\S+) (\S+) (\S+) (\S+)'
        )
        
    def parse_date(self, date_str):
        """Convierte la fecha del log a formato datetime"""
        try:
            # Formatos comunes en logs de FTP
            date_formats = [
                '%a %b %d %H:%M:%S %Y',  # Tue Jun 15 10:23:45 2023
                '%Y-%m-%d %H:%M:%S',     # 2023-06-15 10:23:45
                '%d/%b/%Y:%H:%M:%S'      # 15/Jun/2023:10:23:45
            ]
            
            # Intentar con diferentes formatos
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
            return datetime.now()  # Fallback si no se puede analizar
            
        except Exception as e:
            print(f"Error al parsear fecha FTP: {e}")
            return datetime.now()
        
    def parse_dates(self, date_str):
        """Convertir string de fecha a objeto datetime"""
        try:
            # Formato: Sat May 10 00:51:40 2025
            return datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
        except Exception as e:
            print(f"Error al parsear fecha '{date_str}': {e}")
            return datetime.now()  # Usar fecha actual como respaldo
        
    def parse_ftp_log(self, filepath):
        """Parsea un archivo de log de vsftpd"""
        entries = []
        
        try:
            with open(filepath, 'r', errors='ignore') as f:
                current_user = None
                current_ip = None
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Extraer fecha y hora
                        date_parts = line.split('[pid', 1)[0].strip()
                        fecha_hora = self.parse_date(date_parts)

                        # Extraer usuario evitando [pid]
                        usuario = 'anonymous'
                        usuario_match = re.search(r'\[(?!pid)([^\]]+)\]', line)
                        if usuario_match:
                            usuario = usuario_match.group(1)
                        elif 'USER ' in line:
                            user_parts = line.split('USER ', 1)
                            if len(user_parts) > 1:
                                usuario = user_parts[1].split()[0]
                        if usuario != 'anonymous' and usuario != '':
                            current_user = usuario
                        elif current_user:
                            usuario = current_user

                        # Extraer IP
                        ip = ''
                        ip_match = re.search(r'Client "([^"]+)"', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            current_ip = ip
                        elif current_ip:
                            ip = current_ip

                        # Determinar acción
                        accion = 'unknown'
                        archivo = ''
                        action_map = {
                            'CONNECT:': 'CONNECT',
                            'OK LOGIN:': 'LOGIN',
                            'FAIL LOGIN:': 'LOGIN_FAILED',
                            'OK UPLOAD:': 'UPLOAD',
                            'OK DOWNLOAD:': 'DOWNLOAD',
                            'STOR ': 'STOR',
                            'RETR ': 'RETR',
                            'DELE ': 'DELETE',
                            'MKD ': 'MKDIR',
                            'RMD ': 'RMDIR',
                            'CWD ': 'CWD',
                            'LIST': 'LIST',
                            'USER ': 'USER',
                            'PASS ': 'PASS',
                            'QUIT': 'QUIT'
                        }

                        for action_key, action_value in action_map.items():
                            if action_key in line:
                                accion = action_value
                                if action_key in ['STOR ', 'RETR ', 'DELE ', 'MKD ', 'RMD ', 'CWD ']:
                                    parts = line.split(action_key, 1)
                                    if len(parts) > 1:
                                        file_part = parts[1].strip()
                                        if '"' in file_part:
                                            file_match = re.search(r'"([^"]+)"', file_part)
                                            if file_match:
                                                archivo = file_match.group(1)
                                        else:
                                            archivo = file_part.split()[0]
                                elif action_key in ['OK UPLOAD:', 'OK DOWNLOAD:']:
                                    file_match = re.search(r'"[^"]+", "([^"]+)"', line)
                                    if file_match:
                                        archivo = file_match.group(1)
                                break

                        # Limpiar detalles
                        detalles = line
                        if '[pid' in detalles:
                            detalles = detalles.split('[pid', 1)[1]
                            if ']' in detalles:
                                detalles = detalles.split(']', 1)[1].strip()
                        if current_user and current_user != 'anonymous':
                            detalles = detalles.replace(f'[{current_user}] ', '')
                        detalles = detalles.strip()

                        # Construir entrada
                        entry = {
                            'fecha_hora': fecha_hora,
                            'usuario': usuario,
                            'ip': ip,
                            'accion': accion,
                            'archivo': archivo,
                            'detalles': detalles
                        }
                        entries.append(entry)

                    except Exception as e:
                        print(f"Error al procesar línea de log FTP: {e}")
                        continue

        except Exception as e:
            print(f"Error al abrir o leer el archivo de log FTP: {e}")

        return entries
    
        
    def parse_ftp_transfer(self, filepath):
        """Parsea un archivo de log de transferencias FTP (xferlog)"""
        entries = []
        
        try:
            with open(filepath, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Intentar primero con el patrón xferlog estándar
                        match = self.xferlog_pattern.match(line)
                        
                        if match:
                            # Formato xferlog estándar: fecha dur host bytes archivo tipo _ dir modo user serv auth resto
                            (date_time, duracion, servidor, tamano_archivo, 
                             archivo, tipo_transferencia, accion_especial, direccion, 
                             modo, usuario, servicio, autenticacion, resto) = match.groups()
                            
                            # Convertir valores numéricos
                            try:
                                duracion = int(duracion)
                            except:
                                duracion = 0
                                
                            try:
                                tamano_archivo = int(tamano_archivo)
                            except:
                                tamano_archivo = 0
                                
                            # Normalizar tipo_transferencia (a=ASCII, b=Binary)
                            tipo_transferencia = tipo_transferencia.upper()
                            
                            # Normalizar dirección (i=IN/upload, o=OUT/download)
                            direccion_normalizada = 'IN' if direccion.lower() == 'i' else 'OUT'
                            
                            entry = {
                                'fecha_hora': self.parse_date(date_time),
                                'duracion': duracion,
                                'servidor': servidor,
                                'ip_remota': servidor,  # En xferlog a veces se usa host como IP
                                'tamaño_archivo': tamano_archivo,
                                'archivo': archivo,
                                'tipo_transferencia': tipo_transferencia,
                                'accion_especial': accion_especial,
                                'direccion': direccion_normalizada,
                                'usuario': usuario,
                                'servicio': servicio,
                                'metodo_autenticacion': autenticacion,
                                'usuario_id': usuario
                            }
                            entries.append(entry)
                        else:
                            # Probar con el patrón alternativo para otros formatos de transferencia
                            match = self.transfer_pattern.match(line)
                            
                            if match:
                                (date_time, duracion, servidor, ip_remota, tamano_archivo, 
                                archivo, tipo_transferencia, accion_especial, direccion, 
                                usuario, servicio, autenticacion, usuario_id) = match.groups()
                                
                                # Convertir valores numéricos
                                try:
                                    duracion = int(duracion)
                                except:
                                    duracion = 0
                                    
                                try:
                                    tamano_archivo = int(tamano_archivo)
                                except:
                                    tamano_archivo = 0
                                
                                entry = {
                                    'fecha_hora': self.parse_date(date_time),
                                    'duracion': duracion,
                                    'servidor': servidor,
                                    'ip_remota': ip_remota,
                                    'tamaño_archivo': tamano_archivo,
                                    'archivo': archivo,
                                    'tipo_transferencia': tipo_transferencia,
                                    'accion_especial': accion_especial,
                                    'direccion': direccion,
                                    'usuario': usuario,
                                    'servicio': servicio,
                                    'metodo_autenticacion': autenticacion,
                                    'usuario_id': usuario_id
                                }
                                entries.append(entry)
                            else:
                                # Enfoque alternativo para xferlog si ningún patrón coincide
                                parts = line.split()
                                
                                # Verificar si tiene suficientes partes para ser un xferlog
                                if len(parts) >= 12:
                                    # En xferlog, los primeros 5 elementos suelen ser la fecha
                                    date_str = ' '.join(parts[:5])
                                    fecha_hora = self.parse_date(date_str)
                                    
                                    # Posiciones estándar en xferlog (puede variar)
                                    try:
                                        duracion = int(parts[5])
                                    except:
                                        duracion = 0
                                        
                                    servidor = parts[6]
                                    
                                    try:
                                        tamano_archivo = int(parts[7])
                                    except:
                                        tamano_archivo = 0
                                        
                                    archivo = parts[8]
                                    tipo_transferencia = parts[9].upper()  # a/b -> A/B
                                    accion_especial = parts[10]
                                    direccion = 'IN' if parts[11].lower() == 'i' else 'OUT'
                                    
                                    # Los campos restantes pueden variar según la implementación
                                    usuario = parts[12] if len(parts) > 12 else 'unknown'
                                    servicio = parts[13] if len(parts) > 13 else 'ftp'
                                    
                                    entry = {
                                        'fecha_hora': fecha_hora,
                                        'duracion': duracion,
                                        'servidor': servidor,
                                        'ip_remota': servidor,  # En algunos formatos no hay IP específica
                                        'tamaño_archivo': tamano_archivo,
                                        'archivo': archivo,
                                        'tipo_transferencia': tipo_transferencia,
                                        'accion_especial': accion_especial,
                                        'direccion': direccion,
                                        'usuario': usuario,
                                        'servicio': servicio,
                                        'metodo_autenticacion': 'password',  # Valor por defecto
                                        'usuario_id': usuario
                                    }
                                    entries.append(entry)
                    except Exception as e:
                        print(f"Error al procesar línea de log de transferencia FTP: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error al abrir o leer el archivo de log de transferencia FTP: {e}")
            
        return entries