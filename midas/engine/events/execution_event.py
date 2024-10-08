from ibapi.contract import Contract
from midas.orders import Action
from midas.trade import Trade
from dataclasses import dataclass, field


@dataclass
class ExecutionEvent:
    """
    Represents an event triggered after the execution of a trade order in a trading system, capturing the
    details of the trade execution.

    This event is vital for tracking trade executions, allowing the system to update portfolios, execute risk management
    protocols, and provide transaction reports. It includes detailed information about the trade, the involved contract,
    and the type of action performed.

    Attributes:
    - timestamp (int): The UNIX timestamp in nanoseconds when the execution occurred.
    - trade_details (Trade): Trade object detailing the execution of the trade, including price, volume, and other relevant metrics.
    - action (Action): The type of action (e.g., BUY, SELL) that was executed.
    - contract (Contract): The contract object detailing the financial instrument involved in the trade.
    - type (str): The type of the event, set to 'EXECUTION' by default.
    """

    timestamp: int
    trade_details: Trade
    action: Action
    contract: Contract
    type: str = field(init=False, default="EXECUTION")

    def __post_init__(self):
        # Type Check
        if not isinstance(self.timestamp, int):
            raise TypeError("'timestamp' field must be of type int.")
        if not isinstance(self.action, Action):
            raise TypeError("'action' field must be of type Action enum.")
        if not isinstance(self.trade_details, Trade):
            raise TypeError(
                "'trade_details' field must be of type Trade instance."
            )
        if not isinstance(self.contract, Contract):
            raise TypeError(
                "'contract' field must be of type Contract instance."
            )

    def __str__(self) -> str:
        return (
            f"\n{self.type} EVENT:\n"
            f"  Timestamp: {self.timestamp}\n"
            f"  Action: {self.action}\n"
            f"  Contract: {self.contract}\n"
            f"  Execution Details: {self.trade_details.to_dict()}\n"
        )
