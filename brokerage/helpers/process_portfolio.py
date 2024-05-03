from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
import logging
from ..models import Listing, Transaction
from users.models import UserProfile
from .helpers import *
__all__ = ['process_user_transactions', 'Portfolio']

logger = logging.getLogger('django')


# Defines a class called portfolio, used for /index and /index_detail
class Portfolio:
    def __init__(self):
        # Below are portfolio totals
        self.portfolio_data = {}
        self.cash_initial = 0
        self.cash = 0
        self.portfolio_total_transaction_shares = 0
        self.portfolio_total_shares_outstanding = 0
        self.portfolio_cost_basis_total = 0
        self.portfolio_cost_basis_per_share = 0
        self.portfolio_STCG_unrealized = 0
        self.portfolio_LTCG_unrealized = 0
        self.portfolio_CG_unrealized = 0
        self.portfolio_CG_total_unrealized = 0
        self.portfolio_market_value_total_pre_tax = 0
        self.portfolio_market_value_total_pre_tax_incl_cash = 0
        self.portfolio_market_value_per_share = 0
        self.portfolio_gain_or_loss_pre_tax_percent = 0
        self.portfolio_STCG_tax_unrealized = 0
        self.portfolio_LTCG_tax_unrealized = 0
        self.portfolio_CG_tax_offset_unrealized = 0
        self.portfolio_market_value_post_tax = 0
        self.portfolio_market_value_post_tax_incl_cash = 0
        self.portfolio_return_percent_post_tax = 0
        self.cash_return_percent = 0
    
        # This metric holds the SLD transactions
        self.sell_transactions = []

        # Below are metrics for completed sales
        self.sld_transaction_shares_total = 0
        self.sld_transaction_cost_basis_total = 0
        self.sld_transaction_STCG_total = 0
        self.sld_transaction_LTCG_total = 0
        self.sld_transaction_CG_total_realized_total = 0
        self.sld_transaction_market_value_pre_tax_total = 0
        self.sld_transaction_gain_or_loss_pre_tax_percent = 0
        self.sld_transaction_STCG_tax_total = 0
        self.sld_transaction_LTCG_tax_total = 0
        self.sld_transaction_tax_offset_total = 0
        self.sld_transaction_market_value_post_tax_total = 0
        self.sld_transaction_return_percent_post_tax = 0

        # Below are metrics for open portfolio+cash+sales
        self.total_portfolio_transaction_shares = 0
        self.total_portfolio_STCG = 0
        self.total_portfolio_LTCG = 0
        self.total_portfolio_CG = 0
        self.total_portfolio_market_value_pre_tax = 0
        self.total_portfolio_gain_or_loss_pre_tax_percent = 0
        self.total_portfolio_STCG_tax = 0
        self.total_portfolio_LTCG_tax = 0
        self.total_portfolio_CG_tax_total = 0
        self.total_portfolio_tax_offset = 0
        self.total_portfolio_market_value_post_tax = 0
        self.total_portfolio_market_value_post_tax_percent = 0

    # Adds the symbol to portfolio
    def add_symbol(self, symbol, data):
        self.portfolio_data[symbol] = data

    # Adds symbol-level data
    def get_symbol_data(self, symbol):
        return self.portfolio_data.get(symbol, None)

#----------------------------------------------------------------------------------------

# Creates an item of the portfolio class and populates it
def process_user_transactions(user):
    logger.debug(f'running process_user_transactions() ...  for user { user.id } ...  function started')
    
    # Initialize tax rates and whether cap loss offset is turned on
    tax_rate_STCG = Decimal(user.userprofile.tax_rate_STCG / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tax_rate_LTCG = Decimal(user.userprofile.tax_rate_LTCG / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tax_offset_coefficient = 1 if user.userprofile.tax_loss_offsets == 'On' else 0
    cutoff_date = timezone.now() - timezone.timedelta(days=365)
    
    # Create an instance of the Portfolio class
    portfolio = Portfolio()
    logger.debug(f'running process_user_transactions() ...  for user { user.id } ...  object created')
    
    # Query transactions DB to see if user has transactions
    transactions = Transaction.objects.filter(user=user).all()
    
    # If user doesn't have transactions (e.g. a new user, return an empty portfolio object)
    if not transactions:
        logger.debug(f'running process_user_transactions() ... for user {user.id} ... no transactions in portfolio, returning empty portfolio object ')
        return portfolio
    
    # If user has transactions, but no open positions (e.g. everything is closed out), return an empty portfolio object
    total_shares_held = 0
    for transaction in transactions:
        if transaction.type =='BOT':
            total_shares_held += transaction.transaction_shares
        else:
            total_shares_held -= transaction.transaction_shares
    if not total_shares_held > 0:
        logger.debug(f'running process_user_transactions() ... for user {user.id} ... user has transactions, but all positions are closed.')
        return portfolio


    # Collect all unique symbols
    unique_symbols = set(transaction.symbol for transaction in transactions)
    print(f'running process_portfolio.py ... unique_symbols is: {unique_symbols}')
    unique_symbols_string = ','.join(unique_symbols)
    print(f'running process_portfolio.py ... unique_symbols_string is: {unique_symbols_string}')
    unique_symbols_data = company_data_multiple(unique_symbols_string)
    print(f'running process_portfolio.py ... unique_symbols_data is: {unique_symbols_data}')

    # Initialize portfolio data for each symbol
    for symbol in unique_symbols:
        if symbol not in portfolio.portfolio_data:
            symbol_info = unique_symbols_data.get(symbol, {})
            market_value_per_share = Decimal(str(symbol_info.get('price', '0')))
            portfolio.add_symbol(symbol, {
                'symbol': symbol,
                'transaction_shares': Decimal('0'),
                'shares_outstanding': Decimal('0'),
                'cost_basis_per_share' : Decimal('0'),
                'cost_basis_total' : Decimal('0'),
                'market_value_per_share': market_value_per_share,
                'market_value_total_pre_tax': Decimal('0'),
                'gain_or_loss_pre_tax_percent': Decimal('0'),
                'STCG_unrealized': Decimal('0'),
                'LTCG_unrealized': Decimal('0'),
                'CG_total_unrealized': Decimal('0'),
                'STCG_tax_unrealized': Decimal('0'),
                'LTCG_tax_unrealized': Decimal('0'),
                'CG_tax_offset_unrealized': Decimal('0'),
                'CG_total_tax_unrealized': Decimal('0'),
                'CG_total_post_tax': Decimal('0'),
                'market_value_post_tax': Decimal('0'),
                'return_percent_post_tax': Decimal('0'),
            })


        # ----------------------------------------------------------------------
    
    
    for transaction in transactions:
        symbol_data = portfolio.get_symbol_data(transaction.symbol)

        # If the current transaction = BOT... 
        if transaction.type == 'BOT':  
    
            # If the current transaction = BOT && shares outstanding > 0 ...
            if transaction.shares_outstanding > 0:

                # Cost basis and unrealized cap gains on the current transaction
                open_transaction_cost_basis_total = transaction.shares_outstanding * transaction.transaction_value_per_share
                open_transaction_gain_or_loss_unrealized = (transaction.shares_outstanding * symbol_data['market_value_per_share']) - open_transaction_cost_basis_total

                # If short-term, then...
                if transaction.timestamp > cutoff_date:
                    open_transaction_STCG_unrealized = open_transaction_gain_or_loss_unrealized
                    open_transaction_LTCG_unrealized = 0
                    # If a ST gain, then...
                    if open_transaction_STCG_unrealized > 0:
                        open_transaction_STCG_tax_unrealized = open_transaction_STCG_unrealized *  tax_rate_STCG
                        open_transaction_LTCG_tax_unrealized = 0
                        open_transaction_CG_tax_offset_unrealized = 0
                    # If a ST loss, then...
                    else:
                        open_transaction_STCG_tax_unrealized = 0
                        open_transaction_LTCG_tax_unrealized = 0
                        open_transaction_CG_tax_offset_unrealized = abs(open_transaction_STCG_unrealized *  tax_rate_STCG * tax_offset_coefficient)
                # If LT, then...
                else:
                    open_transaction_STCG_unrealized = 0
                    open_transaction_LTCG_unrealized = open_transaction_gain_or_loss_unrealized
                    # If a LT gain, then...
                    if open_transaction_LTCG_unrealized > 0:
                        open_transaction_STCG_tax_unrealized = 0
                        open_transaction_LTCG_tax_unrealized = open_transaction_LTCG_unrealized *  tax_rate_LTCG
                        open_transaction_CG_tax_offset_unrealized = 0
                    # If a LT loss, then...
                    else:
                        open_transaction_STCG_tax_unrealized = 0
                        open_transaction_LTCG_tax_unrealized = 0
                        open_transaction_CG_tax_offset_unrealized = abs(open_transaction_LTCG_unrealized *  tax_rate_LTCG * tax_offset_coefficient)
                
                open_transaction_CG_total_unrealized = open_transaction_STCG_unrealized + open_transaction_LTCG_unrealized  
                open_transaction_CG_total_tax_unrealized = open_transaction_STCG_tax_unrealized + open_transaction_LTCG_tax_unrealized  
                open_transaction_market_value_total_pre_tax =  transaction.shares_outstanding * symbol_data['market_value_per_share']
                open_transaction_gain_or_loss_pre_tax_percent_unrealized = open_transaction_market_value_total_pre_tax / open_transaction_cost_basis_total

                open_transaction_CG_total_post_tax_unrealized = open_transaction_CG_total_unrealized - open_transaction_CG_total_tax_unrealized
                open_transaction_market_value_post_tax = open_transaction_market_value_total_pre_tax - open_transaction_CG_total_tax_unrealized  
                open_transaction_return_percent_post_tax = (open_transaction_market_value_post_tax / open_transaction_cost_basis_total) - 1 
            
            # If the current transaction = BOT && shares outstanding == 0 ...
            else:
                open_transaction_cost_basis_total = 0
                open_transaction_STCG_unrealized = 0
                open_transaction_LTCG_unrealized = 0
                open_transaction_CG_total_unrealized = 0
                open_transaction_market_value_total_pre_tax = 0
                open_transaction_STCG_tax_unrealized = 0
                open_transaction_LTCG_tax_unrealized = 0
                open_transaction_CG_total_tax_unrealized = 0
                open_transaction_CG_tax_offset_unrealized = 0
                open_transaction_market_value_post_tax = 0

            # Increment data consolidated on symbol --------------------------------------
            
            # Symbol-level metrics: This is symbol-level data
            symbol_data['transaction_shares'] += transaction.transaction_shares
            symbol_data['shares_outstanding'] += transaction.shares_outstanding
            symbol_data['cost_basis_total'] += open_transaction_cost_basis_total
            
            symbol_data['STCG_unrealized'] += open_transaction_STCG_unrealized
            symbol_data['LTCG_unrealized'] += open_transaction_LTCG_unrealized
            symbol_data['CG_total_unrealized'] += open_transaction_CG_total_unrealized        

            symbol_data['market_value_total_pre_tax'] += open_transaction_market_value_total_pre_tax
            symbol_data['STCG_tax_unrealized'] += open_transaction_STCG_tax_unrealized
            symbol_data['LTCG_tax_unrealized'] += open_transaction_LTCG_tax_unrealized    
            symbol_data['CG_total_tax_unrealized'] += open_transaction_CG_total_tax_unrealized
            symbol_data['CG_tax_offset_unrealized'] += open_transaction_CG_tax_offset_unrealized
            
            symbol_data['market_value_post_tax'] += open_transaction_market_value_post_tax
            
            if symbol_data['shares_outstanding'] > 0:
                symbol_data['cost_basis_per_share'] = symbol_data['cost_basis_total'] / symbol_data['shares_outstanding']
                symbol_data['gain_or_loss_pre_tax_percent'] = symbol_data['CG_total_unrealized'] / symbol_data['cost_basis_total'] 
                symbol_data['return_percent_post_tax'] = (symbol_data['market_value_post_tax']/symbol_data['cost_basis_total']) - 1 

        
        #-------------------------------------------------------------------------
        

        # For share SALES        
        else:
            
            # If SLD, add the following txn metrics...
            transaction.CG_total_realized = transaction.STCG + transaction.LTCG
            transaction.cost_basis_total = transaction.transaction_value_total - transaction.STCG - transaction.LTCG
            transaction.gain_or_loss_pre_tax_percent = transaction.CG_total_realized / transaction.cost_basis_total
            transaction.STCG_tax_realized = max(transaction.STCG_tax, 0)
            transaction.LTCG_tax_realized = max(transaction.LTCG_tax, 0)
            transaction.CG_total_tax_realized = max(transaction.STCG * tax_rate_STCG + transaction.LTCG * tax_rate_LTCG, 0)
            transaction.CG_tax_offset_unrealized = max(-(transaction.STCG_tax + transaction.LTCG_tax), 0)
            transaction.market_value_post_tax = transaction.transaction_value_total - transaction.CG_total_tax_realized
            transaction.return_percent_post_tax = (transaction.market_value_post_tax / transaction.cost_basis_total) - 1


            # If SLD, add the following txn metrics...
            portfolio.sld_transaction_shares_total += transaction.transaction_shares
            portfolio.sld_transaction_cost_basis_total += transaction.cost_basis_total 
            portfolio.sld_transaction_STCG_total += transaction.STCG
            portfolio.sld_transaction_LTCG_total += transaction.LTCG            
            portfolio.sld_transaction_CG_total_realized_total += transaction.CG_total_realized      
            portfolio.sld_transaction_market_value_pre_tax_total += transaction.transaction_value_total
            
            # See below for cals. pertaining to: portfolio.sld_transaction_gain_or_loss_pre_tax_percent
            portfolio.sld_transaction_STCG_tax_total += transaction.STCG_tax_realized 
            portfolio.sld_transaction_LTCG_tax_total += transaction.LTCG_tax_realized
            portfolio.sld_transaction_tax_offset_total += transaction.CG_tax_offset_unrealized
            portfolio.sld_transaction_market_value_post_tax_total += transaction.market_value_post_tax 

            portfolio.sell_transactions.append(transaction) 
            
    # PORTFOLIO-LEVEL METRICS: This is total portfolio data shown at bottom of index tables    
    portfolio.sld_transaction_gain_or_loss_pre_tax_percent = ((portfolio.sld_transaction_market_value_pre_tax_total / portfolio.sld_transaction_cost_basis_total) - 1) if portfolio.sld_transaction_cost_basis_total else "-"
    portfolio.sld_transaction_return_percent_post_tax = ((portfolio.sld_transaction_market_value_post_tax_total / portfolio.sld_transaction_cost_basis_total) - 1) if portfolio.sld_transaction_cost_basis_total else "-"
    
    portfolio.cash = user.userprofile.cash 
    portfolio.cash_initial = user.userprofile.cash_initial
    logger.debug(f'running /process_user_transactions(user) ...  portfolio.cash is: { portfolio.cash }')

    # Step 3.5: Derive total portfolio cost basis, market value, and returns, all ex cash.
    for symbol, symbol_data in portfolio.portfolio_data.items():
        portfolio.portfolio_total_transaction_shares += symbol_data['transaction_shares']
        portfolio.portfolio_total_shares_outstanding += symbol_data['shares_outstanding']
        portfolio.portfolio_cost_basis_total += symbol_data['cost_basis_total']
        portfolio.portfolio_STCG_unrealized += symbol_data['STCG_unrealized']
        portfolio.portfolio_LTCG_unrealized += symbol_data['LTCG_unrealized']
        portfolio.portfolio_CG_unrealized += portfolio.portfolio_STCG_unrealized + portfolio.portfolio_LTCG_unrealized  
        portfolio.portfolio_market_value_total_pre_tax += symbol_data['market_value_total_pre_tax']
        portfolio.portfolio_STCG_tax_unrealized += symbol_data['STCG_tax_unrealized']
        portfolio.portfolio_LTCG_tax_unrealized += symbol_data['LTCG_tax_unrealized']
        portfolio.portfolio_total_tax_unrealized = portfolio.portfolio_STCG_tax_unrealized + portfolio.portfolio_LTCG_tax_unrealized
        portfolio.portfolio_CG_tax_offset_unrealized += symbol_data['CG_tax_offset_unrealized']

    portfolio.portfolio_cost_basis_per_share = portfolio.portfolio_cost_basis_total / portfolio.portfolio_total_shares_outstanding
    portfolio.portfolio_CG_total_unrealized = portfolio.portfolio_STCG_unrealized + portfolio.portfolio_LTCG_unrealized
    portfolio.portfolio_market_value_per_share = portfolio.portfolio_market_value_total_pre_tax / portfolio.portfolio_total_shares_outstanding
    portfolio.portfolio_market_value_total_pre_tax_incl_cash = portfolio.portfolio_market_value_total_pre_tax + user.userprofile.cash
    portfolio.portfolio_gain_or_loss_pre_tax_percent = (portfolio.portfolio_market_value_total_pre_tax / portfolio.portfolio_cost_basis_total) -1
    portfolio.portfolio_market_value_post_tax = portfolio.portfolio_market_value_total_pre_tax + min((-portfolio.portfolio_total_tax_unrealized + portfolio.portfolio_CG_tax_offset_unrealized),0)
    portfolio.portfolio_market_value_post_tax_incl_cash = portfolio.portfolio_market_value_post_tax + user.userprofile.cash
    portfolio.portfolio_return_percent_post_tax = (portfolio.portfolio_market_value_post_tax / portfolio.portfolio_cost_basis_total) -1
    
    # Below are calculations for total portfolio performance, incl. 
    # open positions + cash + sld transactions.
    portfolio.total_portfolio_transaction_shares = portfolio.portfolio_total_transaction_shares + portfolio.sld_transaction_shares_total
    portfolio.total_portfolio_STCG = portfolio.portfolio_STCG_unrealized + portfolio.sld_transaction_STCG_total
    portfolio.total_portfolio_LTCG = portfolio.portfolio_LTCG_unrealized + portfolio.sld_transaction_LTCG_total
    portfolio.total_portfolio_CG = portfolio.portfolio_CG_total_unrealized + portfolio.sld_transaction_CG_total_realized_total
    portfolio.total_portfolio_market_value_pre_tax = portfolio.portfolio_market_value_total_pre_tax_incl_cash + portfolio.sld_transaction_CG_total_realized_total
    portfolio.total_portfolio_gain_or_loss_pre_tax_percent = portfolio.total_portfolio_CG / portfolio.cash_initial  
    portfolio.total_portfolio_STCG_tax =  portfolio.portfolio_STCG_tax_unrealized + portfolio.sld_transaction_STCG_tax_total
    portfolio.total_portfolio_LTCG_tax =  portfolio.portfolio_LTCG_tax_unrealized + portfolio.sld_transaction_LTCG_tax_total
    portfolio.total_portfolio_CG_tax_total = portfolio.total_portfolio_STCG_tax + portfolio.total_portfolio_LTCG_tax  
    portfolio.total_portfolio_tax_offset = portfolio.portfolio_CG_tax_offset_unrealized + portfolio.sld_transaction_tax_offset_total 
    portfolio.total_portfolio_market_value_post_tax =  portfolio.total_portfolio_market_value_pre_tax + min((-portfolio.total_portfolio_CG_tax_total + portfolio.total_portfolio_tax_offset),0)
    portfolio.total_portfolio_market_value_post_tax_percent = (portfolio.total_portfolio_market_value_post_tax /  portfolio.cash_initial) - 1

    # return the portfolio object
    return portfolio

