#!/usr/bin/env python3
"""
Script to automatically create Prophet forecasting dashboard in Superset
"""

import requests
import json
import time
from typing import Dict, Any, List

class SupersetDashboardCreator:
    def __init__(self, base_url: str = "http://localhost:8088", 
                 username: str = "admin", password: str = "admin"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self) -> bool:
        """Login to Superset and get CSRF token"""
        try:
            # Get login page to get CSRF token
            response = self.session.get(f"{self.base_url}/login/")
            
            # Login
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.post(
                f"{self.base_url}/login/",
                data=login_data,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Get CSRF token
                csrf_response = self.session.get(f"{self.base_url}/api/v1/security/csrf_token/")
                if csrf_response.status_code == 200:
                    self.csrf_token = csrf_response.json()['result']
                    self.session.headers.update({
                        'X-CSRFToken': self.csrf_token,
                        'Content-Type': 'application/json'
                    })
                    print("Successfully logged in to Superset")
                    return True
            
            print("Failed to login to Superset")
            return False
            
        except Exception as e:
            print(f"Error during login: {str(e)}")
            return False
    
    def create_database_connection(self) -> bool:
        """Create database connection if it doesn't exist"""
        try:
            # Check if database connection already exists
            response = self.session.get(f"{self.base_url}/api/v1/database/")
            if response.status_code == 200:
                databases = response.json()['result']
                for db in databases:
                    if 'crypto' in db['database_name']:
                        print(f"Database connection already exists: {db['database_name']}")
                        return True
            
            # Create new database connection
            db_config = {
                "database_name": "Crypto Database",
                "sqlalchemy_uri": "postgresql+psycopg2://crypto:crypto@postgres:5432/crypto",
                "expose_in_sqllab": True,
                "allow_ctas": True,
                "allow_cvas": True,
                "allow_dml": True
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/database/",
                data=json.dumps(db_config)
            )
            
            if response.status_code in [200, 201]:
                print("Database connection created successfully")
                return True
            else:
                print(f"Failed to create database connection: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error creating database connection: {str(e)}")
            return False
    
    def create_dataset(self, table_name: str, database_id: int) -> Dict[str, Any]:
        """Create a dataset from a table"""
        try:
            dataset_config = {
                "database": database_id,
                "table_name": table_name,
                "schema": "public"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/dataset/",
                data=json.dumps(dataset_config)
            )
            
            if response.status_code in [200, 201]:
                dataset = response.json()['result']
                print(f"Dataset created for table {table_name}")
                return dataset
            else:
                print(f"Failed to create dataset for {table_name}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating dataset for {table_name}: {str(e)}")
            return None
    
    def create_chart(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chart"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/chart/",
                data=json.dumps(chart_config)
            )
            
            if response.status_code in [200, 201]:
                chart = response.json()['result']
                print(f"Chart created: {chart_config['slice_name']}")
                return chart
            else:
                print(f"Failed to create chart {chart_config['slice_name']}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating chart {chart_config['slice_name']}: {str(e)}")
            return None
    
    def create_dashboard(self, dashboard_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a dashboard"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/dashboard/",
                data=json.dumps(dashboard_config)
            )
            
            if response.status_code in [200, 201]:
                dashboard = response.json()['result']
                print(f"Dashboard created: {dashboard_config['dashboard_title']}")
                return dashboard
            else:
                print(f"Failed to create dashboard: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating dashboard: {str(e)}")
            return None
    
    def get_database_id(self) -> int:
        """Get the database ID for crypto database"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/database/")
            if response.status_code == 200:
                databases = response.json()['result']
                for db in databases:
                    if 'crypto' in db['database_name'].lower():
                        return db['id']
            return None
        except Exception as e:
            print(f"Error getting database ID: {str(e)}")
            return None
    
    def setup_prophet_dashboard(self):
        """Main method to set up the Prophet forecasting dashboard"""
        if not self.login():
            return False
        
        # Wait a bit for Superset to be fully ready
        time.sleep(5)
        
        # Create database connection
        if not self.create_database_connection():
            return False
        
        # Get database ID
        database_id = self.get_database_id()
        if not database_id:
            print("Could not find database ID")
            return False
        
        # Create datasets
        datasets = {}
        tables = ['coin_ticks', 'coin_forecasts', 'coin_data_with_forecasts']
        
        for table in tables:
            dataset = self.create_dataset(table, database_id)
            if dataset:
                datasets[table] = dataset
        
        # Chart configurations
        chart_configs = [
            {
                "slice_name": "Real-time Crypto Prices",
                "viz_type": "line",
                "datasource_id": datasets.get('coin_ticks', {}).get('id'),
                "datasource_type": "table",
                "params": json.dumps({
                    "metrics": ["price"],
                    "groupby": ["symbol"],
                    "granularity_sqla": "event_time",
                    "time_range": "Last 24 hours",
                    "color_scheme": "prophet_forecast"
                })
            },
            {
                "slice_name": "Price Forecasts vs Actual",
                "viz_type": "line",
                "datasource_id": datasets.get('coin_data_with_forecasts', {}).get('id'),
                "datasource_type": "table",
                "params": json.dumps({
                    "metrics": ["actual_price", "predicted_price"],
                    "groupby": ["symbol", "data_type"],
                    "granularity_sqla": "time",
                    "time_range": "Last 7 days",
                    "color_scheme": "prophet_forecast"
                })
            },
            {
                "slice_name": "Forecast Confidence Bands",
                "viz_type": "line",
                "datasource_id": datasets.get('coin_forecasts', {}).get('id'),
                "datasource_type": "table",
                "params": json.dumps({
                    "metrics": ["predicted_price", "lower_bound", "upper_bound"],
                    "groupby": ["symbol"],
                    "granularity_sqla": "forecast_time",
                    "time_range": "Next 24 hours",
                    "color_scheme": "prophet_forecast"
                })
            }
        ]
        
        # Create charts
        charts = []
        for config in chart_configs:
            if config.get('datasource_id'):
                chart = self.create_chart(config)
                if chart:
                    charts.append(chart)
        
        # Create dashboard
        if charts:
            dashboard_config = {
                "dashboard_title": "Crypto Prophet Forecasting Dashboard",
                "description": "Real-time cryptocurrency price forecasting using Facebook Prophet",
                "css": "",
                "json_metadata": json.dumps({
                    "refresh_frequency": 300,  # 5 minutes
                    "default_filters": {},
                    "color_scheme": "prophet_forecast"
                }),
                "slices": [chart['id'] for chart in charts]
            }
            
            dashboard = self.create_dashboard(dashboard_config)
            if dashboard:
                print(f"\n✅ Prophet Dashboard created successfully!")
                print(f"Dashboard URL: {self.base_url}/superset/dashboard/{dashboard['id']}/")
                return True
        
        print("❌ Failed to create dashboard")
        return False

def main():
    """Main function"""
    print("🚀 Setting up Prophet Forecasting Dashboard in Superset...")
    
    creator = SupersetDashboardCreator()
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(30)
    
    success = creator.setup_prophet_dashboard()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Visit http://localhost:8088")
        print("2. Login with admin/admin")
        print("3. Go to the Prophet Dashboard")
        print("4. Trigger forecasts by calling: http://localhost:5000/forecast/batch")
    else:
        print("\n❌ Setup failed. Please check the logs and try again.")

if __name__ == "__main__":
    main()