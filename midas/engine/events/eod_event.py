from datetime import date
from dataclasses import dataclass, field


@dataclass
class EODEvent:
    """
    Represents an End-of-Day (EOD) event, used to trigger end-of-day processing such as
    mark-to-market evaluations and summary calculations.

    Attributes:
    - timestamp (datetime.date): The date for for whcih it is the end-of-day moment.
    - type (str): Automatically set to 'End-of-day' to signify the type of event.
    """

    timestamp: date
    type: str = field(init=False, default="END-OF-DAY")

    def __post_init__(self):
        # Type Check
        if not isinstance(self.timestamp, date):
            raise TypeError(
                f"'timestamp' should be an datetime.date instance, got {type(self.timestamp).__name__}."
            )

    def __str__(self) -> str:
        string = f"\n{self.type} EVENT:\n  Timestamp: {self.timestamp}\n"
        return string
