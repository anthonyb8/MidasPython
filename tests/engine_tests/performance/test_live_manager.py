import unittest
import numpy as np
import pandas as pd
from contextlib import ExitStack
from ibapi.contract import Contract
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from pandas.testing import assert_frame_equal
from midas.shared.signal import TradeInstruction
from midas.shared.orders import Action, OrderType
from midas.shared.trade import Trade, ExecutionDetails
from midas.engine.command.parameters import Parameters
from midas.shared.account import EquityDetails, Account
from midas.engine.performance.live.manager import LivePerformanceManager
from midas.shared.market_data import MarketData, BarData, QuoteData, MarketDataType
from midas.engine.events import MarketEvent, OrderEvent, SignalEvent, ExecutionEvent

class TestPerformanceManager(unittest.TestCase):    
    def setUp(self) -> None:
        # Mock methods
        self.mock_db_client = Mock()
        self.mock_logger = Mock()

        # Test parameter object
        self.mock_parameters = Parameters(
            strategy_name="cointegrationzscore", 
            capital= 100000, 
            data_type= MarketDataType.BAR, 
            train_start= "2018-05-18", 
            train_end= "2023-01-18", 
            test_start= "2023-01-19", 
            test_end= "2024-01-19", 
            tickers= ["HE.n.0", "ZC.n.0"], 
        )

        # Performance manager instance
        self.performance_manager = LivePerformanceManager(self.mock_db_client, self.mock_logger, self.mock_parameters)

        # Test signal event
        self.valid_trade1 = TradeInstruction(ticker = 'AAPL',
                                                order_type = OrderType.MARKET,
                                                action = Action.LONG,
                                                trade_id = 2,
                                                leg_id =  5,
                                                weight = 0.5,
                                                quantity=2)
        self.valid_trade2 = TradeInstruction(ticker = 'TSLA',
                                                order_type = OrderType.MARKET,
                                                action = Action.LONG,
                                                trade_id = 2,
                                                leg_id =  6,
                                                weight = 0.5,
                                                quantity=2)
        self.valid_trade_instructions = [self.valid_trade1,self.valid_trade2]
                        
        self.signal_event = SignalEvent(np.uint64(1651500000), self.valid_trade_instructions)

        # Valid performance data
        self.mock_static_stats = [{
            "total_return": 10.0,
            "total_trades": 5,
            "total_fees": 2.5
        }]
        self.mock_trades =  {
            "timestamp": "2024-01-01", 
            "ticker": "AAPL", 
            "quantity": "1.000",
            "cumQty": "1.00",
            "price": 99.99,
            "AvPrice": 99.99,
            "action": "BUY",
            "cost":0,
            "currency": "USD", 
        }
        self.mock_signals =  [{
            "timestamp": "2023-01-03T00:00:00+0000", 
            "trade_instructions": [{
                "ticker": "AAPL", 
                "action": "BUY", 
                "trade_id": 1, 
                "leg_id": 1, 
                "weight": 0.05
            }, 
            {
                "ticker": "MSFT", 
                "action": "SELL", 
                "trade_id": 1, 
                "leg_id": 2, 
                "weight": 0.05
            }]
        }]

    # Basic Validation
    def test_update_trades_new_trade_valid(self):
        trade_id = 12345
        
        # Test
        self.performance_manager.update_trades(trade_id, self.mock_trades)

        # Validate
        self.assertEqual(self.performance_manager.trades[trade_id], self.mock_trades)
        self.mock_logger.info.assert_called_once()
    
    def test_update_trades_old_trade_valid(self):  
        trade_id = 12345
        self.performance_manager.update_trades(trade_id, self.mock_trades)   

        # Test
        self.mock_trades["action"] = "SELL"   
        self.performance_manager.update_trades(trade_id, self.mock_trades)   
        
        # Validate
        self.assertEqual(self.performance_manager.trades[trade_id], self.mock_trades)
        self.assertEqual(self.performance_manager.trades[trade_id]["action"], "SELL")
        self.assertEqual(len(self.performance_manager.trades), 1)
        self.mock_logger.info.assert_called
    
    def test_output_trades(self):
        trade_id = 12345

        # Test
        self.performance_manager.update_trades(trade_id, self.mock_trades)   

        # Validate
        self.mock_logger.info.assert_called_once_with("Trade Updated: 12345\nDetails: {'timestamp': '2024-01-01', 'ticker': 'AAPL', 'quantity': '1.000', 'cumQty': '1.00', 'price': 99.99, 'AvPrice': 99.99, 'action': 'BUY', 'cost': 0, 'currency': 'USD'}")

    def test_update_trade_commission(self):
        trade_id = 12345
        self.performance_manager.update_trades(trade_id, self.mock_trades)   

        # Test 
        self.performance_manager.update_trade_commission(trade_id, 2.97)

        # Validate
        self.mock_logger.info.assert_called
        self.assertEqual(self.performance_manager.trades[trade_id]["fees"], 2.97)
    
    def test_update_signals_valid(self):        
        # Test
        self.performance_manager.update_signals(self.signal_event)

        # Validate
        self.assertEqual(self.performance_manager.signals[0], self.signal_event.to_dict())
        self.mock_logger.info.assert_called_once()
    
    def test_output_signal(self):
        # Test
        self.performance_manager.update_signals(self.signal_event)

        # Validate
        self.mock_logger.info.assert_called_once_with("\nSIGNALS UPDATED: \n  Timestamp: 1651500000 \n  Trade Instructions: \n    {'ticker': 'AAPL', 'order_type': 'MKT', 'action': 'LONG', 'trade_id': 2, 'leg_id': 5, 'weight': 0.5, 'quantity': 2, 'limit_price': '', 'aux_price': ''}\n    {'ticker': 'TSLA', 'order_type': 'MKT', 'action': 'LONG', 'trade_id': 2, 'leg_id': 6, 'weight': 0.5, 'quantity': 2, 'limit_price': '', 'aux_price': ''}\n")

    def test_update_equity_new_valid(self):
        equity = EquityDetails(timestamp= 165500000, equity_value = 10000000.99)

        # Test
        self.performance_manager.update_equity(equity)

        # Validate
        self.assertEqual(self.performance_manager.equity_value[0], equity)
        self.mock_logger.info.assert_called_once_with("\nEQUITY UPDATED: \n  {'timestamp': 165500000, 'equity_value': 10000000.99}\n")
    
    def test_update_equity_old_valid(self):
        equity = EquityDetails(timestamp= 165500000, equity_value = 10000000.99)
        self.performance_manager.equity_value.append(equity)

        # Test
        self.performance_manager.update_equity(equity)
        
        # Validate
        self.assertEqual(len(self.performance_manager.equity_value), 1)
        self.assertFalse(self.mock_logger.info.called)
        
    def test_create_live_session(self):
        # Signals
        self.performance_manager.update_signals(self.signal_event)

        # Trades
        trades = {123: {"timestamp": "2024-01-01", "ticker": "AAPL", "quantity": "1.000","cumQty": "1.00","price": 99.99,"AvPrice": 99.99,"action": "BUY","cost":0,"currency": "USD"},
                  1234: {"timestamp": "2024-01-01", "ticker": "AAPL", "quantity": "1.000","cumQty": "1.00","price": 99.99,"AvPrice": 99.99,"action": "BUY","cost":0,"currency": "USD"},
                  12345: {"timestamp": "2024-01-01", "ticker": "AAPL", "quantity": "1.000","cumQty": "1.00","price": 99.99,"AvPrice": 99.99,"action": "BUY","cost":0,"currency": "USD"}}
        self.performance_manager.trades = trades

        # Account
        self.performance_manager.account_log = [{'BuyingPower': 2563178.43, 'Currency': 'USD', 'ExcessLiquidity': 768953.53, 'FullAvailableFunds': 768953.53, 'FullInitMarginReq': 263.95, 'FullMaintMarginReq': 263.95, 'FuturesPNL': -367.5, 'NetLiquidation': 769217.48, 'TotalCashBalance': -10557.9223, 'UnrealizedPnL': 0.0, 'Timestamp': '2024-04-10T13:12:24.127576'},
                                            {'BuyingPower': 2541533.29, 'Currency': 'USD', 'ExcessLiquidity': 763767.68, 'FullAvailableFunds': 762459.99, 'FullInitMarginReq': 6802.69, 'FullMaintMarginReq': 5495.0, 'FuturesPNL': -373.3, 'NetLiquidation': 769262.67, 'TotalCashBalance': 768538.5532, 'UnrealizedPnL': -11.73, 'Timestamp': '2024-04-10T13:13:43.160076'}]

        # Test 
        self.performance_manager.save()
        live_summary = self.performance_manager.live_summary
        
        # Validate
        self.assertEqual(live_summary.parameters, self.mock_parameters.to_dict())
        self.assertEqual(live_summary.signal_data, [self.signal_event.to_dict()])
        self.assertEqual(live_summary.trade_data ,  list(trades.values()))

        # Validate account
        expected_account = [{'start_BuyingPower': '2563178.4300', 'currency': 'USD', 'start_ExcessLiquidity': '768953.5300', 'start_FullAvailableFunds': '768953.5300', 'start_FullInitMarginReq': '263.9500', 'start_FullMaintMarginReq': '263.9500', 'start_FuturesPNL': '-367.5000', 'start_NetLiquidation': '769217.4800', 'start_TotalCashBalance': '-10557.9223', 
                             'start_UnrealizedPnL': '0.0000', 'start_timestamp': '2024-04-10T13:12:24.127576', 'end_BuyingPower': '2541533.2900', 'end_ExcessLiquidity': '763767.6800', 'end_FullAvailableFunds': '762459.9900', 'end_FullInitMarginReq': '6802.6900', 'end_FullMaintMarginReq': '5495.0000', 'end_FuturesPNL': '-373.3000', 
                             'end_NetLiquidation': '769262.6700', 'end_TotalCashBalance': '768538.5532', 'end_UnrealizedPnL': '-11.7300', 'end_timestamp': '2024-04-10T13:13:43.160076'}]

        self.assertEqual(live_summary.account_data, expected_account)


if __name__ == "__main__":
    unittest.main()