"""
Custom Superset configuration for Prophet integration
"""

# Import the Prophet integration functions
from prophet_integration import CUSTOM_TEMPLATE_PROCESSORS, JINJA_CONTEXT_ADDONS

# Database configuration
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://crypto:crypto@postgres:5432/crypto'

# Security
SECRET_KEY = 'your_secret_key'
WTF_CSRF_ENABLED = True

# Prophet integration
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
    'SQLLAB_BACKEND_PERSISTENCE': True,
    'SCHEDULED_QUERIES': True,
    'DYNAMIC_PLUGINS': True,
}

# Custom template processors
CUSTOM_TEMPLATE_PROCESSORS.update(CUSTOM_TEMPLATE_PROCESSORS)

# Jinja context for SQL Lab
JINJA_CONTEXT_ADDONS.update(JINJA_CONTEXT_ADDONS)

# Allow custom SQL functions
PREVENT_UNSAFE_DB_CONNECTIONS = False
SQLLAB_CTAS_NO_LIMIT = True
SUPERSET_WEBSERVER_TIMEOUT = 300

# Chart and dashboard defaults
DEFAULT_FEATURE_FLAGS = {
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'GLOBAL_ASYNC_QUERIES': True,
}

# Custom color schemes
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "prophet_forecast",
        "description": "Prophet Forecast Colors",
        "colors": [
            "#1f77b4",  # Actual data
            "#ff7f0e",  # Forecast
            "#2ca02c",  # Upper bound
            "#d62728",  # Lower bound
        ]
    }
]

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,
}

# SQL Lab configuration
SQLLAB_TIMEOUT = 300
SQLLAB_ASYNC_TIME_LIMIT_SEC = 600