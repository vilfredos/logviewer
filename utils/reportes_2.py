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
        
        apache = self.get_apache_filtrado(texto,modo,desde,hasta)
        apache_g1 = self.get_apache_filtrado_grafico(texto,modo,desde,hasta)
        apache_gx = self.get_demas_graficos_apache(texto,modo,desde,hasta)

        apache_error = self.get_apache_error_filtrado(texto,modo,desde,hasta)
        apache_error_g1 = self.get_apache_error_filtrado_grafico(texto,modo,desde,hasta)
        resultado = {
            'ftp':{'tabla':ftp,
                   'g1':ftp_g1
                  },
            'xfer':{'tabla':xfer,
                    'g1':xfer_g1
                   },
            'apache':{'tabla':apache,
                    'g1':apache_g1,
                    'demas':apache_gx
                    },
            'apache_error':{'tabla':apache_error,
                    'g1':apache_error_g1
                    },
        }
        return resultado
 
    
    def get_apache_error_filtrado(self,texto,modo,desde,hasta):

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
    

    def get_apache_error_filtrado_grafico(self,texto,modo,desde,hasta):
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
                FROM registros_error
                WHERE (
                    nivel_error LIKE %s
                    OR cliente LIKE %s
                    OR mensaje LIKE %s
                    OR archivo LIKE %s
                    OR linea LIKE %s
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
                FROM registros_error
                WHERE (
                    nivel_error LIKE %s
                    OR cliente LIKE %s
                    OR mensaje LIKE %s
                    OR archivo LIKE %s
                    OR linea LIKE %s
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
                FROM registros_error
                WHERE (
                    nivel_error LIKE %s
                    OR cliente LIKE %s
                    OR mensaje LIKE %s
                    OR archivo LIKE %s
                    OR linea LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_error
                WHERE (
                    nivel_error LIKE %s
                    OR cliente LIKE %s
                    OR mensaje LIKE %s
                    OR archivo LIKE %s
                    OR linea LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([desde, hasta])
        else:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_error
                WHERE (
                    nivel_error LIKE %s
                    OR cliente LIKE %s
                    OR mensaje LIKE %s
                    OR archivo LIKE %s
                    OR linea LIKE %s
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

 
    def get_apache_filtrado(self,texto,modo,desde,hasta):

        connection = self.get_connection()
        resultado = []
        query = """
            SELECT * FROM registros_acceso
            WHERE (
                ip LIKE %s
                OR metodo LIKE %s
                OR ruta LIKE %s
                OR protocolo LIKE %s
                OR codigo_estado LIKE %s
                OR referer LIKE %s
                OR user_agent LIKE %s
            )
        """
        params = [f"%{texto}%"] * 7

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
    

    def get_apache_filtrado_grafico(self,texto,modo,desde,hasta):
        connection = self.get_connection()
        resultado = []
        query = ""
        
        params = [f"%{texto}%"] * 7

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            query += """
                SELECT HOUR(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_acceso
                WHERE (
                    ip LIKE %s
                    OR metodo LIKE %s
                    OR ruta LIKE %s
                    OR protocolo LIKE %s
                    OR codigo_estado LIKE %s
                    OR referer LIKE %s
                    OR user_agent LIKE %s
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
                FROM registros_acceso
                WHERE (
                    ip LIKE %s
                    OR metodo LIKE %s
                    OR ruta LIKE %s
                    OR protocolo LIKE %s
                    OR codigo_estado LIKE %s
                    OR referer LIKE %s
                    OR user_agent LIKE %s
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
                FROM registros_acceso
                WHERE (
                    ip LIKE %s
                    OR metodo LIKE %s
                    OR ruta LIKE %s
                    OR protocolo LIKE %s
                    OR codigo_estado LIKE %s
                    OR referer LIKE %s
                    OR user_agent LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_acceso
                WHERE (
                    ip LIKE %s
                    OR metodo LIKE %s
                    OR ruta LIKE %s
                    OR protocolo LIKE %s
                    OR codigo_estado LIKE %s
                    OR referer LIKE %s
                    OR user_agent LIKE %s
                )
                AND fecha_hora BETWEEN %s AND %s
                GROUP BY tiempo
                ORDER BY tiempo
            """

            params.extend([desde, hasta])
        else:
            query += """
                SELECT DATE(fecha_hora) AS tiempo, COUNT(*) AS cantidad
                FROM registros_acceso
                WHERE (
                    ip LIKE %s
                    OR metodo LIKE %s
                    OR ruta LIKE %s
                    OR protocolo LIKE %s
                    OR codigo_estado LIKE %s
                    OR referer LIKE %s
                    OR user_agent LIKE %s
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
    

    def get_demas_graficos_apache(self,texto,modo,desde,hasta):




        filtros_where = """
            WHERE (
                ip LIKE %s
                OR metodo LIKE %s
                OR ruta LIKE %s
                OR protocolo LIKE %s
                OR codigo_estado LIKE %s
                OR referer LIKE %s
                OR user_agent LIKE %s
            )
        """
        
        params = [f"%{texto}%"] * 7

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "semanal":
            hoy = datetime.now()
            # Día de la semana: lunes=0, domingo=6
            dia_semana = hoy.weekday()
            
            lunes = hoy - timedelta(days=dia_semana)
            domingo = lunes + timedelta(days=6)

            desde = f"{lunes.date()} 00:00:00"
            hasta = f"{domingo.date()} 23:59:59"

            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "mensual":
            hoy = datetime.now()
            anio = hoy.year
            mes = hoy.month
            primer_dia = f"{anio}-{mes:02d}-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-{mes:02d}-{ultimo_dia_num} 23:59:59"

            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])



        connection = self.get_connection()
        cursor = connection.cursor()
        report_data = {}

        # Total requests
        query = "SELECT COUNT(*) as total FROM registros_acceso"
        query += filtros_where
        cursor.execute(query,params)
        report_data["total"] = cursor.fetchone()['total']
        
        
        # Popular pages
        query = """
            SELECT ruta, COUNT(*) as count 
            FROM registros_acceso 

        """
        query += filtros_where
        query += """  
            GROUP BY ruta 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        populares = cursor.fetchall()
        populares = populares[::-1]
        report_data["populares"] = populares

        # Popular pages chart
        report_data["populares_chart"] = self._create_horizontal_bar_chart(
            [m['ruta'] for m in populares],
            [m['count'] for m in populares],
            'Rutas Populares',
            'Cantidad'
        )
        

        # HTTP methods distribution

        query = """
            SELECT metodo, COUNT(*) as count 
            FROM registros_acceso  

        """
        query += filtros_where
        query += """ 
            GROUP BY metodo 
            ORDER BY count DESC
        """
        
        cursor.execute(query,params)
        methods = cursor.fetchall()
        report_data["http_methods"] = methods
        
        # Method distribution chart
        report_data["http_methods_chart"] = self._create_pie_chart(
            [m['metodo'] for m in methods],
            [m['count'] for m in methods],
            'Metodos http usados'
        )


        
        # Response codes distribution

        query = """
            SELECT codigo_estado, COUNT(*) as count 
            FROM registros_acceso 
        """
        query+= filtros_where
        query+=""" 
            GROUP BY codigo_estado 
            ORDER BY count DESC
        """
        cursor.execute(query,params)
        status_codes = cursor.fetchall()
        report_data["status_codes"] = status_codes
        status_codes = status_codes[::-1]
        # Response codes distribution chart
        report_data["status_codes_chart"] = self._create_horizontal_bar_chart(
            [str(m['codigo_estado']) for m in status_codes],
            [m['count'] for m in status_codes],
            'Respuestas HTTP',
            'Cantidad'
        )

        
        # Top referring sites

        query = """
            SELECT referer, COUNT(*) as count 
            FROM registros_acceso 
        """
        query+= filtros_where
        query+= """ 
            AND (referer != '' AND referer IS NOT NULL)
            GROUP BY referer 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        top_referrers = cursor.fetchall()
        report_data["top_referrers"] = top_referrers
        top_referrers = top_referrers[::-1]
        # Top referring sites chart
        report_data["top_referrers_chart"] = self._create_horizontal_bar_chart(
            [str(m['referer']) for m in top_referrers],
            [m['count'] for m in top_referrers],
            'Sitios de referencia',
            'Cantidad'
        )
        
        # Top user agents
        query = """
            SELECT user_agent, COUNT(*) as count 
            FROM registros_acceso 
        """
        query += filtros_where
        query += """ 
            GROUP BY user_agent 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        top_user_agents = cursor.fetchall()
        top_user_agents = top_user_agents[::-1]
        report_data["top_user_agents"] = top_user_agents
        # Top user agents chart
        report_data["top_user_agents_chart"] = self._create_horizontal_bar_chart(
            [str(m['user_agent']) for m in top_user_agents],
            [m['count'] for m in top_user_agents],
            'Cliente usado',
            'Cantidad'
        )


        # Request size distribution

        query = """
            SELECT 
                CASE 
                    WHEN bytes_enviados < 1024 THEN '< 1KB'
                    WHEN bytes_enviados < 10240 THEN '1KB - 10KB'
                    WHEN bytes_enviados < 102400 THEN '10KB - 100KB'
                    WHEN bytes_enviados < 1048576 THEN '100KB - 1MB'
                    ELSE '> 1MB' 
                END as size_range,
                COUNT(*) as count
            FROM registros_acceso 
            
        """
        query += filtros_where
        query += """ 
             
            GROUP BY size_range
            ORDER BY 
                CASE size_range
                    WHEN '< 1KB' THEN 1
                    WHEN '1KB - 10KB' THEN 2
                    WHEN '10KB - 100KB' THEN 3
                    WHEN '100KB - 1MB' THEN 4
                    ELSE 5
                END
        """
        cursor.execute(query,params)
        size_ranges = cursor.fetchall()
        report_data["response_sizes"] = size_ranges
        
        # Response size chart
        report_data["response_sizes_chart"] = self._create_pie_chart(
            [r['size_range'] for r in size_ranges],
            [r['count'] for r in size_ranges],
            'Tamaños de respuestas enviadas'
        )
        
        # Top IPs
        query = """
            SELECT ip, COUNT(*) as count 
            FROM registros_acceso  
        """
        query += filtros_where
        query += """ 
             
            GROUP BY ip 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        top_ips = cursor.fetchall()
        top_ips = top_ips[::-1]
        report_data["top_ips"] = top_ips

        # Top IPs chart
        report_data["top_ips_chart"] = self._create_horizontal_bar_chart(
            [str(m['ip']) for m in top_ips],
            [m['count'] for m in top_ips],
            'IPs populares',
            'Cantidad'
        )

        
        # Response time statistics
        query = """
            SELECT 
                AVG(tiempo_respuesta) as avg_time,
                MAX(tiempo_respuesta) as max_time,
                MIN(tiempo_respuesta) as min_time
            FROM registros_acceso 
        """
        query += filtros_where
        cursor.execute(query, params)
        report_data["response_time_stats"] = cursor.fetchone()

        labels = ['Mínimo', 'Promedio', 'Máximo']
        values = [report_data["response_time_stats"]['min_time'], report_data["response_time_stats"]['avg_time'], report_data["response_time_stats"]['max_time']]

        report_data["response_time_stats_chart"] = self._create_bar_chart(labels, values, 'Tiempos de respuesta', '', 'ms')

        connection.close()
        return report_data 


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
    

    def _create_horizontal_bar_chart(self, y_data, x_data, title, x_label):
        """Creates a base64 encoded bar chart image."""
        plt.figure(figsize=(10, 6))
        plt.barh(y_data, x_data, color='cornflowerblue')
        plt.title(title)
        plt.xlabel(x_label)
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()
        
        encoded = base64.b64encode(image_png).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    
    
    def _create_pie_chart(self, labels, values, title):
        """Creates a base64 encoded pie chart image."""
        plt.figure(figsize=(8, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title(title)
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()
        
        encoded = base64.b64encode(image_png).decode('utf-8')
        return f"data:image/png;base64,{encoded}"