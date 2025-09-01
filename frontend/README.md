# BackTest Trading Bot - Frontend

Frontend application for the MVP BackTest Trading Bot, built with Svelte and TradingView Lightweight Charts.

## Features

- **Adaptive Multi-Panel Layout**: Responsive design that works on all devices
- **TradingView Lightweight Charts**: Professional-grade charting with trade markers
- **Strategy Configuration**: Intuitive form for setting strategy parameters
- **Real-time Statistics**: Comprehensive backtest results and performance metrics
- **Interactive Controls**: Easy symbol and interval selection

## Architecture

### Components

1. **App.svelte**: Main application layout with adaptive panels
2. **Chart.svelte**: TradingView Lightweight Charts integration
3. **StrategyForm.svelte**: Strategy parameters configuration
4. **Statistics.svelte**: Backtest results and performance metrics
5. **Controls.svelte**: Symbol and interval selection

### State Management

- **backtestStore**: Manages backtest data and execution
- **configStore**: Handles configuration and validation

### Utilities

- **api.js**: Backend API communication
- **chart.js**: Chart utility functions and formatting

## Installation

### Prerequisites

- Node.js 16+
- npm or yarn

### Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000

## Usage

### Running a Backtest

1. **Select Symbol and Interval**: Use the controls in the header
2. **Configure Strategy**: Adjust parameters in the Strategy panel
3. **Run Backtest**: Click "Run Backtest" button
4. **View Results**: Check the chart and statistics panels

### Strategy Parameters

#### Volume Analysis
- **Lookback Period**: Number of candles for volume average (5-100)
- **Volume Threshold**: Volume spike multiplier (1.0-5.0)
- **Min Price Change**: Minimum price change for signals (0.001-0.1)

#### Risk Management
- **Take Profit**: Take profit percentage (0.001-0.5)
- **Stop Loss**: Stop loss percentage (0.001-0.5)
- **Initial Capital**: Starting capital for backtesting (100-1,000,000)

#### Backtest Settings
- **Max Trades**: Maximum trades per backtest (1-1000)

## Development

### Project Structure

```
frontend/
├── src/
│   ├── App.svelte           # Main app component
│   ├── main.js              # Entry point
│   ├── components/          # UI components
│   │   ├── Chart.svelte     # Trading chart
│   │   ├── StrategyForm.svelte # Parameters form
│   │   ├── Statistics.svelte # Results display
│   │   └── Controls.svelte  # Symbol/interval controls
│   ├── stores/              # State management
│   │   ├── backtest.js      # Backtest state
│   │   └── config.js        # Configuration state
│   └── utils/               # Utility functions
│       ├── api.js           # API client
│       └── chart.js         # Chart utilities
├── index.html
├── vite.config.js
├── package.json
└── README.md
```

### Available Scripts

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run check

# Type checking with watch
npm run check:watch
```

### Key Dependencies

- **Svelte**: Reactive UI framework
- **Vite**: Fast build tool and dev server
- **lightweight-charts**: TradingView charting library
- **Fetch API**: HTTP client for backend communication

## Responsive Design

### Breakpoints

- **Mobile**: < 768px - Vertical stack layout
- **Tablet**: 768px - 1024px - 2-column layout
- **Desktop**: > 1024px - 3-panel layout

### Layout Modes

1. **Normal Mode**: Chart, Strategy, and Statistics panels
2. **Fullscreen Mode**: Chart takes full viewport
3. **Collapsed Panels**: Minimized panels for more chart space

## Chart Features

### TradingView Integration

- **Candlestick Charts**: OHLCV data visualization
- **Trade Markers**: Entry/exit points with colors
- **Zoom and Pan**: Interactive chart navigation
- **Export**: Chart image export functionality

### Trade Visualization

- **Entry Markers**: Green arrows for long, red for short
- **Exit Markers**: Circles for take profit, squares for stop loss
- **PnL Display**: Color-coded profit/loss indicators
- **Legend**: Visual guide for chart elements

## Performance

### Optimization

- **Lazy Loading**: Components load on demand
- **Chart Virtualization**: Efficient rendering of large datasets
- **State Management**: Minimal re-renders with Svelte stores
- **API Caching**: Reduced backend requests

### Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+
- **Mobile**: iOS Safari 14+, Chrome Mobile 90+
- **Features**: ES2020, CSS Grid, Flexbox

## Error Handling

### User Experience

- **Loading States**: Visual feedback during operations
- **Error Messages**: Clear error communication
- **Validation**: Real-time form validation
- **Fallbacks**: Graceful degradation for missing data

### Network Handling

- **Connection Errors**: Backend connectivity issues
- **API Errors**: Structured error responses
- **Timeout Handling**: Request timeout management
- **Retry Logic**: Automatic retry for failed requests

## Future Enhancements

### Planned Features

- **Dark Theme**: Alternative color scheme
- **Chart Themes**: Multiple chart appearance options
- **Export Data**: CSV/JSON export functionality
- **Advanced Filters**: Trade filtering and sorting
- **Performance Metrics**: Additional statistics
- **Real-time Updates**: Live data integration

### Technical Improvements

- **PWA Support**: Progressive Web App features
- **Offline Mode**: Basic offline functionality
- **Performance Monitoring**: User experience metrics
- **Accessibility**: WCAG compliance improvements
