import pymysql
import config
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from typing import Dict, Any
class Database:

    def __init__(self):
        self.config = config.DB_CONFIG

    def get_connection(self):
        """Establece conexión con la base de datos"""
        return pymysql.connect(
            host=self.config['host'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            cursorclass=pymysql.cursors.DictCursor
        )

    def insert_access_log(self, entry):
        """Inserta un registro de acceso en la base de datos"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO registros_acceso 
                (ip, fecha_hora, metodo, ruta, protocolo, codigo_estado, 
                bytes_enviados, referer, user_agent, tiempo_respuesta, fecha_registro) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    entry.get('ip', ''),
                    entry.get('fecha_hora'),
                    entry.get('metodo', ''),
                    entry.get('ruta', ''),
                    entry.get('protocolo', ''),
                    entry.get('codigo_estado', 0),
                    entry.get('bytes_enviados', 0),
                    entry.get('referer', ''),
                    entry.get('user_agent', ''),
                    entry.get('tiempo_respuesta', 0.0),
                    datetime.now()
                ))
            conn.commit()
        finally:
            conn.close()

    def insert_error_log(self, entry):
        """Inserta un registro de error en la base de datos"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO registros_error 
                (fecha_hora, nivel_error, cliente, mensaje, archivo, linea, fecha_registro) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    entry.get('fecha_hora'),
                    entry.get('nivel_error', ''),
                    entry.get('cliente', ''),
                    entry.get('mensaje', ''),
                    entry.get('archivo', ''),
                    entry.get('linea', 0),
                    datetime.now()
                ))
            conn.commit()
        finally:
            conn.close()

    def insert_ftp_log(self, entry):
        """Inserta un registro FTP en la base de datos"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO registros_ftp 
                (fecha_hora, usuario, ip, accion, archivo, detalles, fecha_registro) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    entry.get('fecha_hora'),
                    entry.get('usuario', ''),
                    entry.get('ip', ''),
                    entry.get('accion', ''),
                    entry.get('archivo', ''),
                    entry.get('detalles', ''),
                    datetime.now()
                ))
            conn.commit()
        finally:
            conn.close()

    def insert_ftp_transfer(self, entry):
        """Inserta un registro de transferencia FTP en la base de datos"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO transferencias_ftp 
                (fecha_hora, duracion, servidor, ip_remota, tamaño_archivo, archivo, 
                tipo_transferencia, accion_especial, direccion, usuario, servicio, 
                metodo_autenticacion, usuario_id, fecha_registro) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    entry.get('fecha_hora'),
                    entry.get('duracion', 0),
                    entry.get('servidor', ''),
                    entry.get('ip_remota', ''),
                    entry.get('tamaño_archivo', 0),
                    entry.get('archivo', ''),
                    entry.get('tipo_transferencia', ''),
                    entry.get('accion_especial', ''),
                    entry.get('direccion', ''),
                    entry.get('usuario', ''),
                    entry.get('servicio', ''),
                    entry.get('metodo_autenticacion', ''),
                    entry.get('usuario_id', ''),
                    datetime.now()
                ))
            conn.commit()
        finally:
            conn.close()

    def get_access_logs(self, page, per_page):
        """Obtiene registros de acceso paginados"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                offset = (page - 1) * per_page
                sql = "SELECT * FROM registros_acceso ORDER BY fecha_hora DESC LIMIT %s OFFSET %s"
                cursor.execute(sql, (per_page, offset))
                return cursor.fetchall()
        finally:
            conn.close()

    def get_error_logs(self, page, per_page):
        """Obtiene registros de error paginados"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                offset = (page - 1) * per_page
                sql = "SELECT * FROM registros_error ORDER BY fecha_hora DESC LIMIT %s OFFSET %s"
                cursor.execute(sql, (per_page, offset))
                return cursor.fetchall()
        finally:
            conn.close()

    def get_ftp_logs(self, page, per_page):
        """Obtiene registros FTP paginados"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                offset = (page - 1) * per_page
                sql = "SELECT * FROM registros_ftp ORDER BY fecha_hora DESC LIMIT %s OFFSET %s"
                cursor.execute(sql, (per_page, offset))
                return cursor.fetchall()
        finally:
            conn.close()

    def get_ftp_transfers(self, page, per_page):
        """Obtiene registros de transferencias FTP paginados"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                offset = (page - 1) * per_page
                sql = "SELECT * FROM transferencias_ftp ORDER BY fecha_hora DESC LIMIT %s OFFSET %s"
                cursor.execute(sql, (per_page, offset))
                return cursor.fetchall()
        finally:
            conn.close()

    def count_access_logs(self):
        """Cuenta el total de registros de acceso"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM registros_acceso")
                result = cursor.fetchone()
                return result['count'] if result else 0
        finally:
            conn.close()

    def count_error_logs(self):
        """Cuenta el total de registros de error"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM registros_error")
                result = cursor.fetchone()
                return result['count'] if result else 0
        finally:
            conn.close()

    def count_ftp_logs(self):
        """Cuenta el total de registros FTP"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM registros_ftp")
                result = cursor.fetchone()
                return result['count'] if result else 0
        finally:
            conn.close()

    def count_ftp_transfers(self):
        """Cuenta el total de registros de transferencias FTP"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM transferencias_ftp")
                result = cursor.fetchone()
                return result['count'] if result else 0
        finally:
            conn.close()

    def clear_all_logs(self):
        """Elimina todos los registros de las tablas de logs"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM registros_acceso")
                cursor.execute("DELETE FROM registros_error")
                cursor.execute("DELETE FROM registros_ftp")
                cursor.execute("DELETE FROM transferencias_ftp")
                conn.commit()
        except Exception as e:
            print(f"Error al limpiar la base de datos: {e}")
        finally:
            conn.close()

    def get_reportes_ftp(self,query,count_query,error_query,params):
        
        total_logs = 0
        total_errores = 0
        registros = []
        conn = self.get_connection()
        registros = conn.execute(query, params).fetchall()
        total_logs = conn.execute(count_query, params).fetchone()[0]
        total_errores = conn.execute(error_query, params).fetchone()[0]
        conn.close()

        return {'registros':registros, 'total_logs':total_logs, 'total_errores':total_errores}
    #CBRV