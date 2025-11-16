#!/usr/bin/env python3
"""
QuestDB Checkpoint Helper
Executes CHECKPOINT CREATE/RELEASE commands via PostgreSQL protocol
"""

import sys
import os
import psycopg2

def execute_checkpoint(command):
    """Execute CHECKPOINT CREATE or RELEASE command"""
    try:
        host = os.getenv('QUESTDB_HOST', 'localhost')
        port = int(os.getenv('QUESTDB_PORT', '8812'))
        user = os.getenv('QUESTDB_USER', 'admin')
        password = os.getenv('QUESTDB_PASSWORD', 'quest')
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='qdb',
            connect_timeout=5
        )
        
        with conn.cursor() as cur:
            cur.execute(command)
            conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python backup_questdb_helper.py <CREATE|RELEASE>", file=sys.stderr)
        sys.exit(1)
    
    action = sys.argv[1].upper()
    if action == 'CREATE':
        command = 'CHECKPOINT CREATE;'
    elif action == 'RELEASE':
        command = 'CHECKPOINT RELEASE;'
    else:
        print(f"Invalid action: {action}. Use CREATE or RELEASE", file=sys.stderr)
        sys.exit(1)
    
    success = execute_checkpoint(command)
    sys.exit(0 if success else 1)

