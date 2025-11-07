from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, send_file
from models.violation_log import ViolationLog
import pandas as pd
import io

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/api/reports')
def get_report_data():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'violations')

        violation_log = ViolationLog()
        
        # Convert dates to datetime objects
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Get violations within date range
        violations = violation_log.violations.find({
            'timestamp': {'$gte': start_dt, '$lt': end_dt}
        })

        # Process data by date
        data_by_date = {}
        for v in violations:
            date_str = v['timestamp'].strftime('%Y-%m-%d')
            if date_str not in data_by_date:
                data_by_date[date_str] = {
                    'total_violations': 0,
                    'speeds': [],
                    'violations_by_hour': {str(i).zfill(2): 0 for i in range(24)}
                }
            
            data_by_date[date_str]['total_violations'] += 1
            data_by_date[date_str]['speeds'].append(v['speed'])
            hour = v['timestamp'].strftime('%H')
            data_by_date[date_str]['violations_by_hour'][hour] += 1

        # Prepare response data
        dates = sorted(data_by_date.keys())
        response_data = {
            'dates': dates,
            'violations': [data_by_date[d]['total_violations'] for d in dates],
            'speeds': [sum(data_by_date[d]['speeds']) / len(data_by_date[d]['speeds']) 
                      if data_by_date[d]['speeds'] else 0 for d in dates],
            'details': []
        }

        # Add detailed information
        for date in dates:
            peak_hours = sorted(
                data_by_date[date]['violations_by_hour'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            response_data['details'].append({
                'date': date,
                'total_violations': data_by_date[date]['total_violations'],
                'avg_speed': sum(data_by_date[date]['speeds']) / len(data_by_date[date]['speeds']) 
                            if data_by_date[date]['speeds'] else 0,
                'peak_hours': ', '.join([f"{h}:00" for h, _ in peak_hours])
            })

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/api/reports/download')
def download_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'violations')

        violation_log = ViolationLog()
        
        # Convert dates to datetime objects
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Get violations within date range
        violations = list(violation_log.violations.find({
            'timestamp': {'$gte': start_dt, '$lt': end_dt}
        }))

        # Create DataFrame
        df = pd.DataFrame(violations)
        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # Create CSV file in memory
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'traffic_report_{start_date}_to_{end_date}.csv'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500