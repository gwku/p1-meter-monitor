#!/usr/bin/env python3
"""
Email HTML Templates
"""

from jinja2 import Template


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
<h1>📊 P1 Meter Maandoverzicht</h1>
<p>Beste administratie,</p>
<p>Hierbij het maandoverzicht van de P1 meter.</p>

<div class="period-box">
PERIODE: {{ period_start }} t/m {{ period_end }}
</div>

<div class="section">
<h2>⚡ Verbruik deze periode</h2>
<table>
<tr><td>Elektriciteit verbruikt</td><td>{{ electricity_consumed }} kWh</td></tr>
<tr><td class="indent">Normaaltarief</td><td>{{ consumed_t1 }} kWh</td></tr>
<tr><td class="indent">Daltarief</td><td>{{ consumed_t2 }} kWh</td></tr>
<tr><td>Elektriciteit geleverd</td><td>{{ electricity_produced }} kWh</td></tr>
<tr class="highlight"><td>Netto verbruik</td><td>{{ net_consumption }} kWh</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>Gas verbruikt</td><td>{{ gas_consumed }} m³</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>Gemiddeld vermogen</td><td>{{ avg_power }} W</td></tr>
<tr><td>Piek vermogen</td><td>{{ peak_power }} W</td></tr>
</table>
</div>

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


def generate_monthly_html(stats, live_data, has_csv_attachment=True):
    """Generate HTML email for monthly report
    
    Args:
        stats: Statistics data from QuestDB
        live_data: Live data from P1 API
        has_csv_attachment: Whether CSV is attached to the email (default: True)
    """
    
    template = Template(MONTHLY_REPORT_TEMPLATE)
    
    # Calculate net consumption
    net_consumption = float(stats.get('electricity_consumed', 0)) - float(stats.get('electricity_produced', 0))
    
    # Format dates
    period_start = stats.get('period_start', '').strftime('%Y-%m-%d') if stats.get('period_start') else 'N/A'
    period_end = stats.get('period_end', '').strftime('%Y-%m-%d') if stats.get('period_end') else 'N/A'
    
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
        has_csv_attachment=has_csv_attachment
    )
    
    return html

