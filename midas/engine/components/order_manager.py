from ibapi.contract import Contract
from typing import List
from midas.symbol import SymbolMap
from midas.engine.components.order_book import OrderBook
from midas.signal import SignalInstruction
from midas.orders import Action, BaseOrder
from midas.engine.components.portfolio_server import PortfolioServer
from midas.engine.events import SignalEvent, OrderEvent
from midas.utils.logger import SystemLogger
from midas.engine.components.observer.base import Subject, Observer, EventType


class OrderExecutionManager(Subject, Observer):
    """
    Manages order execution based on trading signals, interfacing with a portfolio server and order book.
    """

    def __init__(
        self,
        symbols_map: SymbolMap,
        order_book: OrderBook,
        portfolio_server: PortfolioServer,
    ):
        """
        Initialize the OrderManager with necessary components for managing orders.

        Parameters:
        - symbols_map (Dict[str, Symbol]): Mapping of symbol strings to Symbol objects.
        - event_queue (Queue): Event queue for sending events to other parts of the system.
        - order_book (OrderBook): Reference to the order book for price lookups.
        - portfolio_server (PortfolioServer): Reference to the portfolio server for managing account and positions.
        - logger (logging.Logger): Logger for logging messages.
        """
        super().__init__()
        self.logger = SystemLogger.get_logger()
        self.portfolio_server = portfolio_server
        self.order_book = order_book
        self.symbols_map = symbols_map

    def handle_event(
        self,
        subject: Subject,
        event_type: EventType,
        event: SignalEvent,
    ) -> None:
        """
        Handle received signal events by initiating trade actions if applicable.

        Parameters:
        - event (SignalEvent): The signal event containing trade instructions.
        """
        if event_type == EventType.SIGNAL:
            self.logger.info(event)
            if not isinstance(event, SignalEvent):
                raise TypeError(
                    "'event' must be of type SignalEvent instance."
                )

            trade_instructions = event.instructions
            timestamp = event.timestamp

            # Get a list of tickers in active orders
            active_orders_tickers = (
                self.portfolio_server.get_active_order_tickers()
            )
            self.logger.info(f"Active order tickers {active_orders_tickers}")

            # Check if any of the tickers in trade_instructions are in active orders or positions
            if any(
                trade.instrument in active_orders_tickers
                for trade in trade_instructions
            ):
                self.logger.info(
                    "One or more tickers in the trade instructions have active orders; ignoring signal."
                )
                return
            else:
                self._handle_signal(timestamp, trade_instructions)

    def _handle_signal(
        self, timestamp: int, trade_instructions: List[SignalInstruction]
    ) -> None:
        """
        Process trade instructions to generate orders, checking if sufficient capital is available.

        Parameters:
        - timestamp (int): The time at which the signal was generated.
        - trade_capital (Union[int, float]): The amount of capital allocated for trading.
        - trade_instructions (List[SignalInstruction]): List of trading instructions to be processed.
        """
        # Create and Validate Orders
        orders = []
        total_capital_required = 0

        for trade in trade_instructions:
            self.logger.info(trade)
            symbol = self.symbols_map.map[trade.instrument]
            order = self._create_order(trade)
            current_price = self.order_book.retrieve(symbol.instrument_id)
            order_cost = symbol.cost(order.quantity, current_price)

            order_details = {
                "timestamp": timestamp,
                "trade_id": trade.trade_id,
                "leg_id": trade.leg_id,
                "action": trade.action,
                "contract": symbol.contract,
                "order": order,
            }

            orders.append(order_details)
            total_capital_required += order_cost

        for order in orders:
            if (
                order["action"] in [Action.SELL, Action.COVER]
                or total_capital_required <= self.portfolio_server.capital
            ):
                self._set_order(
                    order["timestamp"],
                    order["trade_id"],
                    order["leg_id"],
                    order["action"],
                    order["contract"],
                    order["order"],
                )
            else:
                self.logger.info("Not enough capital to execute all orders")

    def _create_order(self, trade_instruction: SignalInstruction) -> BaseOrder:
        """
        Create an order object based on specified parameters.

        Parameters:
        - order_type (OrderType): The type of order to create (MARKET, LIMIT, STOPLOSS).
        - action (Action): The action to be taken (BUY, SELL, etc.).
        - quantity (float): The quantity of the order.
        - limit_price (float, optional): The limit price for limit orders.
        - aux_price (float, optional): The auxiliary price for stop-loss orders.

        Returns:
        - BaseOrder: The created order object, ready for execution.
        """
        try:
            return trade_instruction.to_order()
        except (ValueError, TypeError) as e:
            raise RuntimeError(f"Failed to create order due to input: {e}")

    def _set_order(
        self,
        timestamp: int,
        trade_id: int,
        leg_id: int,
        action: Action,
        contract: Contract,
        order: BaseOrder,
    ) -> None:
        """
        Queue an OrderEvent based on the order details.

        Parameters:
        - timestamp (int): The timestamp when the order was initiated.
        - trade_id (int): The trade identifier.
        - leg_id (int): The leg identifier of the trade.
        - action (Action): The action of the trade (BUY, SELL, etc.).
        - contract (Contract): The contract involved in the order.
        - order (BaseOrder): The order to be executed.
        """
        try:
            order_event = OrderEvent(
                timestamp=timestamp,
                trade_id=trade_id,
                leg_id=leg_id,
                action=action,
                contract=contract,
                order=order,
            )
            self.notify(EventType.ORDER_CREATED, order_event)
        except (ValueError, TypeError) as e:
            raise RuntimeError(f"Failed to set OrderEvent due to input : {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error setting OrderEvent: {e}")
