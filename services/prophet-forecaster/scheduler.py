#!/usr/bin/env python3
"""
Cron job script to trigger Prophet forecasts periodically
"""

import requests
import json
import time
import schedule
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/prophet_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ForecastScheduler:
    def __init__(self, prophet_url: str = "http://prophet-forecaster:5000"):
        self.prophet_url = prophet_url
        
    def health_check(self) -> bool:
        """Check if Prophet service is healthy"""
        try:
            response = requests.get(f"{self.prophet_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def trigger_batch_forecast(self) -> bool:
        """Trigger batch forecasting for all symbols"""
        try:
            logger.info("Starting batch forecast...")
            
            if not self.health_check():
                logger.error("Prophet service is not healthy, skipping forecast")
                return False
            
            response = requests.get(f"{self.prophet_url}/forecast/batch", timeout=600)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Batch forecast completed successfully:")
                logger.info(f"  - Processed symbols: {result.get('processed_symbols', 0)}")
                logger.info(f"  - Errors: {len(result.get('errors', []))}")
                
                if result.get('errors'):
                    for error in result.get('errors', []):
                        logger.warning(f"  - Error: {error}")
                
                return True
            else:
                logger.error(f"Batch forecast failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error during batch forecast: {str(e)}")
            return False
    
    def trigger_single_forecast(self, symbol: str, days: int = 30, periods: int = 24) -> bool:
        """Trigger forecast for a single symbol"""
        try:
            logger.info(f"Starting forecast for {symbol}...")
            
            params = {"days": days, "periods": periods}
            response = requests.get(
                f"{self.prophet_url}/forecast/{symbol}",
                params=params,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Forecast for {symbol} completed successfully")
                logger.info(f"  - Forecast periods: {result.get('forecast_periods', 0)}")
                return True
            else:
                logger.error(f"Forecast for {symbol} failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error forecasting {symbol}: {str(e)}")
            return False

def main():
    """Main function to set up scheduled tasks"""
    scheduler = ForecastScheduler()
    
    # Schedule batch forecasts every hour
    schedule.every().hour.do(scheduler.trigger_batch_forecast)
    
    # Schedule specific high-priority symbols every 30 minutes
    priority_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
    for symbol in priority_symbols:
        schedule.every(30).minutes.do(scheduler.trigger_single_forecast, symbol=symbol)
    
    logger.info("Prophet Forecast Scheduler started")
    logger.info("Scheduled tasks:")
    logger.info("  - Batch forecast: Every hour")
    logger.info(f"  - Priority symbols ({', '.join(priority_symbols)}): Every 30 minutes")
    
    # Run initial forecast
    logger.info("Running initial batch forecast...")
    scheduler.trigger_batch_forecast()
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()