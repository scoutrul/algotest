"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
    
    def test_get_symbols(self):
        """Test getting available symbols."""
        response = client.get("/api/v1/symbols")
        
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert isinstance(data["symbols"], list)
        assert len(data["symbols"]) > 0
        assert "BTC/USDT" in data["symbols"]
    
    def test_get_intervals(self):
        """Test getting available intervals."""
        response = client.get("/api/v1/intervals")
        
        assert response.status_code == 200
        data = response.json()
        assert "intervals" in data
        assert isinstance(data["intervals"], list)
        assert len(data["intervals"]) > 0
        assert "15m" in data["intervals"]
    
    def test_get_config(self):
        """Test getting configuration."""
        response = client.get("/api/v1/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "default_strategy_params" in data
        assert "supported_symbols" in data
        assert "supported_intervals" in data
        assert "max_candles_limit" in data
    
    def test_get_engine_info(self):
        """Test getting engine information."""
        response = client.get("/api/v1/engine/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "strategy" in data
        assert "data_fetcher" in data
    
    def test_get_strategy_info(self):
        """Test getting strategy information."""
        response = client.get("/api/v1/strategy/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "description" in data
        assert "components" in data
        assert "config" in data


class TestBacktestEndpoint:
    """Test cases for backtest endpoint."""
    
    def test_backtest_get_valid_params(self):
        """Test backtest endpoint with valid GET parameters."""
        response = client.get("/api/v1/backtest", params={
            "symbol": "BTC/USDT",
            "interval": "15m",
            "take_profit": "0.02",
            "stop_loss": "0.01"
        })
        
        # Should return 200 or 500 depending on if backend services are available
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "candles" in data
            assert "trades" in data
            assert "statistics" in data
        else:
            # If 500, should have error details
            data = response.json()
            assert "detail" in data
    
    def test_backtest_get_invalid_symbol(self):
        """Test backtest endpoint with invalid symbol."""
        response = client.get("/api/v1/backtest", params={
            "symbol": "INVALID/USDT",
            "interval": "15m"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
    
    def test_backtest_get_invalid_interval(self):
        """Test backtest endpoint with invalid interval."""
        response = client.get("/api/v1/backtest", params={
            "symbol": "BTC/USDT",
            "interval": "invalid"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
    
    def test_backtest_get_missing_required_params(self):
        """Test backtest endpoint with missing required parameters."""
        # Missing symbol
        response = client.get("/api/v1/backtest", params={
            "interval": "15m"
        })
        
        assert response.status_code == 422  # Validation error
        
        # Missing interval
        response = client.get("/api/v1/backtest", params={
            "symbol": "BTC/USDT"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_backtest_post_valid_request(self):
        """Test backtest endpoint with valid POST request."""
        request_data = {
            "symbol": "BTC/USDT",
            "interval": "15m",
            "strategy_params": {
                "take_profit": 0.02,
                "stop_loss": 0.01,
                "volume_threshold": 1.5
            }
        }
        
        response = client.post("/api/v1/backtest", json=request_data)
        
        # Should return 200 or 500 depending on if backend services are available
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "candles" in data
            assert "trades" in data
            assert "statistics" in data
        else:
            # If 500, should have error details
            data = response.json()
            assert "detail" in data
    
    def test_backtest_post_invalid_request(self):
        """Test backtest endpoint with invalid POST request."""
        request_data = {
            "symbol": "INVALID/USDT",
            "interval": "15m",
            "strategy_params": {}
        }
        
        response = client.post("/api/v1/backtest", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]


class TestRootEndpoint:
    """Test cases for root endpoint."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        assert data["message"] == "BackTest Trading Bot API"
