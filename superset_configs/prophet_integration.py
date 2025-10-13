import requests
import json
from typing import Dict, Any, List
from superset.extensions import cache_manager
from flask import current_app

class ProphetForecaster:
    """Class to handle Prophet forecasting integration"""
    
    def __init__(self, base_url: str = "http://prophet-forecaster:5000"):
        self.base_url = base_url
    
    def get_forecast(self, symbol: str, days: int = 30, periods: int = 24) -> Dict[str, Any]:
        """Get forecast for a specific symbol"""
        try:
            url = f"{self.base_url}/forecast/{symbol}"
            params = {"days": days, "periods": periods}
            
            response = requests.get(url, params=params, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error getting forecast for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def get_batch_forecast(self) -> Dict[str, Any]:
        """Get forecasts for all supported symbols"""
        try:
            url = f"{self.base_url}/forecast/batch"
            
            response = requests.get(url, timeout=600)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error getting batch forecast: {str(e)}")
            return {"error": str(e)}
    
    def health_check(self) -> bool:
        """Check if Prophet service is healthy"""
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

# Create global instance
prophet_forecaster = ProphetForecaster()

# Custom SQL functions for Superset
def get_forecast_data(symbol: str):
    """Custom function to get forecast data that can be used in SQL Lab"""
    result = prophet_forecaster.get_forecast(symbol)
    return json.dumps(result)

def trigger_batch_forecast():
    """Custom function to trigger batch forecasting"""
    result = prophet_forecaster.get_batch_forecast()
    return json.dumps(result)

# Register custom functions with Superset
CUSTOM_TEMPLATE_PROCESSORS = {
    'prophet_forecast': get_forecast_data,
    'trigger_batch_forecast': trigger_batch_forecast,
}

# Jinja template context for use in SQL Lab
JINJA_CONTEXT_ADDONS = {
    'prophet_forecast': get_forecast_data,
    'trigger_batch_forecast': trigger_batch_forecast,
}

# Allow custom functions in SQL Lab
PREVENT_UNSAFE_DB_CONNECTIONS = False
SQLLAB_CTAS_NO_LIMIT = True

# Cache configuration for forecast data
CACHE_CONFIG = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes
}

# Custom CSS for forecast charts
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "forecast_colors",
        "description": "Prophet Forecast Color Scheme",
        "colors": [
            "#1f77b4",  # Actual data (blue)
            "#ff7f0e",  # Forecast (orange)
            "#2ca02c",  # Upper bound (green)
            "#d62728",  # Lower bound (red)
        ]
    }
]