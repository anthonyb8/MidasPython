import unittest
import threading
from ibapi.contract import Contract
from unittest.mock import patch, Mock
from midas.engine.gateways.live.contract_manager import ContractManager
from midas.shared.symbol import Future, Equity, Currency, Venue, Industry, ContractUnits
class TestContractManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from midas.engine.gateways.live.contract_manager import ContractManager

    def setUp(self) -> None:
        # Mock methods
        self.mock_logger = Mock()
        self.mock_client = Mock()
        self.mock_client.app = Mock()

        # Contract manager instance
        self.contract_manager = ContractManager(client_instance=self.mock_client, logger=self.mock_logger)
        self.contract_manager.app.validate_contract_event = threading.Event()
        
        # Test symbols
        self.symbols_map = {'HEJ4' : Future(ticker = "HEJ4",
                                            data_ticker = "HE.n.0",
                                            currency = Currency.USD,  
                                            exchange = Venue.CME,  
                                            fees = 0.85,  
                                            initial_margin =4564.17,
                                            quantity_multiplier=40000,
                                            price_multiplier=0.01,
                                            product_code="HE",
                                            product_name="Lean Hogs",
                                            industry=Industry.AGRICULTURE,
                                            contract_size=40000,
                                            contract_units=ContractUnits.POUNDS,
                                            tick_size=0.00025,
                                            min_price_fluctuation=10,
                                            continuous=False,
                                            lastTradeDateOrContractMonth="202404"),
                                    'AAPL' : Equity(ticker="AAPL",
                                                    currency = Currency.USD  ,
                                                    exchange = Venue.NASDAQ  ,
                                                    fees = 0.1,
                                                    initial_margin = 0,
                                                    quantity_multiplier=1,
                                                    price_multiplier=1,
                                                    data_ticker = "AAPL2",
                                                    company_name = "Apple Inc.",
                                                    industry=Industry.TECHNOLOGY,
                                                    market_cap=10000000000.99,
                                                    shares_outstanding=1937476363)}

    # Basic Validation
    def change_is_valid_contract_true(self, reqId, contract):
        # Side effect for mocking reqContractdetails
        self.contract_manager.app.is_valid_contract = True 
        self.contract_manager.app.validate_contract_event.set()
    
    def change_is_valid_contract_false(self, reqId, contract):
        # Side effect for mocking reqContractdetails
        self.contract_manager.app.is_valid_contract = False
        self.contract_manager.app.validate_contract_event.set()        
    
    def test_validate_contract_valid_contract(self):
        contract = Contract()
        contract.symbol = 'AAPL'

        # Test contract not already validated and is correclty validated
        with patch.object(self.contract_manager.app, 'reqContractDetails', side_effect=self.change_is_valid_contract_true) as mock_method:
            # Test
            response = self.contract_manager.validate_contract(contract)
            
            # Validate
            self.assertEqual(response,True)
            self.mock_logger.info.assert_called_once_with(f"Contract {contract.symbol} validated successfully.") 
            self.assertEqual(self.contract_manager.validated_contracts[contract.symbol], contract)
            self.assertTrue(self.contract_manager.app.validate_contract_event.is_set()) 
    
    def test_validate_contract_invalid_contract(self):
        contract = Contract()
        contract.symbol = 'AAPL'
        
        # Test contract not already validated and is not correclty validated
        with patch.object(self.contract_manager.app, 'reqContractDetails', side_effect=self.change_is_valid_contract_false) as mock_method:
            # Test
            response = self.contract_manager.validate_contract(contract) 
            
            # Validate
            self.assertEqual(response,False)
            self.mock_logger.warning.assert_called_once_with(f"Contract {contract.symbol} validation failed.") 
            self.assertEqual(self.contract_manager.validated_contracts, {}) 
            self.assertTrue(self.contract_manager.app.validate_contract_event.is_set()) 

    def test_validate_contract_already_validate(self):
        contract = Contract()
        contract.symbol = 'AAPL'
        # Add contract to validated contract log
        self.contract_manager.validated_contracts[contract.symbol] = contract 

        # Test
        response = self.contract_manager.validate_contract(contract)
        
        # Validate
        self.assertEqual(response,True) # Should return contract is valid
        self.mock_logger.info.assert_called_once_with(f"Contract {contract.symbol} is already validated.") 

    def test_is_contract_validate_valid(self):
        contract = Contract()
        contract.symbol = 'AAPL'
        
        # Add contract to validated contract log
        self.contract_manager.validated_contracts[contract.symbol] = contract

        # Test 
        response = self.contract_manager._is_contract_validated(contract)
        
        # validate
        self.assertTrue(response) # should be true b/c in the validated contracts

    def test_is_contract_validate_invalid(self):
        contract = Contract()
        contract.symbol = 'AAPL'

        # Test
        response = self.contract_manager._is_contract_validated(contract)
        
        # Validate
        self.assertFalse(response) # Should be false because not in valdiated contracts

    # Type Check
    def test_validate_contract_invalid_contract_type(self):
        contract = 'AAPL'
        with self.assertRaisesRegex(ValueError,"'contract' must be of type Contract instance." ):
            self.contract_manager.validate_contract(contract)

if __name__ == '__main__':

    unittest.main()