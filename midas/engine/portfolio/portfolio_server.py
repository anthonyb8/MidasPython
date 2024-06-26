import logging
from typing import Dict
from ibapi.contract import Contract
from midas.shared.symbol import Symbol
from midas.client import DatabaseClient
from midas.shared.account import Account
from midas.shared.positions import Position
from midas.engine.observer import Subject, EventType
from midas.shared.active_orders import ActiveOrder

class PortfolioServer(Subject):
    """
    Manages and updates the state of the portfolio including positions, orders, and account details, notifying observers of changes.
    """
    def __init__(self, symbols_map: Dict[str, Symbol], logger: logging.Logger, database : DatabaseClient = None):
        """
        Initializes a new instance of the PortfolioServer.

        Parameters:
        - symbols_map (Dict[str, Symbol]): Mapping of symbol strings to Symbol objects.
        - logger (logging.Logger): Logger for logging messages.
        - database (DatabaseClient, optional): Client for database operations.
        """
        super().__init__()
        self.symbols_map = symbols_map
        self.logger = logger
        self.database = database
  
        # self.capital = None
        self.account : Account
        self.positions : Dict[str, Position] = {}
        self.active_orders : Dict[int, ActiveOrder] = {}
        self.pending_positions_update = set()

    @property
    def capital(self):
        return self.account.capital

    @property
    def get_positions(self):
        """Returns the current positions in the portfolio."""
        return self.positions
    
    @property
    def get_account(self):
        """Returns the account details of the portfolio."""
        return self.account
    
    @property
    def get_active_orders(self):
        """Returns the active orders in the portfolio."""
        return self.active_orders
    
    def get_active_order_tickers(self) -> list:
        """
        Retrieves a list of tickers that currently have active orders.

        Returns:
        - List[str]: List of tickers with active orders.
        """
        active_order_tickers = [order["symbol"] for id, order in self.active_orders.items()]
        
        # Combine with pending position updates and remove duplicates
        combined_tickers = list(set(active_order_tickers + list(self.pending_positions_update)))
        return combined_tickers
    
    def update_positions(self, contract: Contract, new_position: Position) -> None:
        """
        Updates the position for a given contract.

        Parameters:
        - contract (Contract): The contract associated with the position.
        - new_position (Position): The new position to be updated.
        """
        # Check if this position exists and is equal to the new position
        if contract.symbol in self.positions:
            if new_position.quantity == 0:
                del self.positions[contract.symbol]
            else: # Same position duplicated, no need to log or notify
                return
        else:
            # Update the position
            self.positions[contract.symbol] = new_position
        
        # Notify listener and log 
        self.pending_positions_update.discard(contract.symbol)
        self.notify(EventType.POSITION_UPDATE)  # update database
        self.logger.info(f"\nPOSITIONS UPDATED: \n{self._output_positions()}")

    def _output_positions(self) -> str:
        """
        Generates a string representation of all positions for logging.

        Returns:
        - str: String representation of positions.
        """
        string =""
        for contract, position in self.positions.items():
            string += f"  {contract}: {position.pretty_print()}\n"
        return string
    
    def update_orders(self, order: ActiveOrder) -> None:
        """
        Updates the status of an order in the portfolio.

        Parameters:
        - order (ActiveOrder): The order to be updated.
        """
        # If the status is 'Cancelled' and the order is present in the dict, remove it
        if order['status'] == 'Cancelled' and order['orderId'] in self.active_orders:
            del self.active_orders[order['orderId']]
        elif order['status'] == 'Filled' and order['orderId'] in self.active_orders:
            self.pending_positions_update.add(order["symbol"])
            del self.active_orders[order['orderId']]
        # If not cancelled, either update the existing order or add a new one
        elif order['status'] != 'Cancelled' and order['status'] != 'Filled':
            if order['orderId'] not in self.active_orders:
                self.active_orders[order['orderId']] = order
            else:
                self.active_orders[order['orderId']].update(order)
        
        self.notify(EventType.ORDER_UPDATE)  # udpate dataabase
        self.logger.info(f"\nORDERS UPDATED: \n{self._ouput_orders()}")

    def _ouput_orders(self) -> str:        
        """
        Generates a string representation of all active orders for logging.

        Returns:
        - str: String representation of active orders.
        """
        string =""
        for permId, order in self.active_orders.items():
            string += f" {order} \n"
        return string

    def update_account_details(self, account_details: Account) -> None:
        """
        Updates the account details in the portfolio.

        Parameters:
        - account_details (AccountDetails): The updated account details.
        """
        self.account = account_details
        self.notify(EventType.ACCOUNT_DETAIL_UPDATE)  
        self.logger.info(f"\nACCOUNT UPDATED: \n{self.account.pretty_print()}")
    

