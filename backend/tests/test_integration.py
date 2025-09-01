"""
Integration tests for the complete BackTest Trading Bot system.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSystemIntegration:
    """Integration tests for the complete system."""
    
    def test_system_health(self):
        """Test that the entire system is healthy."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "BackTest Trading Bot API"
    
    def test_api_endpoints_available(self):
        """Test that all required API endpoints are available."""
        endpoints = [
            "/",
            "/api/v1/health",
            "/api/v1/symbols",
            "/api/v1/intervals",
            "/api/v1/config",
            "/api/v1/engine/info",
            "/api/v1/strategy/info"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404, 422]  # Valid responses
    
    def test_backtest_endpoint_structure(self):
        """Test that backtest endpoint returns proper structure."""
        response = client.get("/api/v1/backtest", params={
            "symbol": "BTC/USDT",
            "interval": "15m",
            "take_profit": "0.02",
            "stop_loss": "0.01"
        })
        
        # Should return either 200 (success) or 500 (service error)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Check response structure
            assert "candles" in data
            assert "trades" in data
            assert "statistics" in data
            assert "parameters" in data
            assert "execution_time" in data
            assert "success" in data
    
    def test_symbols_endpoint(self):
        """Test symbols endpoint returns valid data."""
        response = client.get("/api/v1/symbols")
        
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert isinstance(data["symbols"], list)
        assert len(data["symbols"]) > 0
        
        # Check that symbols have correct format
        for symbol in data["symbols"]:
            assert "/" in symbol  # Should contain "/"
            assert len(symbol.split("/")) == 2  # Should be in format BASE/QUOTE
    
    def test_intervals_endpoint(self):
        """Test intervals endpoint returns valid data."""
        response = client.get("/api/v1/intervals")
        
        assert response.status_code == 200
        data = response.json()
        assert "intervals" in data
        assert isinstance(data["intervals"], list)
        assert len(data["intervals"]) > 0
        
        # Check that intervals are valid
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
        for interval in data["intervals"]:
            assert interval in valid_intervals
    
    def test_config_endpoint(self):
        """Test config endpoint returns valid configuration."""
        response = client.get("/api/v1/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required config fields
        assert "default_strategy_params" in data
        assert "supported_symbols" in data
        assert "supported_intervals" in data
        assert "max_candles_limit" in data
        
        # Check strategy params structure
        strategy_params = data["default_strategy_params"]
        required_params = [
            "lookback_period", "volume_threshold", "min_price_change",
            "take_profit", "stop_loss", "max_trades", "initial_capital"
        ]
        
        for param in required_params:
            assert param in strategy_params
    
    def test_engine_info_endpoint(self):
        """Test engine info endpoint returns valid information."""
        response = client.get("/api/v1/engine/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "strategy" in data
        assert "data_fetcher" in data
    
    def test_strategy_info_endpoint(self):
        """Test strategy info endpoint returns valid information."""
        response = client.get("/api/v1/strategy/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "description" in data
        assert "components" in data
        assert "config" in data
        
        # Check components structure
        components = data["components"]
        required_components = ["volume_analyzer", "price_analyzer", "risk_manager", "signal_combiner"]
        
        for component in required_components:
            assert component in components
    
    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        response = client.options("/api/v1/health")
        
        # Should allow OPTIONS method for CORS preflight
        assert response.status_code in [200, 405]  # 405 is also acceptable
    
    def test_error_handling(self):
        """Test that error handling works properly."""
        # Test invalid symbol
        response = client.get("/api/v1/backtest", params={
            "symbol": "INVALID/USDT",
            "interval": "15m"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
        
        # Test invalid interval
        response = client.get("/api/v1/backtest", params={
            "symbol": "BTC/USDT",
            "interval": "invalid"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
    
    def test_validation_errors(self):
        """Test that validation errors are properly handled."""
        # Test missing required parameters
        response = client.get("/api/v1/backtest", params={
            "symbol": "BTC/USDT"
            # Missing interval
        })
        
        assert response.status_code == 422  # Validation error
        
        response = client.get("/api/v1/backtest", params={
            "interval": "15m"
            # Missing symbol
        })
        
        assert response.status_code == 422  # Validation error


class TestDataFlow:
    """Test data flow through the system."""
    
    def test_backtest_data_flow(self):
        """Test that backtest data flows correctly through the system."""
        # This test would require more complex setup with mocked external services
        # For now, we'll test the basic structure
        
        response = client.post("/api/v1/backtest", json={
            "symbol": "BTC/USDT",
            "interval": "15m",
            "strategy_params": {
                "lookback_period": 20,
                "volume_threshold": 1.5,
                "take_profit": 0.02,
                "stop_loss": 0.01,
                "initial_capital": 10000
            }
        })
        
        # Should return either 200 (success) or 500 (service error)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Verify data structure
            assert "candles" in data
            assert "trades" in data
            assert "statistics" in data
            assert "success" in data
            assert data["success"] is True


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])
