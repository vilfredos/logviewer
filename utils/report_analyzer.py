import pymysql
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64
from typing import Dict, List, Any, Tuple, Optional

class ReportAnalyzer:
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
    
    def identify_active_table(self) -> Tuple[str, int]:
        """Identifies which table has data.
        
        Returns:
            tuple: (table_name, record_count)
        """
        tables = [
            'registros_acceso',
            'registros_error',
            'registros_ftp',
            'transferencias_ftp'
        ]
        
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    if result and result['count'] > 0:
                        return table, result['count']
                
                # If no tables have data
                return None, 0
        finally:
            connection.close()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generates statistics based on the active table.
        
        Returns:
            Dict containing report data and type
        """
        active_table, count = self.identify_active_table()
        
        if not active_table:
            return {"type": "none", "message": "No data found in any table"}
        
        if active_table == 'registros_acceso':
            return self._generate_apache_report()
        elif active_table == 'registros_error':
            return self._generate_apache_error_report()
        elif active_table == 'registros_ftp':
            return self._generate_ftp_events_report()
        elif active_table == 'transferencias_ftp':
            return self._generate_ftp_transfers_report()
    
    def _generate_apache_report(self) -> Dict[str, Any]:
        """Generates statistics from Apache access logs."""
        connection = self.get_connection()
        report_data = {"type": "apache_access"}
        
        try:
            with connection.cursor() as cursor:
                # Total requests
                cursor.execute("SELECT COUNT(*) as total FROM registros_acceso")
                report_data["total_requests"] = cursor.fetchone()['total']
                
                # Requests per day (historico)
                cursor.execute("""
                    SELECT DATE(fecha_hora) as date, COUNT(*) as count 
                    FROM registros_acceso 
                    GROUP BY DATE(fecha_hora)
                    ORDER BY date     
                """)
                requests_by_day = cursor.fetchall()
                report_data["requests_by_day"] = requests_by_day
                
                # Visualize requests by day
                report_data["requests_by_day_chart"] = self._create_bar_chart(
                    [day['date'].strftime('%Y-%m-%d') for day in requests_by_day],
                    [day['count'] for day in requests_by_day],
                    'Requests by Day', 'Date', 'Count'
                )
                
                # Popular pages
                cursor.execute("""
                    SELECT ruta, COUNT(*) as count 
                    FROM registros_acceso 
                    GROUP BY ruta 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["popular_pages"] = cursor.fetchall()
                
                # HTTP methods distribution
                cursor.execute("""
                    SELECT metodo, COUNT(*) as count 
                    FROM registros_acceso 
                    GROUP BY metodo 
                    ORDER BY count DESC
                """)
                methods = cursor.fetchall()
                report_data["http_methods"] = methods
                
                # Method distribution chart
                report_data["http_methods_chart"] = self._create_pie_chart(
                    [m['metodo'] for m in methods],
                    [m['count'] for m in methods],
                    'HTTP Methods Distribution'
                )
                
                # Response codes distribution
                cursor.execute("""
                    SELECT codigo_estado, COUNT(*) as count 
                    FROM registros_acceso 
                    GROUP BY codigo_estado 
                    ORDER BY count DESC
                """)
                report_data["status_codes"] = cursor.fetchall()
                
                # Top referring sites
                cursor.execute("""
                    SELECT referer, COUNT(*) as count 
                    FROM registros_acceso 
                    WHERE referer != '' AND referer IS NOT NULL
                    GROUP BY referer 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["top_referrers"] = cursor.fetchall()
                
                # Top user agents
                cursor.execute("""
                    SELECT user_agent, COUNT(*) as count 
                    FROM registros_acceso 
                    GROUP BY user_agent 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["top_user_agents"] = cursor.fetchall()
                
                # Request size distribution
                cursor.execute("""
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
                    GROUP BY size_range
                    ORDER BY 
                        CASE size_range
                            WHEN '< 1KB' THEN 1
                            WHEN '1KB - 10KB' THEN 2
                            WHEN '10KB - 100KB' THEN 3
                            WHEN '100KB - 1MB' THEN 4
                            ELSE 5
                        END
                """)
                size_ranges = cursor.fetchall()
                report_data["response_sizes"] = size_ranges
                
                # Response size chart
                report_data["response_sizes_chart"] = self._create_pie_chart(
                    [r['size_range'] for r in size_ranges],
                    [r['count'] for r in size_ranges],
                    'Response Size Distribution'
                )
                
                # Top IPs
                cursor.execute("""
                    SELECT ip, COUNT(*) as count 
                    FROM registros_acceso 
                    GROUP BY ip 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["top_ips"] = cursor.fetchall()
                
                # Response time statistics
                cursor.execute("""
                    SELECT 
                        AVG(tiempo_respuesta) as avg_time,
                        MAX(tiempo_respuesta) as max_time,
                        MIN(tiempo_respuesta) as min_time
                    FROM registros_acceso
                """)
                report_data["response_time_stats"] = cursor.fetchone()
                
                return report_data
        finally:
            connection.close()
    
    def _generate_apache_error_report(self) -> Dict[str, Any]:
        """Generates statistics from Apache error logs."""
        connection = self.get_connection()
        report_data = {"type": "apache_error"}
        
        try:
            with connection.cursor() as cursor:
                # Total errors
                cursor.execute("SELECT COUNT(*) as total FROM registros_error")
                report_data["total_errors"] = cursor.fetchone()['total']
                
                # Errors by severity level
                cursor.execute("""
                    SELECT nivel_error, COUNT(*) as count 
                    FROM registros_error 
                    GROUP BY nivel_error 
                    ORDER BY count DESC
                """)
                errors_by_level = cursor.fetchall()
                report_data["errors_by_level"] = errors_by_level
                
                # Error level chart
                report_data["error_level_chart"] = self._create_pie_chart(
                    [e['nivel_error'] for e in errors_by_level],
                    [e['count'] for e in errors_by_level],
                    'Error Level Distribution'
                )
                
                # Errors over time (historico)
                cursor.execute("""
                    SELECT DATE(fecha_hora) as date, COUNT(*) as count 
                    FROM registros_error 
                    GROUP BY DATE(fecha_hora)
                    ORDER BY date
                """)
                errors_by_day = cursor.fetchall()
                report_data["errors_by_day"] = errors_by_day
                
                # Error by day chart
                report_data["errors_by_day_chart"] = self._create_bar_chart(
                    [day['date'].strftime('%Y-%m-%d') for day in errors_by_day],
                    [day['count'] for day in errors_by_day],
                    'Errors by Day', 'Date', 'Count'
                )
                
                # Most common error messages
                cursor.execute("""
                    SELECT LEFT(mensaje, 100) as mensaje_short, COUNT(*) as count 
                    FROM registros_error 
                    GROUP BY mensaje_short 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["common_errors"] = cursor.fetchall()
                
                # Files with most errors
                cursor.execute("""
                    SELECT archivo, COUNT(*) as count 
                    FROM registros_error 
                    WHERE archivo IS NOT NULL AND archivo != ''
                    GROUP BY archivo 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["error_files"] = cursor.fetchall()
                
                # Clients causing most errors
                cursor.execute("""
                    SELECT cliente, COUNT(*) as count 
                    FROM registros_error 
                    WHERE cliente IS NOT NULL AND cliente != ''
                    GROUP BY cliente 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["error_clients"] = cursor.fetchall()
                
                return report_data
        finally:
            connection.close()
    
    def _generate_ftp_events_report(self) -> Dict[str, Any]:
        """Generates statistics from FTP event logs."""
        connection = self.get_connection()
        report_data = {"type": "ftp_events"}
        
        try:
            with connection.cursor() as cursor:
                # Total events
                cursor.execute("SELECT COUNT(*) as total FROM registros_ftp")
                report_data["total_events"] = cursor.fetchone()['total']
                
                # Events by action type
                cursor.execute("""
                    SELECT accion, COUNT(*) as count 
                    FROM registros_ftp 
                    GROUP BY accion 
                    ORDER BY count DESC
                """)
                actions = cursor.fetchall()
                report_data["events_by_action"] = actions
                
                # Action chart 
                report_data["action_chart"] = self._create_pie_chart(
                    [a['accion'] for a in actions],
                    [a['count'] for a in actions],
                    'FTP Actions Distribution'
                )
                
                # Events over time (historico)
                cursor.execute("""
                    SELECT DATE(fecha_hora) as date, COUNT(*) as count 
                    FROM registros_ftp 
                    GROUP BY DATE(fecha_hora)
                    ORDER BY date
                """)
                events_by_day = cursor.fetchall()
                report_data["events_by_day"] = events_by_day
                
                # Events by day chart
                report_data["events_by_day_chart"] = self._create_bar_chart(
                    [day['date'].strftime('%Y-%m-%d') for day in events_by_day],
                    [day['count'] for day in events_by_day],
                    'FTP Events by Day', 'Date', 'Count'
                )
                
                # Login success/failure counts
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN detalles LIKE '%success%' THEN 1 ELSE 0 END) as successful_logins,
                        SUM(CASE WHEN detalles LIKE '%FAIL%' OR detalles LIKE '%FAIL%' THEN 1 ELSE 0 END) as failed_logins
                    FROM registros_ftp
                    WHERE accion = 'LOGIN'
                """)
                report_data["login_stats"] = cursor.fetchone()
                
                # Most active users
                cursor.execute("""
                    SELECT usuario, COUNT(*) as count 
                    FROM registros_ftp 
                    GROUP BY usuario 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["active_users"] = cursor.fetchall()
                
                # Most active IPs
                cursor.execute("""
                    SELECT ip, COUNT(*) as count 
                    FROM registros_ftp 
                    GROUP BY ip 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["active_ips"] = cursor.fetchall()
                
                # Most accessed files
                cursor.execute("""
                    SELECT archivo, COUNT(*) as count 
                    FROM registros_ftp 
                    WHERE archivo IS NOT NULL AND archivo != ''
                    GROUP BY archivo 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["accessed_files"] = cursor.fetchall()
                
                return report_data
        finally:
            connection.close()
    
    def _generate_ftp_transfers_report(self) -> Dict[str, Any]:
        """Generates statistics from FTP transfer logs."""
        connection = self.get_connection()
        report_data = {"type": "ftp_transfers"}
        
        try:
            with connection.cursor() as cursor:
                # Total transfers
                cursor.execute("SELECT COUNT(*) as total FROM transferencias_ftp")
                report_data["total_transfers"] = cursor.fetchone()['total']
                
                # Upload vs Download counts
                cursor.execute("""
                    SELECT direccion, COUNT(*) as count 
                    FROM transferencias_ftp 
                    GROUP BY direccion
                """)
                directions = cursor.fetchall()
                report_data["transfers_by_direction"] = directions
                
                # Direction chart
                report_data["direction_chart"] = self._create_pie_chart(
                    [d['direccion'] for d in directions],
                    [d['count'] for d in directions],
                    'Transfer Direction Distribution'
                )
                
                # Transfers over time (last 7 days)
                cursor.execute("""
                    SELECT DATE(fecha_hora) as date, COUNT(*) as count 
                    FROM transferencias_ftp
                    GROUP BY DATE(fecha_hora)
                    ORDER BY date
                """)
                transfers_by_day = cursor.fetchall()
                report_data["transfers_by_day"] = transfers_by_day
                
                # Transfers chart
                report_data["transfers_by_day_chart"] = self._create_bar_chart(
                    [day['date'].strftime('%Y-%m-%d') for day in transfers_by_day],
                    [day['count'] for day in transfers_by_day],
                    'FTP Transfers by Day', 'Date', 'Count'
                )
                
                # Transfer service types
                cursor.execute("""
                    SELECT servicio, COUNT(*) as count 
                    FROM transferencias_ftp 
                    GROUP BY servicio 
                    ORDER BY count DESC
                """)
                report_data["services"] = cursor.fetchall()
                
                # Authentication methods
                cursor.execute("""
                    SELECT metodo_autenticacion, COUNT(*) as count 
                    FROM transferencias_ftp 
                    GROUP BY metodo_autenticacion 
                    ORDER BY count DESC
                """)
                report_data["auth_methods"] = cursor.fetchall()
                
                # Most active users
                cursor.execute("""
                    SELECT usuario, COUNT(*) as count 
                    FROM transferencias_ftp 
                    GROUP BY usuario 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["active_users"] = cursor.fetchall()
                
                # Most active IPs
                cursor.execute("""
                    SELECT ip_remota, COUNT(*) as count 
                    FROM transferencias_ftp 
                    GROUP BY ip_remota 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                report_data["active_ips"] = cursor.fetchall()
                
                # Transfer size distribution
                cursor.execute("""
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
                    GROUP BY size_range
                    ORDER BY 
                        CASE size_range
                            WHEN '< 1KB' THEN 1
                            WHEN '1KB - 100KB' THEN 2
                            WHEN '100KB - 1MB' THEN 3
                            WHEN '1MB - 10MB' THEN 4
                            ELSE 5
                        END
                """)
                size_ranges = cursor.fetchall()
                report_data["transfer_sizes"] = size_ranges
                
                # Size range chart
                report_data["size_chart"] = self._create_pie_chart(
                    [r['size_range'] for r in size_ranges],
                    [r['count'] for r in size_ranges],
                    'Transfer Size Distribution'
                )
                
                # Total bytes transferred
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN direccion = 'IN' THEN tamaño_archivo ELSE 0 END) as total_upload_bytes,
                        SUM(CASE WHEN direccion = 'OUT' THEN tamaño_archivo ELSE 0 END) as total_download_bytes,
                        SUM(tamaño_archivo) as total_transfer_bytes
                    FROM transferencias_ftp
                """)
                report_data["transfer_volume"] = cursor.fetchone()
                
                # Average transfer duration
                cursor.execute("SELECT AVG(duracion) as avg_duration FROM transferencias_ftp")
                report_data["avg_duration"] = cursor.fetchone()['avg_duration']
                
                return report_data
        finally:
            connection.close()
    
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