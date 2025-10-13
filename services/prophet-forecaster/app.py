import os
import logging
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from prophet import Prophet
from flask import Flask, jsonify, request
from tenacity import retry, stop_after_attempt, wait_exponential
import numpy as np

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection parameters
PG_CONN_INFO = dict(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=30))
def get_db_connection():
    """Get database connection with retry logic"""
    return psycopg2.connect(**PG_CONN_INFO)

def fetch_historical_data(symbol: str, days: int = 30, granularity: str = "hour", hours: int | None = None):
    """Fetch historical price data for the given symbol with flexible granularity.

    - granularity="hour": aggregates by hour over last `days` days
    - granularity="minute": fetches raw ticks for last `hours` (default 6) and resamples to 1-minute averages
    """
    try:
        conn = get_db_connection()

        if granularity == "minute":
            # Default lookback hours for minute data
            lookback_hours = hours or 6
            logger.info(f"Querying minute data: symbol={symbol}, hours={lookback_hours}")
            query = """
                SELECT 
                    event_time AS ts,
                    price::numeric AS price
                FROM public.coin_ticks
                WHERE symbol = %s 
                  AND event_time >= NOW() - INTERVAL '%s hours'
                ORDER BY ts
            """
            df_raw = pd.read_sql_query(query, conn, params=(symbol, lookback_hours))
            logger.info(f"Raw data fetched: {len(df_raw)} rows")
            conn.close()

            if df_raw.empty:
                logger.warning(f"No raw data found for symbol {symbol}")
                return None

            # Resample to 1-minute frequency using pandas
            df_raw['ts'] = pd.to_datetime(df_raw['ts'])
            df_raw.set_index('ts', inplace=True)
            
            # Use mean over each minute; forward fill missing minutes to maintain continuity
            df_min = df_raw['price'].resample('1T').mean()
            
            # Drop NaN values and forward fill only if we have enough data
            df_min = df_min.dropna()
            if len(df_min) < 10:
                # If resampling results in too few points, use original data with time rounding
                logger.info(f"Resampling yielded too few points ({len(df_min)}), using rounded timestamps instead")
                df_raw_copy = df_raw.copy()
                df_raw_copy.index = df_raw_copy.index.round('T')  # Round to nearest minute
                df_min = df_raw_copy['price'].groupby(df_raw_copy.index).mean()
            
            df_min = df_min.reset_index().rename(columns={'ts': 'ds', 'price': 'y'})
            logger.info(f"After resampling: {len(df_min)} minute intervals")

            # Ensure numeric types
            df_min['ds'] = pd.to_datetime(df_min['ds'])
            df_min['y'] = pd.to_numeric(df_min['y'])
            return df_min[['ds', 'y']]

        else:
            # Hourly aggregation for last `days` days
            query = """
                SELECT 
                    date_trunc('hour', event_time) as ds,
                    AVG(price) as y,
                    symbol
                FROM public.coin_ticks 
                WHERE symbol = %s 
                  AND event_time >= NOW() - INTERVAL '%s days'
                GROUP BY date_trunc('hour', event_time), symbol
                ORDER BY ds
            """
            df = pd.read_sql_query(query, conn, params=(symbol, days))
            conn.close()

            if df.empty:
                logger.warning(f"No data found for symbol {symbol}")
                return None

            df['ds'] = pd.to_datetime(df['ds'])
            df['y'] = pd.to_numeric(df['y'])
            return df[['ds', 'y']]

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def create_prophet_model(df):
    """Create and train Prophet model"""
    try:
        # Initialize Prophet with some basic parameters
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,  # Crypto doesn't follow yearly patterns
            changepoint_prior_scale=0.05,  # Lower value = less flexible
            seasonality_prior_scale=10.0,
            interval_width=0.8
        )
        
        # Add custom seasonalities for crypto
        model.add_seasonality(name='hourly', period=1, fourier_order=8)
        
        # Fit the model
        model.fit(df)
        
        return model
        
    except Exception as e:
        logger.error(f"Error creating Prophet model: {str(e)}")
        return None

def generate_forecast(model, periods=24, freq: str = 'H'):
    """Generate forecast for the next periods using specified frequency.

    - freq='H' for hours
    - freq='T' for minutes
    """
    try:
        # Create future dataframe
        future = model.make_future_dataframe(periods=periods, freq=freq)

        # Generate forecast
        forecast = model.predict(future)

        # Get only the forecasted part (not historical)
        forecast_only = forecast.tail(periods)

        return forecast_only[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}")
        return None

def save_forecast_to_db(symbol, forecast_df):
    """Save forecast results to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert forecast data
        for _, row in forecast_df.iterrows():
            cursor.execute("""
                INSERT INTO public.coin_forecasts 
                (symbol, forecast_time, predicted_price, lower_bound, upper_bound, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, forecast_time) 
                DO UPDATE SET 
                    predicted_price = EXCLUDED.predicted_price,
                    lower_bound = EXCLUDED.lower_bound,
                    upper_bound = EXCLUDED.upper_bound,
                    created_at = EXCLUDED.created_at
            """, (
                symbol,
                row['ds'],
                float(row['yhat']),
                float(row['yhat_lower']),
                float(row['yhat_upper']),
                datetime.utcnow()
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Saved {len(forecast_df)} forecast points for {symbol}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving forecast to database: {str(e)}")
        return False

@app.route('/forecast/<symbol>')
def forecast_symbol(symbol):
    """API endpoint to generate forecast for a specific symbol"""
    try:
        # Get parameters from query string
        days = request.args.get('days', 30, type=int)
        periods = request.args.get('periods', 24, type=int)
        granularity = request.args.get('granularity', 'hour', type=str)
        hours = request.args.get('hours', None, type=int)
        
        logger.info(f"Forecast request: symbol={symbol}, granularity={granularity}, hours={hours}, days={days}, periods={periods}")
        
        # Validate symbol (should be in our list of tracked coins)
        from configs import BINANCE20
        if symbol not in BINANCE20:
            return jsonify({'error': f'Symbol {symbol} not supported'}), 400
        
        # Fetch historical data
        if granularity == 'minute':
            effective_hours = hours or 6
            logger.info(f"Fetching minute-level data for {symbol} (last {effective_hours} hours)")
            df = fetch_historical_data(symbol, days=days, granularity='minute', hours=effective_hours)
            min_required = 10  # at least 10 data points for minute-level
        else:
            logger.info(f"Fetching hourly data for {symbol} (last {days} days)")
            df = fetch_historical_data(symbol, days=days, granularity='hour')
            min_required = 24  # at least 24 hours

        if df is None or len(df) < min_required:
            # Try with lower requirements if we have some data
            if df is not None and len(df) >= 10:
                logger.info(f"Relaxing requirements for {symbol}: using {len(df)} points instead of {min_required}")
                min_required = len(df)
            else:
                return jsonify({'error': f'Insufficient data for {symbol}', 'required_points': min_required, 'available_points': (0 if df is None else len(df))}), 400
        
        # Create and train model
        logger.info(f"Training Prophet model for {symbol}")
        model = create_prophet_model(df)
        
        if model is None:
            return jsonify({'error': f'Failed to create model for {symbol}'}), 500
        
        # Generate forecast
        if granularity == 'minute':
            logger.info(f"Generating {periods} minute forecast for {symbol}")
            forecast = generate_forecast(model, periods, freq='T')
        else:
            logger.info(f"Generating {periods} hour forecast for {symbol}")
            forecast = generate_forecast(model, periods, freq='H')
        
        if forecast is None:
            return jsonify({'error': f'Failed to generate forecast for {symbol}'}), 500
        
        # Save to database
        save_forecast_to_db(symbol, forecast)
        
        # Prepare response
        forecast_list = []
        for _, row in forecast.iterrows():
            forecast_list.append({
                'time': row['ds'].isoformat(),
                'predicted_price': float(row['yhat']),
                'lower_bound': float(row['yhat_lower']),
                'upper_bound': float(row['yhat_upper'])
            })
        
        return jsonify({
            'symbol': symbol,
            'forecast_periods': periods,
            'period_unit': ('minute' if granularity == 'minute' else 'hour'),
            'training_days': days,
            'forecast': forecast_list
        })
        
    except Exception as e:
        logger.error(f"Error in forecast endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/forecast/batch')
def forecast_batch():
    """Generate forecasts for all supported symbols"""
    try:
        from configs import BINANCE20
        
        results = {}
        errors = []
        
        for symbol in BINANCE20:
            try:
                logger.info(f"Processing forecast for {symbol}")
                
                # Try hourly data first (last 30 days)
                df = fetch_historical_data(symbol, days=30, granularity='hour')
                freq = 'H'
                periods = 24
                min_required = 24

                # Fallback to minute-level if hourly insufficient
                if df is None or len(df) < min_required:
                    logger.info(f"Hourly data insufficient for {symbol}, falling back to minute-level")
                    df = fetch_historical_data(symbol, days=30, granularity='minute', hours=1)
                    freq = 'T'
                    periods = 60  # next 60 minutes
                    min_required = 10  # reduced requirement

                # Relax requirements if we have some data
                if df is not None and len(df) >= 10 and len(df) < min_required:
                    logger.info(f"Relaxing requirements for {symbol}: using {len(df)} points instead of {min_required}")
                    min_required = len(df)

                if df is None or len(df) < 10:
                    errors.append(f"Insufficient data for {symbol} (need at least 10 points, got {0 if df is None else len(df)})")
                    continue

                model = create_prophet_model(df)
                if model is None:
                    errors.append(f"Failed to create model for {symbol}")
                    continue

                forecast = generate_forecast(model, periods, freq=freq)
                if forecast is None:
                    errors.append(f"Failed to generate forecast for {symbol}")
                    continue
                
                # Save to database
                if save_forecast_to_db(symbol, forecast):
                    results[symbol] = {
                        'status': 'success',
                        'forecast_points': len(forecast)
                    }
                else:
                    errors.append(f"Failed to save forecast for {symbol}")
                    
            except Exception as e:
                errors.append(f"Error processing {symbol}: {str(e)}")
                
        return jsonify({
            'processed_symbols': len(results),
            'results': results,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in batch forecast: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = get_db_connection()
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/')
def index():
    """Basic info endpoint"""
    return jsonify({
        'service': 'Prophet Forecaster',
        'version': '1.0.0',
        'endpoints': [
            '/forecast/<symbol>?days=30&periods=24',
            '/forecast/<symbol>?granularity=minute&hours=3&periods=60',
            '/forecast/batch',
            '/health'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)