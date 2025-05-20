import pymysql
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
import io
import base64
from typing import Dict, List, Any, Tuple, Optional


class AlertasClass:
    def __init__(self, db_config: Dict[str, Any]):
        """Initializes the report analyzer with database configuration.
        
        Args:
            db_config: Dictionary with database connection parameters
        """
        self.config = db_config
        
    def get_connection(self):
        """Establishes connection with the database."""
        return pymysql.connect(
            host=self.config['host'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def get_todo(self,texto,modo,desde,hasta):
        ftp = self.get_ftp(texto,modo,desde,hasta)
        apache = self.get_apache(texto,modo,desde,hasta)
        resultado = {
            'ftp':{'tabla':ftp},
            'apache':{'tabla':apache}
        }
        return resultado
    

    def get_ftp(self,texto,modo,desde,hasta):
        connection = self.get_connection()
        resultado = []
        query = """
            SELECT * FROM registros_ftp
            WHERE (
                LOWER(accion) REGEXP 'fail|refused|denied|530|incorrect|error|crit|alert|emerg'
                OR LOWER(detalles) REGEXP 'fail|refused|denied|530|incorrect|error|crit|alert|emerg'
            ) AND (
                usuario LIKE %s
                OR ip LIKE %s
                OR accion LIKE %s
                OR archivo LIKE %s
                OR detalles LIKE %s
            )
        """
        params = [f"%{texto}%"] * 5

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "semanal":
            hoy = datetime.now()
            # Día de la semana: lunes=0, domingo=6
            dia_semana = hoy.weekday()
            
            lunes = hoy - timedelta(days=dia_semana)
            domingo = lunes + timedelta(days=6)

            desde = f"{lunes.date()} 00:00:00"
            hasta = f"{domingo.date()} 23:59:59"

            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "mensual":
            hoy = datetime.now()
            anio = hoy.year
            mes = hoy.month
            primer_dia = f"{anio}-{mes:02d}-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-{mes:02d}-{ultimo_dia_num} 23:59:59"

            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        
        

        try:
            cursor = connection.cursor()
            cursor.execute(query,params)
            resultado = cursor.fetchall()
        finally:
            connection.close()
        return resultado
    


    def get_apache(self,texto,modo,desde,hasta):
        connection = self.get_connection()
        resultado = []
        query = """
            SELECT * FROM registros_error
            WHERE (
                nivel_error LIKE %s
                OR cliente LIKE %s
                OR mensaje LIKE %s
                OR archivo LIKE %s
                OR linea LIKE %s
            )
        """
        params = [f"%{texto}%"] * 5

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "semanal":
            hoy = datetime.now()
            # Día de la semana: lunes=0, domingo=6
            dia_semana = hoy.weekday()
            
            lunes = hoy - timedelta(days=dia_semana)
            domingo = lunes + timedelta(days=6)

            desde = f"{lunes.date()} 00:00:00"
            hasta = f"{domingo.date()} 23:59:59"

            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "mensual":
            hoy = datetime.now()
            anio = hoy.year
            mes = hoy.month
            primer_dia = f"{anio}-{mes:02d}-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-{mes:02d}-{ultimo_dia_num} 23:59:59"

            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            query += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        
        

        try:
            cursor = connection.cursor()
            cursor.execute(query,params)
            resultado = cursor.fetchall()
        finally:
            connection.close()
        return resultado