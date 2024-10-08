from enum import Enum, auto
from abc import ABC, abstractmethod


class EventType(Enum):
    """Enum for different types of events that can be observed."""

    MARKET_DATA = auto()
    ORDER_BOOK = auto()
    SIGNAL = auto()
    ORDER_CREATED = auto()
    TRADE_EXECUTED = auto()
    EOD_EVENT = auto()

    # OLD
    POSITION_UPDATE = auto()
    ORDER_UPDATE = auto()
    ACCOUNT_UPDATE = auto()
    EQUITY_VALUE_UPDATE = auto()
    RISK_UPDATE = auto()
    TRADE_UPDATE = auto()
    TRADE_COMMISSION_UPDATE = auto()


class Subject:
    """Class representing a subject that can notify observers about various events."""

    def __init__(self):
        """Initialize the Subject with an empty observer dictionary."""
        # Maps EventType to observers interested in that event
        self._observers = {}

    def attach(self, observer: "Observer", event_type: EventType):
        """
        Attach an observer to a specific event type.

        Parameters:
        - observer (Observer): The observer to attach.
        - event_type (EventType): The event type to which the observer should be attached.
        """
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)

    def detach(self, observer: "Observer", event_type: EventType):
        """
        Detach an observer from a specific event type.

        Parameters:
        - observer (Observer): The observer to detach.
        - event_type (EventType): The event type from which the observer should be detached.
        """
        if (
            event_type in self._observers
            and observer in self._observers[event_type]
        ):
            self._observers[event_type].remove(observer)

    def notify(self, event_type: EventType, *args, **kwargs):
        """
        Notify all observers about an event, passing dynamic data.

        Parameters:
        - event_type (EventType): The event type that has occurred.
        - *args: Additional positional arguments to be passed to the observers.
        - **kwargs: Additional keyword arguments to be passed to the observers.
        """
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                observer.handle_event(self, event_type, *args, **kwargs)


class Observer(ABC):
    """Abstract base class for observers that need to respond to subject events."""

    @abstractmethod
    def handle_event(
        self, subject: Subject, event_type: EventType, *args, **kwargs
    ):
        """
        Handle the event based on the type.

            Parameters:
            - subject (Subject): The subject that triggered the event.
                - event_type (EventType): The type of event that was triggered.
        """

    pass
