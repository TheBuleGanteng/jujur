import logging
import os
logger = logging.getLogger('django')

__all__ = ['company_data', 'fmp_key']


# Pull company data via FMP API
def company_data(symbol, fmp_key):
    logger.debug(f'running get_stock_info(symbol): ... symbol is: { symbol }')
        
    try:
        limit = 1
        response = requests.get(f'https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={fmp_key}')       
        increment_ping()
        logger.debug(f'running get_stock_info(symbol): ... response is: { response }')
        data = response.json()
        #print(f'running get_stock_info(symbol): ... data is: { data }')

        # Check if data contains at least one item
        if data and isinstance(data, list):
            return data[0]
        else:
            return None

    except Exception as e:
        logger.debug(f'running get_stock_info(symbol): ... function tried symbol: { symbol } but errored with error: { e }')
        return None


# Defines key for FMP api
fmp_key = os.getenv('FMP_API_KEY')