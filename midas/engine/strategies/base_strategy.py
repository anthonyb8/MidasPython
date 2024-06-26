import logging
import pandas as pd
import importlib.util
from typing import Type
from queue import Queue
from typing import List, Union
from abc import ABC, abstractmethod
from midas.engine.order_book import OrderBook
from midas.shared.signal import TradeInstruction
from midas.engine.portfolio import PortfolioServer
from midas.engine.events import  SignalEvent, MarketEvent


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies, providing a framework for handling market data,
    generating signals, and managing orders. Designed to be extended with specific strategy implementations.
    """
    def __init__(self, portfolio_server: PortfolioServer, order_book: OrderBook, logger: logging.Logger, event_queue: Queue):
        """
        Initialize the strategy with necessary components for data handling and event management.

        Parameters:
        - portfolio_server (PortfolioServer): The server handling the portfolio operations.
        - order_book (OrderBook): The book that maintains and updates market data.
        - logger (logging.Logger): Logger for recording activity and debugging.
        - event_queue (Queue): Queue for dispatching events like signals and orders.
        """
        self.logger = logger
        self.order_book = order_book
        self._event_queue = event_queue 
        self.portfolio_server = portfolio_server

        self.trade_id = 1
        self.historical_data = None

    @abstractmethod
    def prepare(self):
        """ 
        Perform any initial setup required before the strategy can start processing events.
        """
        pass
    
    def on_market_data(self, event: MarketEvent):
        """
        Callback to handle and process new market data events.

        Parameters:
        - event (MarketEvent): The market event containing new data to be processed.
        """
        if not isinstance(event, MarketEvent):
            raise TypeError("'event' must be of type Market Event instance.")

        self.handle_market_data()

    @abstractmethod
    def handle_market_data(self):
        """
        Process the latest market data and generate corresponding trading signals.
        This method needs to be implemented by subclasses to specify the strategy's logic.
        """
        pass

    def set_signal(self, trade_instructions: List[TradeInstruction], timestamp: int):
        """
        Creates and queues a signal event based on the strategy's trade instructions.

        Parameters:
        - trade_instructions (List[TradeInstruction]): Specific trade instructions to execute.
        - timestamp (int): The time at which the signal is generated.
        """
        try:
            signal_event = SignalEvent(timestamp, trade_instructions)
            self._event_queue.put(signal_event)
        except (ValueError, TypeError) as e:
            raise RuntimeError(f"Failed to create or queue SignalEvent due to input error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error when creating or queuing SignalEvent: {e}") from e

    @abstractmethod
    def _entry_signal(self):
        """
        Define the logic to generate entry signals for trades based on market data.
        This method should specify when and how trades should be entered.
        """
        pass

    @abstractmethod
    def _exit_signal(self):
        """
        Define the logic to generate exit signals for closing or adjusting trades based on market conditions.
        This method should specify when and how trades should be exited.
        """
        pass

    @abstractmethod
    def _asset_allocation(self):
        """
        Define how the strategy allocates assets across different instruments or markets.
        This method should detail the asset distribution method used by the strategy.
        """
        pass

    def generate_signals(self):
        """
        Generate signals based on historical data for backtesting purposes.
        This method typically involves a vectorized approach to signal generation.
        """
        pass

    @abstractmethod
    def get_strategy_data(self) -> pd.DataFrame:
        """
        Get strategy-specific data.
        """
        pass 

def load_strategy_class(module_path: str, class_name: str) -> Type[BaseStrategy]:
    """
    Dynamically loads a strategy class from a given module path and class name.
    """
    spec = importlib.util.spec_from_file_location("module.name", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy_class = getattr(module, class_name)
    if not issubclass(strategy_class, BaseStrategy):
        raise ValueError(f"Strategy class {class_name} is not a subclass of BaseStrategy.")
    return strategy_class