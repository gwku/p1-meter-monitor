#!/usr/bin/env python3
"""
P1 Meter Monitor - Automated Data Collection and Reporting
"""

import os
import sys
import time
import logging
from datetime import datetime
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from collector import P1Collector
from reporter import P1Reporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/p1-meter-monitor.log')
    ]
)

logger = logging.getLogger(__name__)


class P1Monitor:
    """Main application for P1 meter monitoring"""
    
    def __init__(self):
        self.collector = P1Collector()
        self.reporter = P1Reporter()
        self.scheduler = BackgroundScheduler()
        
    def start(self):
        """Start the monitoring system"""
        logger.info("=" * 70)
        logger.info("P1 Meter Monitor Starting")
        logger.info("=" * 70)
        
        # Schedule data collection (every minute)
        collection_interval = int(os.getenv('COLLECTION_INTERVAL', '60'))
        self.scheduler.add_job(
            self.collector.collect,
            'interval',
            seconds=collection_interval,
            id='data_collection',
            name='Collect P1 meter data'
        )
        logger.info(f"✓ Data collection scheduled every {collection_interval}s")
        
        # Schedule monthly report (1st of month at 00:00 AM)
        if os.getenv('ENABLE_MONTHLY_REPORT', 'true').lower() == 'true':
            self.scheduler.add_job(
                self.reporter.send_monthly_report,
                CronTrigger(day=1, hour=0, minute=0),
                id='monthly_report',
                name='Send monthly report'
            )
            logger.info("✓ Monthly report scheduled (1st of month at 9:00 AM)")
        
        # Schedule weekly export (Mondays at 00:00 AM) - optional
        if os.getenv('ENABLE_WEEKLY_EXPORT', 'false').lower() == 'true':
            self.scheduler.add_job(
                self.reporter.export_weekly_csv,
                CronTrigger(day_of_week='mon', hour=0, minute=0),
                id='weekly_export',
                name='Weekly CSV export'
            )
            logger.info("✓ Weekly export scheduled (Mondays at 8:00 AM)")
        
        # Start scheduler
        self.scheduler.start()
        logger.info("=" * 70)
        logger.info("System running. Press Ctrl+C to stop.")
        logger.info("=" * 70)
        
        # Run initial collection after startup delay
        time.sleep(10)
        logger.info("Running initial data collection...")
        self.collector.collect()
        
        # Keep the application running
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
            self.scheduler.shutdown()


if __name__ == '__main__':
    monitor = P1Monitor()
    monitor.start()

