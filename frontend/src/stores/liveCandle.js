// Live-candle connector with backend WebSocket proxy and Binance fallback
// Usage:
//   import { liveCandle } from './liveCandle.js'
//   liveCandle.connect('BTC/USDT', '1m', onKline)
//   liveCandle.disconnect()

const BACKEND_WS = 'ws://localhost:8000/ws';
const BINANCE_WS = 'wss://stream.binance.com:9443/ws';

function toBinanceSymbol(symbol) {
  if (!symbol) return 'btcusdt';
  return symbol.replace('/', '').toLowerCase();
}

function normalizeInterval(interval) {
  // pass-through for supported values
  return interval || '1m';
}

class LiveCandle {
  constructor() {
    this.ws = null;
    this.current = { symbol: null, interval: null };
    this.onKline = null;
    this.reconnectTimer = null;
    this.useBackend = true; // Try backend first, fallback to Binance
    this.connectionAttempts = 0;
    this.maxRetries = 3;
  }

  connect(symbol, interval, onKline) {
    console.log('🔌 Connecting to WebSocket for:', symbol, interval);
    this.disconnect();

    this.current = { symbol, interval };
    this.onKline = onKline;
    this.connectionAttempts = 0;

    // Try backend WebSocket first, then fallback to Binance
    if (this.useBackend) {
      console.log('🔌 Using backend WebSocket');
      this._connectToBackend(symbol, interval);
    } else {
      console.log('🔌 Using Binance WebSocket (fallback)');
      this._connectToBinance(symbol, interval);
    }
  }

  _connectToBackend(symbol, interval) {
    const url = `${BACKEND_WS}/live-candle`;
    
    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      console.warn('Backend WS creation failed, falling back to Binance:', e);
      this._fallbackToBinance(symbol, interval);
      return;
    }

    this.ws.onopen = () => {
      console.log('🔌 Backend WS connected', url);
      this.connectionAttempts = 0;
      
      // Send subscription message after connection is established
      const subscriptionMessage = {
        symbol: symbol,
        interval: interval
      };
      this.ws.send(JSON.stringify(subscriptionMessage));
      console.log('📤 Sent subscription message:', subscriptionMessage);
    };

    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        
        // Handle different message types
        if (data.type === 'kline_update' && data.data) {
          const candle = {
            timestamp: data.data.timestamp,
            open: data.data.open,
            high: data.data.high,
            low: data.data.low,
            close: data.data.close,
            volume: data.data.volume,
            isClosed: data.data.isClosed,
          };
          console.log('📊 Received kline update from backend:', candle);
          this.onKline && this.onKline(candle);
        } else if (data.type === 'connection_established') {
          console.log('✅ Backend WebSocket connection established for', data.symbol, data.interval);
        } else if (data.type === 'health_check') {
          // Send pong response
          this.ws.send('pong');
        } else {
          console.log('📨 Backend message:', data);
        }
      } catch (e) {
        console.warn('Error parsing backend message:', e);
      }
    };

    this.ws.onclose = () => {
      console.warn('Backend WS closed, falling back to Binance');
      this._fallbackToBinance(symbol, interval);
    };

    this.ws.onerror = (error) => {
      console.warn('Backend WS error, falling back to Binance:', error);
      this._fallbackToBinance(symbol, interval);
    };
  }

  _connectToBinance(symbol, interval) {
    const s = toBinanceSymbol(symbol);
    const i = normalizeInterval(interval);
    const url = `${BINANCE_WS}/${s}@kline_${i}`;

    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      console.warn('Binance WS creation failed:', e);
      this._scheduleReconnect(symbol, interval);
      return;
    }

    this.ws.onopen = () => {
      console.log('🔌 Binance WS connected', url);
      this.connectionAttempts = 0;
    };

    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        const k = data.k; // kline payload
        if (!k) return;
        const candle = {
          timestamp: k.t, // open time (ms)
          open: Number(k.o),
          high: Number(k.h),
          low: Number(k.l),
          close: Number(k.c),
          volume: Number(k.v),
          isClosed: !!k.x,
        };
        this.onKline && this.onKline(candle);
      } catch (e) {
        console.warn('Error parsing Binance message:', e);
      }
    };

    this.ws.onclose = () => {
      console.warn('Binance WS closed');
      this._scheduleReconnect(symbol, interval);
    };

    this.ws.onerror = (error) => {
      console.warn('Binance WS error:', error);
      this._scheduleReconnect(symbol, interval);
    };
  }

  _fallbackToBinance(symbol, interval) {
    this.useBackend = false;
    this.connectionAttempts++;
    
    if (this.connectionAttempts <= this.maxRetries) {
      console.log(`🔄 Falling back to Binance (attempt ${this.connectionAttempts}/${this.maxRetries})`);
      this._connectToBinance(symbol, interval);
    } else {
      console.error('Max retries reached, giving up');
    }
  }

  _scheduleReconnect(symbol, interval) {
    if (this.connectionAttempts < this.maxRetries) {
      this.connectionAttempts++;
      console.log(`🔄 Reconnecting in 2s (attempt ${this.connectionAttempts}/${this.maxRetries})`);
      this.reconnectTimer = setTimeout(() => {
        this.connect(symbol, interval, this.onKline);
      }, 2000);
    } else {
      console.error('Max retries reached, giving up');
    }
  }

  disconnect() {
    console.log('🔌 Disconnecting WebSocket...');
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try { 
        console.log('🔌 Closing WebSocket connection...');
        this.ws.onopen = null; 
        this.ws.onmessage = null; 
        this.ws.onclose = null; 
        this.ws.onerror = null; 
        this.ws.close(); 
        console.log('✅ WebSocket connection closed');
      } catch (e) {
        console.warn('Error closing WebSocket:', e);
      }
      this.ws = null;
    }
    this.onKline = null;
    this.connectionAttempts = 0;
    this.useBackend = true; // Reset to try backend first on next connect
    console.log('✅ WebSocket disconnected');
  }
}

export const liveCandle = new LiveCandle();
