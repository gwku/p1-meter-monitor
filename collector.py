#!/usr/bin/env python3
"""
P1 Meter Data Collector
Fetches data from P1 API and stores in QuestDB
"""

import os
import logging
import requests
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class P1Collector:
    """Collects P1 meter data and stores in QuestDB"""
    
    def __init__(self):
        self.api_url = os.getenv('P1_API_URL', 'http://192.168.178.43/api/v1/data')
        self.questdb_host = os.getenv('QUESTDB_HOST', 'localhost')
        self.questdb_port = int(os.getenv('QUESTDB_PORT', '8812'))
        self.questdb_user = os.getenv('QUESTDB_USER', 'admin')
        self.questdb_password = os.getenv('QUESTDB_PASSWORD', 'quest')
        
        # Initialize database on first run
        self._init_database()
    
    def _get_db_connection(self):
        """Get QuestDB connection via PostgreSQL protocol"""
        try:
            conn = psycopg2.connect(
                host=self.questdb_host,
                port=self.questdb_port,
                user=self.questdb_user,
                password=self.questdb_password,
                database='qdb',
                connect_timeout=10
            )
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    
    def _init_database(self):
        """Initialize database table if it doesn't exist"""
        conn = self._get_db_connection()
        if not conn:
            logger.warning("Cannot initialize database - no connection")
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS p1_meter_data (
                        timestamp TIMESTAMP,
                        total_power_import_kwh DOUBLE,
                        total_power_import_t1_kwh DOUBLE,
                        total_power_import_t2_kwh DOUBLE,
                        total_power_export_kwh DOUBLE,
                        total_power_export_t1_kwh DOUBLE,
                        total_power_export_t2_kwh DOUBLE,
                        active_power_w DOUBLE,
                        active_power_l1_w DOUBLE,
                        active_power_l2_w DOUBLE,
                        active_power_l3_w DOUBLE,
                        total_gas_m3 DOUBLE,
                        gas_timestamp LONG,
                        meter_model SYMBOL,
                        unique_id SYMBOL
                    ) timestamp(timestamp) PARTITION BY DAY WAL;
                """)
                conn.commit()
                logger.info("✓ Database table initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
        finally:
            conn.close()
    
    def collect(self):
        """Fetch data from P1 API and store in QuestDB"""
        try:
            # Fetch from P1 API
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract values
            timestamp = datetime.utcnow()
            
            values = {
                'timestamp': timestamp,
                'total_power_import_kwh': data.get('total_power_import_kwh', 0),
                'total_power_import_t1_kwh': data.get('total_power_import_t1_kwh', 0),
                'total_power_import_t2_kwh': data.get('total_power_import_t2_kwh', 0),
                'total_power_export_kwh': data.get('total_power_export_kwh', 0),
                'total_power_export_t1_kwh': data.get('total_power_export_t1_kwh', 0),
                'total_power_export_t2_kwh': data.get('total_power_export_t2_kwh', 0),
                'active_power_w': data.get('active_power_w', 0),
                'active_power_l1_w': data.get('active_power_l1_w', 0),
                'active_power_l2_w': data.get('active_power_l2_w', 0),
                'active_power_l3_w': data.get('active_power_l3_w', 0),
                'total_gas_m3': data.get('total_gas_m3', 0),
                'gas_timestamp': data.get('gas_timestamp', 0),
                'meter_model': data.get('meter_model', 'Unknown'),
                'unique_id': data.get('unique_id', 'Unknown')
            }
            
            # Store in QuestDB
            conn = self._get_db_connection()
            if not conn:
                logger.error("Cannot store data - no database connection")
                return
            
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO p1_meter_data VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, tuple(values.values()))
                    conn.commit()
                    
                logger.info(
                    f"✓ Data stored | Power: {values['active_power_w']:.0f}W | "
                    f"Import: {values['total_power_import_kwh']:.3f} kWh | "
                    f"Gas: {values['total_gas_m3']:.3f} m³"
                )
            finally:
                conn.close()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to fetch from P1 API: {e}")
        except Exception as e:
            logger.error(f"✗ Collection failed: {e}")

