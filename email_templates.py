#!/usr/bin/env python3
"""
Email HTML Templates
"""

from jinja2 import Template
from datetime import datetime
import pytz


MONTHLY_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body { font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5; margin: 0; padding: 20px; }
.container { max-width: 700px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
h1 { color: #2c5aa0; border-bottom: 3px solid #2c5aa0; padding-bottom: 10px; margin-top: 0; }
h2 { color: #2c5aa0; margin-top: 25px; margin-bottom: 15px; font-size: 18px; }
.period-box { background-color: #e8f0fe; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; font-size: 16px; font-weight: bold; }
table { width: 100%; border-collapse: collapse; margin: 15px 0; }
td { padding: 8px 12px; border-bottom: 1px solid #e0e0e0; }
td:first-child { font-weight: 500; width: 50%; }
td:last-child { text-align: right; font-weight: bold; color: #2c5aa0; }
.indent { padding-left: 30px !important; font-weight: normal; font-size: 14px; }
.section { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
.current-readings { background-color: #e8f5e9; }
.highlight { background-color: #fff9e6; font-weight: bold; }
.footer { margin-top: 30px; padding-top: 20px; border-top: 2px solid #e0e0e0; color: #666; font-size: 12px; }
.meter-info { background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; font-size: 13px; }
</style>
</head>
<body>
<div class="container">
<h1>📊 P1 Meter {{ report_title }}</h1>
<p>Beste administratie,</p>
<p>Hierbij het {{ report_type }} van de P1 meter.</p>

<div class="period-box">
PERIODE: {{ period_start }} t/m {{ period_end }}
</div>

<div class="section">
<h2>⚡ Verbruik deze periode</h2>
<table>
<tr><td>Elektriciteit verbruikt</td><td>{{ electricity_consumed }} kWh{% if prev_month_comparison and prev_month_comparison.electricity_consumed %}<span style="color: {% if prev_month_comparison.electricity_consumed_diff > 0 %}#d32f2f{% else %}#388e3c{% endif %}; font-size: 12px; font-weight: normal;"> ({{ prev_month_comparison.electricity_consumed_diff_percent }}%)</span>{% endif %}</td></tr>
<tr><td class="indent">Normaaltarief</td><td>{{ consumed_t1 }} kWh</td></tr>
<tr><td class="indent">Daltarief</td><td>{{ consumed_t2 }} kWh</td></tr>
<tr><td>Elektriciteit geleverd</td><td>{{ electricity_produced }} kWh</td></tr>
<tr class="highlight"><td>Netto verbruik</td><td>{{ net_consumption }} kWh</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>Gas verbruikt</td><td>{{ gas_consumed }} m³{% if prev_month_comparison and prev_month_comparison.gas_consumed %}<span style="color: {% if prev_month_comparison.gas_consumed_diff > 0 %}#d32f2f{% else %}#388e3c{% endif %}; font-size: 12px; font-weight: normal;"> ({{ prev_month_comparison.gas_consumed_diff_percent }}%)</span>{% endif %}</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>Gemiddeld vermogen</td><td>{{ avg_power }} W</td></tr>
<tr><td>Piek vermogen</td><td>{{ peak_power }} W</td></tr>
{% if is_monthly %}
<tr><td colspan="2" bgcolor="#fff3cd" style="padding: 15px 12px; margin-top: 15px; background-color: #fff3cd; border-top: 3px solid #ffc107; border-bottom: 3px solid #ffc107; font-size: 13px;">
{% if prev_month_comparison %}
<strong style="color: #2c5aa0;">📊 Vergelijking met vorige maand:</strong><br>
{% if prev_month_comparison.electricity_consumed_diff != 0 %}
Elektriciteit: {% if prev_month_comparison.electricity_consumed_diff > 0 %}+{% endif %}{{ prev_month_comparison.electricity_consumed_diff }} kWh ({% if prev_month_comparison.electricity_consumed_diff > 0 %}+{% endif %}{{ prev_month_comparison.electricity_consumed_diff_percent }}%)<br>
{% endif %}
{% if prev_month_comparison.gas_consumed_diff != 0 %}
Gas: {% if prev_month_comparison.gas_consumed_diff > 0 %}+{% endif %}{{ prev_month_comparison.gas_consumed_diff }} m³ ({% if prev_month_comparison.gas_consumed_diff > 0 %}+{% endif %}{{ prev_month_comparison.gas_consumed_diff_percent }}%)
{% endif %}
{% else %}
<strong style="color: #856404; font-size: 14px;">⚠️ Vergelijking met vorige maand:</strong><br>
<span style="color: #856404;">Geen gegevens beschikbaar voor de vorige maand. De vergelijking wordt getoond zodra er gegevens voor twee opeenvolgende maanden beschikbaar zijn.</span>
{% endif %}
</td></tr>
{% endif %}
</table>
</div>

{% if graph_image %}
<div class="section">
<h2>📈 Verbruik Grafiek - Deze Periode</h2>
<div style="text-align: center; margin: 20px 0;">
<img src="data:image/png;base64,{{ graph_image }}" alt="Verbruik Grafiek" style="max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />
</div>
</div>
{% endif %}

{% if yearly_graph_image %}
<div class="section">
<h2>📊 Maandelijks Overzicht - Dit Jaar</h2>
<div style="text-align: center; margin: 20px 0;">
<img src="data:image/png;base64,{{ yearly_graph_image }}" alt="Jaarlijks Overzicht" style="max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />
</div>
</div>
{% endif %}

<div class="section current-readings">
<h2>📍 Huidige meterstanden (nu op de meter)</h2>
<table>
<tr><td><strong>Elektriciteit import</strong></td><td><strong>{{ live_import }} kWh</strong></td></tr>
<tr><td class="indent">Normaaltarief</td><td>{{ live_import_t1 }} kWh</td></tr>
<tr><td class="indent">Daltarief</td><td>{{ live_import_t2 }} kWh</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td><strong>Elektriciteit export</strong></td><td><strong>{{ live_export }} kWh</strong></td></tr>
<tr><td class="indent">Normaaltarief</td><td>{{ live_export_t1 }} kWh</td></tr>
<tr><td class="indent">Daltarief</td><td>{{ live_export_t2 }} kWh</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td><strong>Gas totaal</strong></td><td><strong>{{ live_gas }} m³</strong></td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr class="highlight"><td>Huidig vermogen</td><td>{{ live_power }} W</td></tr>
</table>
</div>

<div class="meter-info">
<strong>Meter:</strong> {{ meter_model }}<br>
<strong>Meter ID:</strong> {{ unique_id }}<br>
<strong>Datapunten:</strong> {{ total_records }} metingen
</div>

{% if has_csv_attachment %}
<p><strong>📎 Bijgesloten:</strong> Gedetailleerde CSV met alle metingen</p>
{% endif %}

<div class="footer">
<p>Met vriendelijke groet,<br>
<strong>P1 Meter Systeem</strong></p>
<p style="font-size: 11px; color: #999;">Dit is een automatisch gegenereerd rapport.</p>
</div>

</div>
</body>
</html>
"""


def generate_monthly_html(stats, live_data, has_csv_attachment=True, graph_image=None, 
                          yearly_graph_image=None, prev_month_stats=None, report_title="Maandoverzicht", report_type="maandoverzicht", is_monthly=True):
    """Generate HTML email for report
    
    Args:
        stats: Statistics data from QuestDB
        live_data: Live data from P1 API
        has_csv_attachment: Whether CSV is attached to the email (default: True)
        graph_image: Base64 encoded period graph image (optional)
        yearly_graph_image: Base64 encoded yearly graph image (optional)
        prev_month_stats: Previous month statistics for comparison (optional)
        report_title: Title for the report (default: "Maandoverzicht")
        report_type: Type text for the report (default: "maandoverzicht")
        is_monthly: Whether this is a monthly report (default: True)
    """
    
    template = Template(MONTHLY_REPORT_TEMPLATE)
    
    # Calculate net consumption
    net_consumption = float(stats.get('electricity_consumed', 0)) - float(stats.get('electricity_produced', 0))
    
    # Format dates (convert UTC to Europe/Amsterdam timezone)
    amsterdam_tz = pytz.timezone('Europe/Amsterdam')
    utc_tz = pytz.UTC
    
    period_start = 'N/A'
    period_end = 'N/A'
    
    if stats.get('period_start'):
        period_start_dt = stats.get('period_start')
        # Convert naive UTC datetime to timezone-aware, then to Amsterdam timezone
        if period_start_dt.tzinfo is None:
            period_start_dt = utc_tz.localize(period_start_dt)
        period_start_ams = period_start_dt.astimezone(amsterdam_tz)
        period_start = period_start_ams.strftime('%Y-%m-%d')
    
    if stats.get('period_end'):
        period_end_dt = stats.get('period_end')
        # Convert naive UTC datetime to timezone-aware, then to Amsterdam timezone
        if period_end_dt.tzinfo is None:
            period_end_dt = utc_tz.localize(period_end_dt)
        period_end_ams = period_end_dt.astimezone(amsterdam_tz)
        period_end = period_end_ams.strftime('%Y-%m-%d')
    
    # Calculate previous month comparison (only for monthly reports)
    prev_month_comparison = None
    has_prev_month_data = False
    show_no_data_message = False
    
    # Only show comparison for monthly reports
    if is_monthly:
        # Always show comparison section for monthly reports
        # Check if we attempted to get previous month data (for monthly reports)
        if prev_month_stats is not None:
            # We tried to get previous month data
            # Handle both dict and RealDictRow types
            if hasattr(prev_month_stats, 'get'):
                total_records = prev_month_stats.get('total_records', 0)
            elif hasattr(prev_month_stats, '__getitem__'):
                total_records = prev_month_stats.get('total_records', 0) if 'total_records' in prev_month_stats else 0
            else:
                total_records = 0
            
            if total_records > 0:
                # We have previous month data, calculate comparison
                current_elec = float(stats.get('electricity_consumed', 0) or 0)
                prev_elec = float(prev_month_stats.get('electricity_consumed', 0) or 0) if hasattr(prev_month_stats, 'get') else 0
                current_gas = float(stats.get('gas_consumed', 0) or 0)
                prev_gas = float(prev_month_stats.get('gas_consumed', 0) or 0) if hasattr(prev_month_stats, 'get') else 0
                
                # Only create comparison if we have valid previous month data
                if prev_elec > 0 or prev_gas > 0:
                    has_prev_month_data = True
                    elec_diff = current_elec - prev_elec
                    elec_diff_percent = round((elec_diff / prev_elec * 100) if prev_elec > 0 else 0, 1)
                    
                    gas_diff = current_gas - prev_gas
                    gas_diff_percent = round((gas_diff / prev_gas * 100) if prev_gas > 0 else 0, 1)
                    
                    prev_month_comparison = {
                        'electricity_consumed': prev_elec,
                        'electricity_consumed_diff': round(elec_diff, 2),
                        'electricity_consumed_diff_percent': elec_diff_percent,
                        'gas_consumed': prev_gas,
                        'gas_consumed_diff': round(gas_diff, 2),
                        'gas_consumed_diff_percent': gas_diff_percent
                    }
            # If prev_month_stats has 0 records, prev_month_comparison stays None
            # which will trigger the "no data" message in the template
        # If prev_month_stats is None, prev_month_comparison stays None
        # which will trigger the "no data" message in the template
        # In both cases, the template will show the yellow warning box
    
    # Render template
    html = template.render(
        period_start=period_start,
        period_end=period_end,
        electricity_consumed=stats.get('electricity_consumed', 0),
        consumed_t1=stats.get('consumed_t1', 0),
        consumed_t2=stats.get('consumed_t2', 0),
        electricity_produced=stats.get('electricity_produced', 0),
        net_consumption=round(net_consumption, 2),
        gas_consumed=stats.get('gas_consumed', 0),
        avg_power=int(stats.get('avg_power', 0)),
        peak_power=int(stats.get('peak_power', 0)),
        live_import=live_data.get('total_power_import_kwh', 'N/A'),
        live_import_t1=live_data.get('total_power_import_t1_kwh', 'N/A'),
        live_import_t2=live_data.get('total_power_import_t2_kwh', 'N/A'),
        live_export=live_data.get('total_power_export_kwh', 'N/A'),
        live_export_t1=live_data.get('total_power_export_t1_kwh', 'N/A'),
        live_export_t2=live_data.get('total_power_export_t2_kwh', 'N/A'),
        live_gas=live_data.get('total_gas_m3', 'N/A'),
        live_power=live_data.get('active_power_w', 'N/A'),
        meter_model=stats.get('meter_model', 'Unknown'),
        unique_id=stats.get('unique_id', 'Unknown'),
        total_records=stats.get('total_records', 0),
        has_csv_attachment=has_csv_attachment,
        graph_image=graph_image,
        yearly_graph_image=yearly_graph_image,
        prev_month_comparison=prev_month_comparison,
        has_prev_month_data=has_prev_month_data,
        show_no_data_message=show_no_data_message,
        report_title=report_title,
        report_type=report_type,
        is_monthly=is_monthly
    )
    
    return html

