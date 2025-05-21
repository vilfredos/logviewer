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
        ftp_gx = self.get_demas_graficos_ftp(texto,modo,desde,hasta)

        xfer = self.get_xfer_filtrado(texto,modo,desde,hasta)
        xfer_g1 = self.get_xfer_filtrado_grafico(texto,modo,desde,hasta)
        xfer_gx = self.get_demas_graficos_xfer(texto,modo,desde,hasta)
        
        apache = self.get_apache_filtrado(texto,modo,desde,hasta)
        apache_g1 = self.get_apache_filtrado_grafico(texto,modo,desde,hasta)
        apache_gx = self.get_demas_graficos_apache(texto,modo,desde,hasta)

        apache_error = self.get_apache_error_filtrado(texto,modo,desde,hasta)
        apache_error_g1 = self.get_apache_error_filtrado_grafico(texto,modo,desde,hasta)
        apache_error_gx = self.get_demas_graficos_apache_error(texto,modo,desde,hasta)

        resultado = {
            'ftp':{'tabla':ftp,
                   'g1':ftp_g1,
                   'demas':ftp_gx
                  },
            'xfer':{'tabla':xfer,
                    'g1':xfer_g1,
                    'demas':xfer_gx
                   },
            'apache':{'tabla':apache,
                    'g1':apache_g1,
                    'demas':apache_gx
                    },
            'apache_error':{'tabla':apache_error,
                    'g1':apache_error_g1,
                    'demas':apache_error_gx
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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

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

        stats = report_data["response_time_stats"]
        labels = ['Mínimo', 'Promedio', 'Máximo']
        values = [stats['min_time'], stats['avg_time'], stats['max_time']]

        # Reemplazar None por 0 (o puedes decidir omitir el gráfico)
        values = [v if v is not None else 0 for v in values]

        # Crear el gráfico solo si hay algún valor distinto de 0
        if any(values):
            report_data["response_time_stats_chart"] = self._create_bar_chart(labels, values, 'Tiempos de respuesta', '', 'ms')
        else:
            report_data["response_time_stats_chart"] = None  # O algún mensaje alternativo
        connection.close()
        return report_data 




    def get_demas_graficos_apache_error(self,texto,modo,desde,hasta):
        
        filtros_where = """ 
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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])


        connection = self.get_connection()
        cursor = connection.cursor()
        report_data = {}
       
        # Total errors
        query = """
        SELECT COUNT(*) as total FROM registros_error 

        """
        query += filtros_where
        cursor.execute(query,params)
        report_data["total_errors"] = cursor.fetchone()['total']
        
        # Errors by severity level
        query = """
            SELECT nivel_error, COUNT(*) as count 
            FROM registros_error  

        """
        query += filtros_where
        query += """
            GROUP BY nivel_error 
            ORDER BY count DESC
        """
        cursor.execute(query, params)
        errors_by_level = cursor.fetchall()
        report_data["errors_by_level"] = errors_by_level
        
        # Error level chart
        report_data["error_level_chart"] = self._create_pie_chart(
            [e['nivel_error'] for e in errors_by_level],
            [e['count'] for e in errors_by_level],
            'Error Level Distribution'
        )
        
        
        # Most common error messages
        query = """
            SELECT LEFT(mensaje, 100) as mensaje_short, COUNT(*) as count 
            FROM registros_error  

        """
        query += filtros_where
        query += """ 
            GROUP BY mensaje_short 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        common_errors = cursor.fetchall()
        common_errors = common_errors[::-1]
        report_data["common_errors"] = cursor.fetchall()
        

        # Most common error messages chart
        report_data["common_errors_chart"] = self._create_horizontal_bar_chart(
            [str(m['mensaje_short']) for m in common_errors],
            [m['count'] for m in common_errors],
            'Mensajes de Error comunes',
            'Cantidad'
        )


        # Files with most errors

        query = """ 
            SELECT archivo, COUNT(*) as count 
            FROM registros_error  
        """
        query += filtros_where

        query += """ 
            AND (archivo IS NOT NULL AND archivo != '')
            GROUP BY archivo 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        error_files = cursor.fetchall()
        error_files = error_files[::-1]
        report_data["error_files"] = error_files

        # Files with most chart
        report_data["error_files_chart"] = self._create_horizontal_bar_chart(
            [str(m['archivo']) for m in error_files],
            [m['count'] for m in error_files],
            'Archivos con mas errores',
            'Cantidad'
        )

        
        # Clients causing most errors
        query = """
            SELECT cliente, COUNT(*) as count 
            FROM registros_error  

        """
        query += filtros_where
        query += """ 
            AND (cliente IS NOT NULL AND cliente != '')
            GROUP BY cliente 
            ORDER BY count DESC 
            LIMIT 10 
        """
        cursor.execute(query, params)
        error_clients = cursor.fetchall()
        error_clients = error_clients[::-1]
        report_data["error_clients"] = error_clients
        
        # Clients causing most errors chart
        report_data["error_clients_chart"] = self._create_horizontal_bar_chart(
            [str(m['cliente']) for m in error_clients],
            [m['count'] for m in error_clients],
            'CLientes con mas errores',
            'Cantidad'
        )
        connection.close()
        return report_data


    def get_demas_graficos_ftp(self,texto,modo,desde,hasta):

        filtro_where = """
            WHERE (
                usuario LIKE %s
                OR ip LIKE %s
                OR accion LIKE %s
                OR archivo LIKE %s
                OR detalles LIKE %s
            )
        """
        params1 = ["'%success%'", "'%FAIL%'"]
        params=([f"%{texto}%"] * 5)

        if modo == "diario":
            hoy = datetime.now().date()
            desde = f"{hoy} 00:00:00"
            hasta = f"{hoy} 23:59:59"
            filtro_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "semanal":
            hoy = datetime.now()
            # Día de la semana: lunes=0, domingo=6
            dia_semana = hoy.weekday()
            
            lunes = hoy - timedelta(days=dia_semana)
            domingo = lunes + timedelta(days=6)

            desde = f"{lunes.date()} 00:00:00"
            hasta = f"{domingo.date()} 23:59:59"

            filtro_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
        elif modo == "mensual":
            hoy = datetime.now()
            anio = hoy.year
            mes = hoy.month
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

            filtro_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            filtro_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])
       

        connection = self.get_connection()
        cursor = connection.cursor()
        report_data = {}

        # Total events
        query = """
                SELECT COUNT(*) as total FROM registros_ftp 

                """
        query += filtro_where

        cursor.execute(query,params)
        report_data["total_events"] = cursor.fetchone()['total']
        
        # Events by action type

        query = """
            SELECT accion, COUNT(*) as count 
            FROM registros_ftp  
 
        """
        query += filtro_where
        query += """ 
            GROUP BY accion 
            ORDER BY count DESC
        """
        cursor.execute(query, params)
        actions = cursor.fetchall()
        report_data["events_by_action"] = actions
        
        # Action chart 
        report_data["action_chart"] = self._create_pie_chart(
            [a['accion'] for a in actions],
            [a['count'] for a in actions],
            'FTP Actions Distribution'
        )
        
        
       # Construir la consulta con placeholders
        query = """
            SELECT 
                SUM(CASE WHEN detalles LIKE 'OK%%' THEN 1 ELSE 0 END) AS successful_logins,
                SUM(CASE WHEN detalles LIKE 'FAIL%%' THEN 1 ELSE 0 END) AS failed_logins
            FROM registros_ftp
        """
        query += filtro_where
        query += """
            AND (accion = 'LOGIN' OR accion = 'LOGIN_FAILED')
        """

        # Definir los patrones como parámetros
        # Asume que `params` ya tiene tus parámetros previos del filtro
        cursor.execute(query, params)
        login_stats = cursor.fetchone()

       # Asegurar que login_stats no sea None y usar .get con fallback
        success = login_stats.get('successful_logins') or 0 if login_stats else 0
        fail = login_stats.get('failed_logins') or 0 if login_stats else 0

        # Guardar en el diccionario
        report_data["login_stats"] = {
            'successful_logins': success,
            'failed_logins': fail
        }

        # Solo crear gráfico si hay algún dato válido (>0)
        if success > 0 or fail > 0:
            report_data["login_stats_chart"] = self._create_pie_chart(
                ['Sesiones exitosas', 'Sesiones fallidas'],
                [success, fail],
                'Intentos de sesión exitosa vs fallida'
            )
        else:
            report_data["login_stats_chart"] = None  # o simplemente omitirlo




        # Most active users
        query = """
            SELECT usuario, COUNT(*) as count 
            FROM registros_ftp  

        """
        query += filtro_where
        query += """
            
            GROUP BY usuario 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query, params)
        active_users = cursor.fetchall()
        active_users = active_users[::-1]
        report_data["active_users"] = active_users
        # Most active users chart
        report_data["active_users_chart"] = self._create_horizontal_bar_chart(
            [str(m['usuario']) for m in active_users],
            [m['count'] for m in active_users],
            'Usuarios mas Activos',
            'Cantidad'
        )

        
        # Most active IPs
        query = """
            SELECT ip, COUNT(*) as count 
            FROM registros_ftp  

        """
        query += filtro_where
        query += """ 
 
            GROUP BY ip 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)

        active_ips = cursor.fetchall()
        active_ips = active_ips[::-1]
        report_data["active_ips"] = active_ips
        # Most active IPs chart
        report_data["active_ips_chart"] = self._create_horizontal_bar_chart(
            [str(m['ip']) for m in active_ips],
            [m['count'] for m in active_ips],
            'IPs mas Activas',
            'Cantidad'
        )

        # Most accessed files
        query = """
            SELECT archivo, COUNT(*) as count 
            FROM registros_ftp  
            
        """
        query += filtro_where
        query += """
            
            AND (archivo IS NOT NULL AND archivo != '')
            GROUP BY archivo 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        accessed_files = cursor.fetchall()
        accessed_files = accessed_files[::-1]
        report_data["accessed_files"] = accessed_files
        
         #  Most accessed files chart
        report_data["accessed_files_chart"] = self._create_horizontal_bar_chart(
            [str(m['archivo']) for m in accessed_files],
            [m['count'] for m in accessed_files],
            'Archivos mas Accedidos',
            'Cantidad'
        )
        connection.close()
        return report_data


    def get_demas_graficos_xfer(self,texto,modo,desde,hasta):
        

        filtros_where = """
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
            primer_dia = f"{anio}-01-01 00:00:00"
            # Último día del mes
            ultimo_dia_num = calendar.monthrange(anio, mes)[1]
            ultimo_dia = f"{anio}-12-31 23:59:59"

            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([primer_dia, ultimo_dia])
        elif modo == "rango" and desde and hasta:
            filtros_where += " AND fecha_hora BETWEEN %s AND %s"
            params.extend([desde, hasta])


        connection = self.get_connection()
        cursor = connection.cursor()
        report_data = {}
        
      
        # Total transfers
        query = """
            SELECT COUNT(*) as total FROM transferencias_ftp 

        """
        query+= filtros_where
        cursor.execute(query,params)
        report_data["total_transfers"] = cursor.fetchone()['total']
        
        # Upload vs Download counts
        query = """ 
            SELECT direccion, COUNT(*) as count 
            FROM transferencias_ftp  
        """

        query+= filtros_where
        query+= """ 
            GROUP BY direccion
        """
        cursor.execute(query,params)
        directions = cursor.fetchall()
        report_data["transfers_by_direction"] = directions
        
        # Direction chart
        report_data["direction_chart"] = self._create_pie_chart(
            [d['direccion'] for d in directions],
            [d['count'] for d in directions],
            'Distribucion de Direcciones'
        )
        
        
        # Transfer service types
        query = """
            SELECT servicio, COUNT(*) as count 
            FROM transferencias_ftp  

        """
        query += filtros_where
        query += """ 
            GROUP BY servicio 
            ORDER BY count DESC 
        """
        cursor.execute(query,params)
        services = cursor.fetchall()
        report_data["services"] = services
        # Transfer service types
        report_data["services_chart"] = self._create_pie_chart(
            [d['servicio'] for d in services],
            [d['count'] for d in services],
            'Servicios'
        )

        # Authentication methods
        query = """
            SELECT metodo_autenticacion, COUNT(*) as count 
            FROM transferencias_ftp  
        """
        query+= filtros_where
        query += """ 
            GROUP BY metodo_autenticacion 
            ORDER BY count DESC 
        """
        cursor.execute(query,params)
        auth_methods = cursor.fetchall()
        report_data["auth_methods"] = auth_methods

        # auth char
        report_data["auth_methods_chart"] = self._create_pie_chart(
            [d['metodo_autenticacion'] for d in auth_methods],
            [d['count'] for d in auth_methods],
            'Metodos de Autentificacion'
        )

        
        # Most active users
        query = """
            SELECT usuario, COUNT(*) as count 
            FROM transferencias_ftp  
             
        """
        query += filtros_where
        query += """ 
            GROUP BY usuario 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        active_users = cursor.fetchall()
        active_users = active_users[::-1]
        report_data["active_users"] = active_users

        report_data["active_users_chart"] = self._create_horizontal_bar_chart(
            [str(m['usuario']) for m in active_users],
            [m['count'] for m in active_users],
            'Usuarios mas activos',
            'Cantidad'
        )
        
        # Most active IPs
        query = """
            SELECT ip_remota, COUNT(*) as count 
            FROM transferencias_ftp  

        """
        query += filtros_where
        query += """  
            GROUP BY ip_remota 
            ORDER BY count DESC 
            LIMIT 10
        """
        cursor.execute(query,params)
        active_ips = cursor.fetchall()
        active_ips = active_ips[::-1]
        report_data["active_ips"] = active_ips

        #grap
        report_data["active_ips_chart"] = self._create_horizontal_bar_chart(
            [str(m['ip_remota']) for m in active_ips],
            [m['count'] for m in active_ips],
            'Usuarios mas activos',
            'Cantidad'
        )

        
        # Transfer size distribution
        query = """
            SELECT 
                CASE 
                    WHEN tamaño_archivo < 1024 THEN '< 1KB'
                    WHEN tamaño_archivo < 102400 THEN '1KB - 100KB'
                    WHEN tamaño_archivo < 1048576 THEN '100KB - 1MB'
                    WHEN tamaño_archivo < 10485760 THEN '1MB - 10MB'
                    ELSE '> 10MB' 
                END as size_range,
                COUNT(*) as count
            FROM transferencias_ftp
            
        """
        query += filtros_where
        query += """ 
            GROUP BY size_range
            ORDER BY 
                CASE size_range
                    WHEN '< 1KB' THEN 1
                    WHEN '1KB - 100KB' THEN 2
                    WHEN '100KB - 1MB' THEN 3
                    WHEN '1MB - 10MB' THEN 4
                    ELSE 5
                END
        """
        cursor.execute(query, params)
        size_ranges = cursor.fetchall()
        report_data["transfer_sizes"] = size_ranges
        
        # Size range chart
        report_data["size_chart"] = self._create_pie_chart(
            [r['size_range'] for r in size_ranges],
            [r['count'] for r in size_ranges],
            'Transfer Size Distribution'
        )
        
        # Total bytes transferred
        query = """
            SELECT 
                SUM(CASE WHEN direccion = 'IN' THEN tamaño_archivo ELSE 0 END) as total_upload_bytes,
                SUM(CASE WHEN direccion = 'OUT' THEN tamaño_archivo ELSE 0 END) as total_download_bytes,
                SUM(tamaño_archivo) as total_transfer_bytes
            FROM transferencias_ftp 

        """
        query += filtros_where
        cursor.execute(query,params)
        report_data["transfer_volume"] = cursor.fetchone()
        
        # Average transfer duration


        # Response time statistics
        query = """
            SELECT 
                AVG(duracion) as avg_time,
                MAX(duracion) as max_time,
                MIN(duracion) as min_time
            FROM transferencias_ftp 
        """
        query += filtros_where
        cursor.execute(query, params)
        report_data["avg_duration"] = cursor.fetchone()

        stats = report_data["avg_duration"]
        labels = ['Mínimo', 'Promedio', 'Máximo']
        values = [stats['min_time'], stats['avg_time'], stats['max_time']]

        # Reemplazar None por 0 (o puedes decidir omitir el gráfico)
        values = [v if v is not None else 0 for v in values]

        # Crear el gráfico solo si hay algún valor distinto de 0
        if any(values):
            report_data["avg_duration_chart"] = self._create_bar_chart(labels, values, 'Tiempos de transferencia', '', 'ms')
        else:
            report_data["avg_duration_chart"] = None  # O algún mensaje alternativo




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