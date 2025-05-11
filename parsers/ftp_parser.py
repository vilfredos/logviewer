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
            
    def parse_ftp_log(self, filepath):
        """Parsea un archivo de log FTP general"""
        entries = []
        
        try:
            with open(filepath, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # Intentar con el patrón regular
                        match = self.ftp_pattern.match(line)
                        
                        if match:
                            date_time, usuario, ip, detalles = match.groups()
                            
                            # Identificar acción y archivo
                            accion = 'unknown'
                            archivo = ''
                            
                            # Buscar comandos FTP comunes
                            ftp_commands = ['STOR', 'RETR', 'DELE', 'MKD', 'RMD', 'LIST', 'NLST', 'CDUP', 
                                           'CWD', 'PWD', 'SYST', 'QUIT', 'USER', 'PASS', 'ACCT', 'PORT']
                            
                            for cmd in ftp_commands:
                                if cmd in detalles:
                                    accion = cmd
                                    # Extraer archivo si existe
                                    parts = detalles.split(cmd, 1)
                                    if len(parts) > 1:
                                        archivo = parts[1].strip()
                                    break
                            
                            # Crear entry
                            entry = {
                                'fecha_hora': self.parse_date(date_time),
                                'usuario': usuario,
                                'ip': ip,
                                'accion': accion,
                                'archivo': archivo,
                                'detalles': detalles
                            }
                            entries.append(entry)
                        else:
                            # Enfoque alternativo si el patrón no coincide
                            parts = line.split()
                            if len(parts) >= 4:
                                # Buscar fecha (primeros elementos que forman una fecha válida)
                                date_str = ' '.join(parts[:5])  # Tomar hasta 5 elementos para la fecha
                                fecha_hora = self.parse_date(date_str)
                                
                                # Buscar usuario y dirección IP
                                usuario = 'anonymous'
                                ip = ''
                                
                                # Buscar IP en la línea
                                ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                                ip_match = re.search(ip_pattern, line)
                                if ip_match:
                                    ip = ip_match.group(0)
                                
                                # Buscar usuario común
                                for part in parts:
                                    if '@' in part or part.lower() in ['user', 'anonymous', 'admin', 'root']:
                                        usuario = part
                                        break
                                
                                # Determinar acción y archivo
                                accion = 'unknown'
                                archivo = ''
                                
                                for cmd in ['STOR', 'RETR', 'DELE', 'MKD', 'LIST']:
                                    if cmd in line:
                                        accion = cmd
                                        cmd_idx = line.find(cmd)
                                        if cmd_idx > 0:
                                            # Tomar el resto de la línea como archivo
                                            rest = line[cmd_idx + len(cmd):].strip()
                                            # Eliminar flags o parámetros adicionales
                                            archivo = rest.split()[0] if rest and ' ' in rest else rest
                                        break
                                
                                entry = {
                                    'fecha_hora': fecha_hora,
                                    'usuario': usuario,
                                    'ip': ip,
                                    'accion': accion,
                                    'archivo': archivo,
                                    'detalles': line
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