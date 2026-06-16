#!/usr/bin/env python3
"""
P1 Meter Reporter
Generates reports and sends emails
"""

import os
import logging
import csv
import base64
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .email_sender import EmailSender
from .templates import generate_monthly_html

logger = logging.getLogger(__name__)


class P1Reporter:
    """Generates reports and sends emails"""
    
    def __init__(self):
        self.questdb_host = os.getenv('QUESTDB_HOST', 'localhost')
        self.questdb_port = int(os.getenv('QUESTDB_PORT', '8812'))
        self.questdb_user = os.getenv('QUESTDB_USER', 'admin')
        self.questdb_password = os.getenv('QUESTDB_PASSWORD', 'quest')
        self.api_url = os.getenv('P1_API_URL', 'http://192.168.1.123/api/v1/data')
        
        self.email_sender = EmailSender()
    
    def _get_db_connection(self):
        """Get QuestDB connection"""
        conn = psycopg2.connect(
            host=self.questdb_host,
            port=self.questdb_port,
            user=self.questdb_user,
            password=self.questdb_password,
            database='qdb'
        )
        return conn
    
    def _get_live_data(self):
        """Fetch live data from P1 API"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch live data: {e}")
            return {}
    
    def get_period_stats(self, start_date, end_date):
        """Get statistics for a specific period"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        count(*) as total_records,
                        min(timestamp) as period_start,
                        max(timestamp) as period_end,
                        round((last(total_power_import_kwh) - first(total_power_import_kwh))::decimal, 2) as electricity_consumed,
                        round((last(total_power_import_t1_kwh) - first(total_power_import_t1_kwh))::decimal, 2) as consumed_t1,
                        round((last(total_power_import_t2_kwh) - first(total_power_import_t2_kwh))::decimal, 2) as consumed_t2,
                        round((last(total_power_export_kwh) - first(total_power_export_kwh))::decimal, 2) as electricity_produced,
                        round((last(total_gas_m3) - first(total_gas_m3))::decimal, 2) as gas_consumed,
                        round(avg(active_power_w)::decimal, 0) as avg_power,
                        round(max(active_power_w)::decimal, 0) as peak_power,
                        last(meter_model) as meter_model,
                        last(unique_id) as unique_id
                    FROM p1_meter_data
                    WHERE timestamp >= %s AND timestamp < %s
                """, (start_date, end_date))
                return cur.fetchone()
        finally:
            conn.close()
    
    def get_monthly_stats(self):
        """Get monthly statistics from database (last complete month)"""
        # Calculate last month boundaries
        now = datetime.now()
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = first_of_this_month
        last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
        
        return self.get_period_stats(last_month_start, last_month_end)
    
    def get_previous_month_stats(self, current_month_start):
        """Get statistics for the month before the given month"""
        # Calculate previous month boundaries
        prev_month_end = current_month_start
        prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        return self.get_period_stats(prev_month_start, prev_month_end)
    
    def get_yearly_monthly_totals(self, year=None):
        """Get monthly totals for a given year (default: current year)"""
        if year is None:
            year = datetime.now().year
        
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get data for the entire year
                year_start = datetime(year, 1, 1)
                year_end = datetime(year + 1, 1, 1)
                
                # Query to get monthly totals using SAMPLE BY
                cur.execute("""
                    SELECT 
                        timestamp,
                        round((last(total_power_import_kwh) - first(total_power_import_kwh))::decimal, 2) as electricity_consumed,
                        round((last(total_power_import_t1_kwh) - first(total_power_import_t1_kwh))::decimal, 2) as consumed_t1,
                        round((last(total_power_import_t2_kwh) - first(total_power_import_t2_kwh))::decimal, 2) as consumed_t2,
                        round((last(total_power_export_kwh) - first(total_power_export_kwh))::decimal, 2) as electricity_produced,
                        round((last(total_gas_m3) - first(total_gas_m3))::decimal, 2) as gas_consumed
                    FROM p1_meter_data
                    WHERE timestamp >= %s AND timestamp < %s
                    SAMPLE BY 1M
                    ORDER BY timestamp ASC
                """, (year_start, year_end))
                
                rows = cur.fetchall()
                return rows if rows else []
        except Exception as e:
            logger.warning(f"Error getting yearly monthly totals with SAMPLE BY: {e}")
            # Fallback: manually calculate monthly totals
            return self._get_yearly_monthly_totals_fallback(year)
        finally:
            conn.close()
    
    def _get_yearly_monthly_totals_fallback(self, year):
        """Fallback method to calculate monthly totals manually"""
        monthly_totals = []
        for month in range(1, 13):
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1)
            else:
                month_end = datetime(year, month + 1, 1)
            
            stats = self.get_period_stats(month_start, month_end)
            if stats and stats.get('total_records', 0) > 0:
                monthly_totals.append({
                    'timestamp': month_start,
                    'electricity_consumed': stats.get('electricity_consumed', 0),
                    'consumed_t1': stats.get('consumed_t1', 0),
                    'consumed_t2': stats.get('consumed_t2', 0),
                    'electricity_produced': stats.get('electricity_produced', 0),
                    'gas_consumed': stats.get('gas_consumed', 0)
                })
        
        return monthly_totals
    
    def get_period_data(self, start_date, end_date):
        """Get raw data for a specific period (for graphing)"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT timestamp, active_power_w, total_power_import_kwh, total_power_export_kwh, total_gas_m3
                    FROM p1_meter_data
                    WHERE timestamp >= %s AND timestamp < %s
                    ORDER BY timestamp ASC
                """, (start_date, end_date))
                
                rows = cur.fetchall()
                return rows if rows else None
        finally:
            conn.close()
    
    def generate_period_graph(self, start_date, end_date):
        """Generate a graph image for the period and return as base64 string"""
        data = self.get_period_data(start_date, end_date)
        if not data or len(data) < 2:
            return None
        
        # Extract data
        timestamps = [row['timestamp'] for row in data]
        power_w = [row['active_power_w'] or 0 for row in data]
        import_kwh = [row['total_power_import_kwh'] or 0 for row in data]
        export_kwh = [row['total_power_export_kwh'] or 0 for row in data]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        fig.patch.set_facecolor('white')
        
        # Plot 1: Power consumption over time
        ax1.plot(timestamps, power_w, linewidth=1.5, color='#2c5aa0', alpha=0.7)
        ax1.fill_between(timestamps, power_w, alpha=0.3, color='#2c5aa0')
        ax1.set_ylabel('Vermogen (W)', fontsize=11, fontweight='bold')
        ax1.set_title('Actief Vermogen Over Tijd', fontsize=13, fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_facecolor('#f8f9fa')
        
        # Format x-axis dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(timestamps) // 10)))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Plot 2: Cumulative import/export
        ax2.plot(timestamps, import_kwh, linewidth=2, color='#d32f2f', label='Import (kWh)', alpha=0.8)
        ax2.plot(timestamps, export_kwh, linewidth=2, color='#388e3c', label='Export (kWh)', alpha=0.8)
        ax2.set_xlabel('Datum', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Cumulatief (kWh)', fontsize=11, fontweight='bold')
        ax2.set_title('Cumulatieve Elektriciteit Import/Export', fontsize=13, fontweight='bold', pad=15)
        ax2.legend(loc='upper left', framealpha=0.9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.set_facecolor('#f8f9fa')
        
        # Format x-axis dates
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(timestamps) // 10)))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        plt.close(fig)
        
        return img_base64
    
    def generate_yearly_graph(self, year=None):
        """Generate a graph showing monthly totals for the year"""
        if year is None:
            year = datetime.now().year
        
        monthly_data = self.get_yearly_monthly_totals(year)
        if not monthly_data or len(monthly_data) < 1:
            return None
        
        # Extract data
        months = [row['timestamp'] for row in monthly_data]
        electricity_consumed = [row['electricity_consumed'] or 0 for row in monthly_data]
        electricity_produced = [row['electricity_produced'] or 0 for row in monthly_data]
        gas_consumed = [row['gas_consumed'] or 0 for row in monthly_data]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        fig.patch.set_facecolor('white')
        
        # Plot 1: Monthly electricity consumption and production
        x_pos = range(len(months))
        width = 0.35
        
        ax1.bar([x - width/2 for x in x_pos], electricity_consumed, width, 
                label='Verbruik (kWh)', color='#d32f2f', alpha=0.8)
        ax1.bar([x + width/2 for x in x_pos], electricity_produced, width,
                label='Productie (kWh)', color='#388e3c', alpha=0.8)
        
        ax1.set_ylabel('Elektriciteit (kWh)', fontsize=11, fontweight='bold')
        ax1.set_title(f'Maandelijks Elektriciteit Verbruik & Productie - {year}', 
                     fontsize=13, fontweight='bold', pad=15)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels([m.strftime('%b') for m in months], rotation=45, ha='right')
        ax1.legend(loc='upper left', framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax1.set_facecolor('#f8f9fa')
        
        # Plot 2: Monthly gas consumption
        ax2.bar(x_pos, gas_consumed, width=0.6, color='#ff9800', alpha=0.8)
        ax2.set_xlabel('Maand', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Gas (m³)', fontsize=11, fontweight='bold')
        ax2.set_title(f'Maandelijks Gas Verbruik - {year}', 
                     fontsize=13, fontweight='bold', pad=15)
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels([m.strftime('%b') for m in months], rotation=45, ha='right')
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax2.set_facecolor('#f8f9fa')
        
        # Add value labels on bars
        for i, (elec, gas) in enumerate(zip(electricity_consumed, gas_consumed)):
            if elec > 0:
                ax1.text(i - width/2, elec, f'{elec:.0f}', 
                        ha='center', va='bottom', fontsize=8)
            if gas > 0:
                ax2.text(i, gas, f'{gas:.1f}', 
                        ha='center', va='bottom', fontsize=8)
        
        # Adjust layout
        plt.tight_layout()
        
        # Convert to base64
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        plt.close(fig)
        
        return img_base64
    
    def export_period_csv(self, start_date, end_date):
        """Export data for a specific period to CSV"""
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM p1_meter_data
                    WHERE timestamp >= %s AND timestamp < %s
                    ORDER BY timestamp ASC
                """, (start_date, end_date))
                
                rows = cur.fetchall()
                if not rows:
                    return None
                
                # Convert to CSV
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                
                return output.getvalue()
        finally:
            conn.close()
    
    def export_monthly_csv(self):
        """Export monthly data to CSV (last complete month)"""
        now = datetime.now()
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = first_of_this_month
        last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
        
        return self.export_period_csv(last_month_start, last_month_end)
    
    def export_weekly_csv(self):
        """Export weekly CSV to file"""
        try:
            conn = self._get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM p1_meter_data
                    WHERE timestamp > dateadd('d', -7, now())
                    ORDER BY timestamp ASC
                """)
                
                rows = cur.fetchall()
                if rows:
                    filename = f"/output/p1_export_week_{datetime.now().strftime('%Y%m%d')}.csv"
                    os.makedirs('/output', exist_ok=True)
                    
                    with open(filename, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                    
                    logger.info(f"✓ Weekly CSV exported: {filename}")
            conn.close()
        except Exception as e:
            logger.error(f"Weekly CSV export failed: {e}")
    
    def send_period_report(self, start_date, end_date, period_name=None):
        """Send email report for a specific period"""
        logger.info("=" * 70)
        logger.info(f"Generating report: {start_date.date()} to {end_date.date()}")
        logger.info("=" * 70)
        
        try:
            # Get statistics
            stats = self.get_period_stats(start_date, end_date)
            if not stats or stats['total_records'] == 0:
                logger.warning(f"No data available for period {start_date.date()} to {end_date.date()}")
                return False
            
            # Determine if this is a monthly report or custom period
            # Monthly report: starts on day 1 and ends on day 1 of next month (full month)
            is_monthly = (start_date.day == 1 and end_date.day == 1 and 
                         start_date.month != end_date.month and
                         (end_date - start_date).days <= 32)
            
            # Show comparison for monthly reports OR periods starting on day 1 (like "this-month")
            show_comparison = is_monthly or (start_date.day == 1 and start_date.month == end_date.month)
            
            # Get previous month stats for comparison
            prev_month_stats = None
            if show_comparison:
                # This is a monthly report, get previous month for comparison
                try:
                    prev_month_stats = self.get_previous_month_stats(start_date)
                    # Keep prev_month_stats even if 0 records, so template can show "no data" message
                except Exception as e:
                    logger.warning(f"Could not get previous month stats: {e}")
                    prev_month_stats = None
            
            # Get live data
            live_data = self._get_live_data()
            
            # Generate period graph (always - shows the period's data)
            logger.info("Generating period graph...")
            graph_image = None
            try:
                graph_image = self.generate_period_graph(start_date, end_date)
                if graph_image:
                    logger.info("✓ Period graph generated successfully")
                else:
                    logger.warning("No period graph generated (insufficient data)")
            except Exception as e:
                logger.warning(f"Period graph generation failed: {e}")
            
            # Generate yearly graph (for full monthly reports OR periods starting on day 1 like "this-month")
            yearly_graph_image = None
            if is_monthly or show_comparison:
                logger.info("Generating yearly graph...")
                try:
                    yearly_graph_image = self.generate_yearly_graph()
                    if yearly_graph_image:
                        logger.info("✓ Yearly graph generated successfully")
                    else:
                        logger.warning("No yearly graph generated (insufficient data)")
                except Exception as e:
                    logger.warning(f"Yearly graph generation failed: {e}")
            
            # Generate HTML email
            # Use show_comparison for template (shows comparison for monthly reports and "this-month" type periods)
            html_content = generate_monthly_html(
                stats, live_data, 
                graph_image=graph_image,
                yearly_graph_image=yearly_graph_image,
                prev_month_stats=prev_month_stats,
                is_monthly=show_comparison
            )
            
            # Generate CSV
            csv_content = self.export_period_csv(start_date, end_date)
            
            # Determine period name and report type
            if period_name:
                # For monthly reports, use just the month name without "(tot nu)" suffix
                if (is_monthly or show_comparison) and start_date.month == end_date.month:
                    display_name = start_date.strftime('%B %Y')
                else:
                    display_name = period_name
            elif start_date.month == end_date.month and start_date.day == 1 and (end_date - start_date).days <= 32:
                display_name = start_date.strftime('%B %Y')
            else:
                display_name = f"{start_date.strftime('%d-%m-%Y')} tot {end_date.strftime('%d-%m-%Y')}"
            
            # Determine report title/type
            # Show "Maandoverzicht" for full monthly reports OR periods starting on day 1 (like "this-month")
            report_title = "Maandoverzicht" if (is_monthly or show_comparison) else "Rapport"
            report_type = "maandoverzicht" if (is_monthly or show_comparison) else "rapport"
            
            # Regenerate HTML with correct title
            html_content = generate_monthly_html(
                stats, live_data, 
                graph_image=graph_image,
                yearly_graph_image=yearly_graph_image,
                prev_month_stats=prev_month_stats,
                report_title=report_title,
                report_type=report_type,
                is_monthly=is_monthly
            )
            
            # Send email
            subject = f"P1 Meter {report_title} - {display_name}"
            csv_filename = f"p1_meter_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            
            success = self.email_sender.send_email(
                subject=subject,
                html_content=html_content,
                csv_content=csv_content,
                csv_filename=csv_filename
            )
            
            if success:
                logger.info(f"✓ Report sent successfully for {display_name}")
                return True
            else:
                logger.error("✗ Failed to send report")
                return False
                
        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            return False
    
    def send_monthly_report(self):
        """Send monthly email report (last complete month)"""
        now = datetime.now()
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = first_of_this_month
        last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
        
        month_name = last_month_start.strftime('%B %Y')
        # This will automatically use "Maandoverzicht" since it's a monthly report
        return self.send_period_report(last_month_start, last_month_end, month_name)


def calculate_period(period):
    """Calculate start and end dates for a period preset"""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == 'today':
        return today, now, 'Vandaag'
    
    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, today, 'Gisteren'
    
    elif period == 'week':
        # Last 7 days
        week_start = today - timedelta(days=7)
        return week_start, now, 'Afgelopen 7 dagen'
    
    elif period == 'this-week':
        # Current week (Monday to now)
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        return week_start, now, 'Deze week'
    
    elif period == 'last-week':
        # Previous week (Monday to Sunday)
        days_since_monday = today.weekday()
        last_sunday = today - timedelta(days=days_since_monday + 1)
        last_monday = last_sunday - timedelta(days=6)
        return last_monday, last_sunday + timedelta(days=1), 'Vorige week'
    
    elif period == 'month':
        # Last complete month
        first_of_this_month = today.replace(day=1)
        last_month_start = (first_of_this_month - timedelta(days=1)).replace(day=1)
        return last_month_start, first_of_this_month, last_month_start.strftime('%B %Y')
    
    elif period == 'this-month':
        # Current month so far
        first_of_month = today.replace(day=1)
        return first_of_month, now, now.strftime('%B %Y (tot nu)')
    
    elif period == 'year':
        # Last complete year
        first_of_this_year = today.replace(month=1, day=1)
        last_year_start = first_of_this_year.replace(year=first_of_this_year.year - 1)
        return last_year_start, first_of_this_year, str(last_year_start.year)
    
    elif period == 'this-year':
        # Current year so far
        first_of_year = today.replace(month=1, day=1)
        return first_of_year, now, f'{now.year} (tot nu)'
    
    else:
        raise ValueError(f"Unknown period: {period}")


if __name__ == '__main__':
    import argparse
    import sys
    
    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(
        description='P1 Meter Reporter - Generate and send reports for any period',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Test SMTP configuration
  %(prog)s --test-email                # Send test email to verify SMTP settings
  
  # Generate report and SEND VIA EMAIL (default behavior)
  %(prog)s --period today              # Generate + email today's report
  %(prog)s --period yesterday          # Generate + email yesterday's report
  %(prog)s --period week               # Generate + email last 7 days
  %(prog)s --period this-week          # Generate + email current week
  %(prog)s --period last-week          # Generate + email previous week
  %(prog)s --period month              # Generate + email last complete month
  %(prog)s --period this-month         # Generate + email current month so far
  %(prog)s --period year               # Generate + email last complete year
  %(prog)s --period this-year          # Generate + email current year so far
  
  # Custom date range (also sends email)
  %(prog)s --start 2025-01-01 --end 2025-01-31    # January 2025 report via email
  %(prog)s --start 2025-11-01 --end 2025-11-15    # Custom period via email
  
  # Email without CSV attachment
  %(prog)s --period month --no-csv     # Email report without CSV file
  
  # Export to CSV only (NO email)
  %(prog)s --period month --csv-only --output /output/report.csv
  %(prog)s --start 2025-01-01 --end 2025-12-31 --csv-only --output /output/year.csv
        '''
    )
    
    parser.add_argument(
        '--period',
        choices=['today', 'yesterday', 'week', 'this-week', 'last-week', 
                 'month', 'this-month', 'year', 'this-year'],
        help='Period preset for the report'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--csv-only',
        action='store_true',
        help='Export to CSV only, do NOT send email (default: email IS sent)'
    )
    
    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='Send email report without CSV attachment'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for CSV (used with --csv-only)'
    )
    
    parser.add_argument(
        '--test-email',
        action='store_true',
        help='Send a test email to verify SMTP configuration'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.test_email:
        # Test email mode - doesn't need other arguments
        pass
    elif not args.period and not (args.start and args.end):
        parser.error('Either --period or both --start and --end must be specified')
    elif args.period and (args.start or args.end):
        parser.error('Cannot use --period with --start/--end')
    elif args.csv_only and not args.output:
        parser.error('--output must be specified when using --csv-only')
    
    try:
        reporter = P1Reporter()
        
        # Test email mode
        if args.test_email:
            logger.info("=" * 70)
            logger.info("SMTP Configuration Test")
            logger.info("=" * 70)
            logger.info("")
            
            sender = reporter.email_sender
            logger.info(f"SMTP Host: {sender.smtp_host}")
            logger.info(f"SMTP Port: {sender.smtp_port}")
            logger.info(f"SMTP User: {sender.smtp_user}")
            logger.info(f"SMTP From: {sender.smtp_from}")
            logger.info(f"SMTP TLS: {sender.smtp_tls}")
            logger.info(f"Recipients: {len(sender.smtp_to)}")
            for i, recipient in enumerate(sender.smtp_to, 1):
                logger.info(f"  {i}. {recipient}")
            logger.info("")
            logger.info("=" * 70)
            logger.info("Sending test email...")
            logger.info("=" * 70)
            logger.info("")
            
            # Create test HTML email
            test_html = f'''
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .success {{ background: #d4edda; color: #155724; padding: 15px; 
                              border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; }}
                    .info-box {{ background: white; padding: 20px; border-radius: 5px; 
                               margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .info-row {{ display: flex; justify-content: space-between; 
                               padding: 10px 0; border-bottom: 1px solid #eee; }}
                    .info-row:last-child {{ border-bottom: none; }}
                    .label {{ font-weight: bold; color: #666; }}
                    .value {{ color: #333; }}
                    .footer {{ text-align: center; color: #999; font-size: 12px; 
                             margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
                    ul {{ list-style: none; padding: 0; }}
                    li {{ padding: 8px 0; padding-left: 25px; position: relative; }}
                    li:before {{ content: "✓"; position: absolute; left: 0; 
                               color: #28a745; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">🧪 P1 Monitor Test Email</h1>
                        <p style="margin: 10px 0 0 0;">SMTP Configuration Verification</p>
                    </div>
                    
                    <div class="content">
                        <div class="success">
                            <strong>✅ Success!</strong> If you're reading this, your SMTP configuration is working correctly.
                        </div>
                        
                        <div class="info-box">
                            <h3 style="margin-top: 0;">Configuration Details</h3>
                            <div class="info-row">
                                <span class="label">SMTP Server:</span>
                                <span class="value">{sender.smtp_host}:{sender.smtp_port}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">From Address:</span>
                                <span class="value">{sender.smtp_from}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Security:</span>
                                <span class="value">{"TLS" if sender.smtp_tls else "None"}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Recipients:</span>
                                <span class="value">{len(sender.smtp_to)}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">Timestamp:</span>
                                <span class="value">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                            </div>
                        </div>
                        
                        <h3>What's Working:</h3>
                        <ul>
                            <li>SMTP server connection established</li>
                            <li>Authentication successful</li>
                            <li>Email delivery working</li>
                            <li>HTML formatting supported</li>
                            <li>Multiple recipients supported ({len(sender.smtp_to)} configured)</li>
                        </ul>
                        
                        <h3>Recipients:</h3>
                        <ul>
                            {"".join([f"<li>{email}</li>" for email in sender.smtp_to])}
                        </ul>
                        
                        <p style="margin-top: 30px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 5px;">
                            <strong>📝 Note:</strong> This is a test email from P1 Monitor. 
                            Your system is ready to send automated reports!
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>P1 Monitor - Automated Smart Meter Monitoring System</p>
                        <p>Powered by QuestDB & Python</p>
                    </div>
                </div>
            </body>
            </html>
            '''
            
            success = sender.send_email(
                subject='✅ P1 Monitor - SMTP Test Successful',
                html_content=test_html
            )
            
            logger.info("")
            if success:
                logger.info("=" * 70)
                logger.info("✅ TEST PASSED - Email sent successfully!")
                logger.info("=" * 70)
                logger.info("")
                logger.info("Check your inbox to verify the email was received.")
                logger.info(f"Sent to: {', '.join(sender.smtp_to)}")
                sys.exit(0)
            else:
                logger.info("=" * 70)
                logger.info("❌ TEST FAILED - Email sending failed")
                logger.info("=" * 70)
                logger.info("")
                logger.info("Please check:")
                logger.info("  1. SMTP credentials are correct")
                logger.info("  2. SMTP server is reachable")
                logger.info("  3. Firewall allows outbound SMTP connections")
                logger.info("  4. Email addresses are valid")
                sys.exit(1)
        
        # Calculate date range
        if args.period:
            start_date, end_date, period_name = calculate_period(args.period)
            logger.info(f"Period: {period_name}")
        else:
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
            period_name = f"{start_date.strftime('%d-%m-%Y')} tot {end_date.strftime('%d-%m-%Y')}"
            logger.info(f"Custom range: {period_name}")
        
        logger.info(f"Start: {start_date}")
        logger.info(f"End: {end_date}")
        logger.info("")
        
        if args.csv_only:
            # Export CSV only
            logger.info("Exporting CSV...")
            csv_content = reporter.export_period_csv(start_date, end_date)
            
            if csv_content:
                with open(args.output, 'w') as f:
                    f.write(csv_content)
                logger.info(f"✓ CSV exported to {args.output}")
                sys.exit(0)
            else:
                logger.error("✗ No data available for the specified period")
                sys.exit(1)
        else:
            # Generate and send report via email
            logger.info("Generating report and sending via email...")
            logger.info("")
            
            # Get stats first to check if data exists
            stats = reporter.get_period_stats(start_date, end_date)
            if not stats or stats['total_records'] == 0:
                logger.error("✗ No data available for the specified period")
                logger.error(f"  Period: {start_date.date()} to {end_date.date()}")
                sys.exit(1)
            
            # Send report (with or without CSV based on --no-csv flag)
            if args.no_csv:
                # Send email without CSV attachment
                live_data = reporter._get_live_data()
                
                # Determine if this is a monthly report or custom period
                is_monthly = (start_date.day == 1 and end_date.day == 1 and 
                             start_date.month != end_date.month and
                             (end_date - start_date).days <= 32)
                
                # Show comparison for monthly reports OR periods starting on day 1 (like "this-month")
                show_comparison = is_monthly or (start_date.day == 1 and start_date.month == end_date.month)
                
                # Get previous month stats for comparison
                prev_month_stats = None
                if show_comparison:
                    try:
                        prev_month_stats = reporter.get_previous_month_stats(start_date)
                        # Keep prev_month_stats even if 0 records, so template can show "no data" message
                    except Exception as e:
                        logger.warning(f"Could not get previous month stats: {e}")
                        prev_month_stats = None
                
                # Generate period graph (always - shows the period's data)
                logger.info("Generating period graph...")
                graph_image = None
                try:
                    graph_image = reporter.generate_period_graph(start_date, end_date)
                    if graph_image:
                        logger.info("✓ Period graph generated successfully")
                except Exception as e:
                    logger.warning(f"Period graph generation failed: {e}")
                
                # Generate yearly graph (for full monthly reports OR periods starting on day 1 like "this-month")
                yearly_graph_image = None
                if is_monthly or show_comparison:
                    logger.info("Generating yearly graph...")
                    try:
                        yearly_graph_image = reporter.generate_yearly_graph()
                        if yearly_graph_image:
                            logger.info("✓ Yearly graph generated successfully")
                    except Exception as e:
                        logger.warning(f"Yearly graph generation failed: {e}")
                
                # Show "Maandoverzicht" for full monthly reports OR periods starting on day 1 (like "this-month")
                report_title = "Maandoverzicht" if (is_monthly or show_comparison) else "Rapport"
                report_type = "maandoverzicht" if (is_monthly or show_comparison) else "rapport"
                
                from .templates import generate_monthly_html
                html_content = generate_monthly_html(
                    stats, live_data, 
                    has_csv_attachment=False, 
                    graph_image=graph_image,
                    yearly_graph_image=yearly_graph_image,
                    prev_month_stats=prev_month_stats,
                    report_title=report_title,
                    report_type=report_type,
                    is_monthly=show_comparison
                )
                
                subject = f"P1 Meter {report_title} - {period_name}"
                success = reporter.email_sender.send_email(
                    subject=subject,
                    html_content=html_content
                )
                
                if success:
                    logger.info(f"✓ Report sent successfully (no CSV) for {period_name}")
                else:
                    logger.error("✗ Failed to send report")
                    sys.exit(1)
            else:
                # Send report with CSV attachment (default)
                success = reporter.send_period_report(start_date, end_date, period_name)
                if not success:
                    sys.exit(1)
            
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

