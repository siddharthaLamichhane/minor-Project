from flask import Blueprint
from .reports import reports_bp
from .report_data import report_data_bp

api_bp = Blueprint('api', __name__)
api_bp.register_blueprint(reports_bp)
api_bp.register_blueprint(report_data_bp)