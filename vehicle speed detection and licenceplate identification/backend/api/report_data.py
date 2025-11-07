from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from models.violation_log import ViolationLog

report_data_bp = Blueprint('report_data', __name__)

@report_data_bp.route('/api/report-data')
def get_report_data():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({
                'error': 'Start date and end date are required'
            }), 400

        violation_log = ViolationLog()
        
        # Convert dates to datetime objects
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            return jsonify({
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400

        # Get violations within date range
        violations = list(violation_log.violations.find({
            'timestamp': {'$gte': start_dt, '$lt': end_dt}
        }))

        if not violations:
            return jsonify({
                'dates': [],
                'violations': [],
                'speeds': [],
                'details': []
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
            'speeds': [round(sum(data_by_date[d]['speeds']) / len(data_by_date[d]['speeds']), 2) 
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
                'avg_speed': round(sum(data_by_date[d]['speeds']) / len(data_by_date[d]['speeds']), 2) 
                            if data_by_date[date]['speeds'] else 0,
                'peak_hours': ', '.join([f"{h}:00" for h, _ in peak_hours if _> 0]) or 'N/A'
            })

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500