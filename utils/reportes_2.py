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

    
    def get_todo(self,texto,modo,desde,hasta):

        ftp = self.get_ftp_filtrado(texto,modo,desde,hasta)
        ftp_g1 = self.get_ftp_filtrado_grafico(texto,modo,desde,hasta)
        
        xfer = self.get_xfer_filtrado(texto,modo,desde,hasta)
        xfer_g1 = self.get_xfer_filtrado_grafico(texto,modo,desde,hasta)
        
        resultado = {
            'ftp':{'tabla':ftp,
                   'g1':ftp_g1
                  },
            'xfer':{'tabla':xfer,
                    'g1':xfer_g1
                   }
        }
        return resultado
 
    def get_xfer_filtrado(self,texto,modo,desde,hasta):

        connection = self.get_connection()
        resultado = []
        query = """
            SELECT * FROM transferencias_ftp
            WHERE (
                usuario LIKE %s
                OR ip_remota LIKE %s
                OR servidor LIKE %s
                OR archivo LIKE %s
                OR tipo_transferencia LIKE %s

                OR accion_especial LIKE %s
                OR direccion LIKE %s
                OR usuario LIKE %s
                OR servicio LIKE %s
                OR metodo_autenticacion LIKE %s
                OR usuario_id LIKE %s
            )
        """
        params = [f"%{texto}%"] * 11

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
    

    def get_xfer_filtrado_grafico(self,texto,modo,desde,hasta):
        connection = self.get_connection()
        resultado = []
        query = ""
        
        params = [f"%{texto}%"] * 11

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            query += """
                SELECT HOUR(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM transferencias_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip_remota LIKE %s
                    OR servidor LIKE %s
                    OR archivo LIKE %s
                    OR tipo_transferencia LIKE %s

                    OR accion_especial LIKE %s
                    OR direccion LIKE %s
                    OR usuario LIKE %s
                    OR servicio LIKE %s
                    OR metodo_autenticacion LIKE %s
                    OR usuario_id LIKE %s
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
                FROM transferencias_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip_remota LIKE %s
                    OR servidor LIKE %s
                    OR archivo LIKE %s
                    OR tipo_transferencia LIKE %s

                    OR accion_especial LIKE %s
                    OR direccion LIKE %s
                    OR usuario LIKE %s
                    OR servicio LIKE %s
                    OR metodo_autenticacion LIKE %s
                    OR usuario_id LIKE %s
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
            primer_dia = f"{anio}-01-01 00:00:00"
            ultimo_dia = f"{anio}-12-31 23:59:59"

            query += """
                SELECT MONTH(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM transferencias_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip_remota LIKE %s
                    OR servidor LIKE %s
                    OR archivo LIKE %s
                    OR tipo_transferencia LIKE %s

                    OR accion_especial LIKE %s
                    OR direccion LIKE %s
                    OR usuario LIKE %s
                    OR servicio LIKE %s
                    OR metodo_autenticacion LIKE %s
                    OR usuario_id LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM transferencias_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip_remota LIKE %s
                    OR servidor LIKE %s
                    OR archivo LIKE %s
                    OR tipo_transferencia LIKE %s

                    OR accion_especial LIKE %s
                    OR direccion LIKE %s
                    OR usuario LIKE %s
                    OR servicio LIKE %s
                    OR metodo_autenticacion LIKE %s
                    OR usuario_id LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([desde, hasta])
        else:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM transferencias_ftp
                WHERE (
                    usuario LIKE %s
                    OR ip_remota LIKE %s
                    OR servidor LIKE %s
                    OR archivo LIKE %s
                    OR tipo_transferencia LIKE %s

                    OR accion_especial LIKE %s
                    OR direccion LIKE %s
                    OR usuario LIKE %s
                    OR servicio LIKE %s
                    OR metodo_autenticacion LIKE %s
                    OR usuario_id LIKE %s
                )
                GROUP BY tiempo
                ORDER BY tiempo
                """

        

        try:
            cursor = connection.cursor()
            cursor.execute(query,params)
            resultado = cursor.fetchall()
            resultado = pd.DataFrame(resultado, columns=["tiempo", "cantidad"])
            resultado['tiempo'] = resultado['tiempo'].astype(str)
            grafico = self._create_bar_chart(
                resultado['tiempo'],
                resultado['cantidad'],
                'Logs en el tiempo', 'Tiempo', 'Cantidad'
            )
            
        finally:
            connection.close()
        return grafico
    

    

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
            primer_dia = f"{anio}-01-01 00:00:00"
            ultimo_dia = f"{anio}-12-31 23:59:59"

            query += """
                SELECT MONTH(fecha_hora) AS tiempo, COUNT(*) AS cantidad
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
                GROUP BY tiempo
                ORDER BY tiempo
                """

        

        try:
            cursor = connection.cursor()
            cursor.execute(query,params)
            resultado = cursor.fetchall()
            resultado = pd.DataFrame(resultado, columns=["tiempo", "cantidad"])
            resultado['tiempo'] = resultado['tiempo'].astype(str)
            grafico = self._create_bar_chart(
                resultado['tiempo'],
                resultado['cantidad'],
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