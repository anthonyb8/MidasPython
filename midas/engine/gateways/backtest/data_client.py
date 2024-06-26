import threading
import numpy as np
import pandas as pd
from typing import List
from queue import Queue
from decimal import Decimal
from dateutil import parser
from datetime import datetime
from midas.client import DatabaseClient
from midas.shared.utils import unix_to_iso
from midas.engine.order_book import OrderBook
from midas.engine.events import MarketEvent, EODEvent
from quantAnalytics.dataprocessor import DataProcessor
from midas.shared.market_data import BarData, QuoteData

class DataClient(DatabaseClient):
    """
    Manages data fetching, processing, and streaming for trading simulations, extending the DatabaseClient for specific trading data operations.

    This class is responsible for interacting with the database to fetch historical market data,
    processing it according to specified parameters, and streaming it to simulate live trading conditions in a backtest environment.

    Attributes:
    - event_queue (Queue): The queue used for posting market data and end-of-day events.
    - data_client (DatabaseClient): A client class based on a Django Rest-Framework API for interacting with the database.
    - order_book (OrderBook): The order book where market data is posted for trading operations.
    """
    def __init__(self, event_queue:Queue, data_client:DatabaseClient, order_book:OrderBook,  eod_event_flag: threading.Event):
        """
        Initializes the DataClient with the necessary components for market data management.

        Parameters:
        - event_queue (Queue): The main event queue for posting data-related events.
        - data_client (DatabaseClient): The database client used for retrieving market data.
        - order_book (OrderBook): The order book where the market data will be used for trading operations.
        """
        self.event_queue = event_queue
        self.data_client = data_client
        self.order_book = order_book
        self.eod_event_flag = eod_event_flag
        if self.eod_event_flag:
            self.eod_event_flag.set()
        
        # Data 
        self.data : pd.DataFrame
        self.unique_timestamps : list
        self.next_date = None
        self.current_date_index = 0
        self.current_day = None

    def get_data(self, tickers:List[str], start_date:str, end_date:str, missing_values_strategy:str='fill_forward') -> bool:
        """
        Retrieves historical market data from the database and initializes the data processing.

        Parameters:
        - tickers (List[str]): A list of ticker symbols (e.g., ['AAPL', 'MSFT']).
        - start_date (str): The start date for the data retrieval in ISO format 'YYYY-MM-DD'.
        - end_date (str): The end date for the data retrieval in ISO format 'YYYY-MM-DD'.
        - missing_values_strategy (str): Strategy to handle missing values, either 'drop' or 'fill_forward'

        Returns:
        - bool: True if data retrieval and initial processing are successful.
        """
        # Type Checks
        if isinstance(tickers, list):
            if not all(isinstance(ticker, str) for ticker in tickers):
                raise TypeError("All items in 'tickers' must be of type string.")
        else:
            raise TypeError("'tickers' must be a list of strings.")
        
        if not isinstance(missing_values_strategy, str) or missing_values_strategy not in ['fill_forward', 'drop']:
            raise ValueError("'missing_value_strategy' must either 'fill_forward' or 'drop' of type str.")

        self._validate_timestamp_format(start_date)
        self._validate_timestamp_format(end_date)

        # Get data from backend
        response = self.data_client.get_bar_data(tickers=tickers, start_date=start_date, end_date=end_date)

        # Process the data
        data = pd.DataFrame(response)
        data.drop(columns=['id'], inplace=True)
        DataProcessor.check_duplicates(data)
        data = DataProcessor.handle_null(data, missing_values_strategy)
        self.data = self._process_bardata(data)
                
        # Storing unique dates if needed
        self.unique_timestamps = self.data['timestamp'].unique().tolist()
        
        return True

    def _validate_timestamp_format(self, timestamp:str) -> None:
        """
        Validates the format of the timestamp string for querying data.

        Parameters:
        - timestamp (str): The timestamp string to validate.
        """
        # Timestamp format check for ISO 8601
        try:
            # This attempts to parse the timestamp according to the ISO 8601 format.
            datetime.fromisoformat(timestamp)
        except ValueError:
            raise ValueError("Invalid timestamp format. Required format: YYYY-MM-DDTHH:MM:SS")
        except TypeError:
            raise TypeError("'timestamp' must be of type str.")

    def _process_bardata(self, data:pd.DataFrame) -> pd.DataFrame:
        """
        Processes raw bar data into a format suitable for the trading simulation.

        Parameters:
        - data (pd.DataFrame): The raw market data.
        """

        # Convert the 'timestamp' column from datetime to Unix time (seconds since epoch)
        data['timestamp'] = data['timestamp'].astype(np.uint64)
        data['open'] = data['open'].apply(Decimal)
        data['high'] = data['high'].apply(Decimal)
        data['low'] = data['low'].apply(Decimal)
        data['close'] = data['close'].apply(Decimal)
        data['volume'] = data['volume'].astype(np.uint64)

        # Sorting the DataFrame by the 'timestamp' column in ascending order
        return  data.sort_values(by='timestamp', ascending=True).reset_index(drop=True)

    # --  SIMULATE DATA STREAM -- 
    def data_stream(self) -> bool:
        """
        Simulates a market data stream by iterating through unique timestamps and posting market data to the order book.

        Returns:
        - bool: False when all data has been streamed, True otherwise.
        """

        if self.current_date_index >= len(self.unique_timestamps):
            return False  # No more unique dates
            
        # Update the next_date here
        self.next_date = self.unique_timestamps[self.current_date_index]
        iso = unix_to_iso(self.next_date)
        next_day = parser.parse(iso).date()

        if self.current_day is None or next_day != self.current_day:
            if self.current_day is not None:
                # Perform EOD operations for the previous day
                self.eod_event_flag.clear()
                self._process_eod(self.current_day)

            # Update the current day
            self.current_day = next_day 

        # Non-blocking wait with timeout
        while not self.eod_event_flag.is_set():
            self.eod_event_flag.wait(timeout=0.1)
            if not self.event_queue.empty():
                return True                   
        
        # Update market data            
        self._set_market_data()

        # Iterate to next date index 
        self.current_date_index += 1

        return True

    def _process_eod(self, current_day):
        """
        Processes End-of-Day operations.

        Parameters:
        - current_day (datetime.date): The current day to process EOD operations.
        """
        self.event_queue.put(EODEvent(timestamp=current_day))
    
    def _get_latest_data(self) -> pd.DataFrame:
        """
        Retrieves the most recent bar data for all symbols.

        Returns:
        - pd.DataFrame: The latest bar data.
        """
        return self.data[self.data['timestamp'] == self.next_date]

    def _set_market_data(self):
        """
        Posts the latest market data to the order book for trading simulation.
        """
        latest_data_batch = self._get_latest_data()
        result_dict = {}
        for idx, row in latest_data_batch.iterrows():
            ticker = row['symbol']
            result_dict[ticker] = BarData(ticker=ticker,
                                            timestamp=np.uint64(row['timestamp']),
                                            open=row['open'],
                                            high=row['high'],            
                                            low=row['low'],
                                            close=row['close'],
                                            volume=np.uint64(row['volume']))
        
        self.order_book.update_market_data(data=result_dict, timestamp=np.uint64(self.next_date))

        




