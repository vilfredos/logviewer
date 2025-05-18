import pymysql
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt
import io
import base64
from typing import Dict, List, Any, Tuple, Optional

class ReportAnalyzer2:
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

        
 
    def get_ftp_filtrado(self,texto,modo,desde,hasta):
        connection = self.get_connection()
        resultado = []
        query = """
            SELECT * FROM registros_ftp
            WHERE (
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
    

    def get_ftp_filtrado_grafico(self,texto,modo,desde,hasta):
        connection = self.get_connection()
        resultado = []
        query = ""
        
        params = [f"%{texto}%"] * 5

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            query += """
                SELECT HOUR(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip LIKE %s
                    OR accion LIKE %s
                    OR archivo LIKE %s
                    OR detalles LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """
            params.extend([desde, hasta])


        elif modo == "semanal":
            hoy = datetime.now()
            # Día de la semana: lunes=0, domingo=6
            dia_semana = hoy.weekday()
            
            lunes = hoy - timedelta(days=dia_semana)
            domingo = lunes + timedelta(days=6)

            desde = f"{lunes.date()} 00:00:00"
            hasta = f"{domingo.date()} 23:59:59"

            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip LIKE %s
                    OR accion LIKE %s
                    OR archivo LIKE %s
                    OR detalles LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """
            
            params.extend([desde, hasta])

        elif modo == "mensual":
            hoy = datetime.now()
            anio = hoy.year
            mes = hoy.month
            primer_dia = f"{anio}-{mes:02d}-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-{mes:02d}-{ultimo_dia_num} 23:59:59"

            query += """
                SELECT DATE_FORMAT(fecha_hora, '%Y-%m') AS tiempo, COUNT(*) AS cantidad
                FROM registros_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip LIKE %s
                    OR accion LIKE %s
                    OR archivo LIKE %s
                    OR detalles LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip LIKE %s
                    OR accion LIKE %s
                    OR archivo LIKE %s
                    OR detalles LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([desde, hasta])
        else:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip LIKE %s
                    OR accion LIKE %s
                    OR archivo LIKE %s
                    OR detalles LIKE %s
                )
                """

        

        try:
            cursor = connection.cursor()
            cursor.execute(query,params)
            resultado = cursor.fetchall()
            grafico_datos = {
                'tiempo': [fila['tiempo'] for fila in resultado],
                'cantidad': [fila['cantidad'] for fila in resultado]
            }
            grafico = self._create_bar_chart(
                    grafico_datos['tiempo'],
                    grafico_datos['cantidad'],
                    'Logs en el tiempo', 'Tiempo', 'Cantidad'
            )
            
        finally:
            connection.close()
        return grafico
    
    def _create_bar_chart(self, x_data, y_data, title, x_label, y_label):
        """Creates a base64 encoded bar chart image."""
        plt.figure(figsize=(10, 6))
        plt.bar(x_data, y_data)
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()
        
        encoded = base64.b64encode(image_png).decode('utf-8')
        return f"data:image/png;base64,{encoded}"