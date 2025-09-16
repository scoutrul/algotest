// Lightweight live-candle connector for Binance kline streams
// Usage:
//   import { liveCandle } from './liveCandle.js'
//   liveCandle.connect('BTC/USDT', '1m', onKline)
//   liveCandle.disconnect()

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
  }

  connect(symbol, interval, onKline) {
    this.disconnect();

    const s = toBinanceSymbol(symbol);
    const i = normalizeInterval(interval);
    const url = `${BINANCE_WS}/${s}@kline_${i}`;

    this.current = { symbol: s, interval: i };
    this.onKline = onKline;

    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      console.warn('Live WS creation failed:', e);
      return;
    }

    this.ws.onopen = () => {
      // console.log('🔌 Live WS connected', url);
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
      } catch (_) {}
    };

    this.ws.onclose = () => {
      // try to reconnect after short delay
      this.reconnectTimer = setTimeout(() => {
        this.connect(symbol, interval, onKline);
      }, 2000);
    };

    this.ws.onerror = () => {
      try { this.ws && this.ws.close(); } catch (_) {}
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try { this.ws.onopen = null; this.ws.onmessage = null; this.ws.onclose = null; this.ws.onerror = null; this.ws.close(); } catch (_) {}
      this.ws = null;
    }
    this.onKline = null;
  }
}

export const liveCandle = new LiveCandle();
