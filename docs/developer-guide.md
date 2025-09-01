# Руководство разработчика - BackTest Trading Bot

## 🏗 Архитектура системы

### Обзор

BackTest Trading Bot построен на микросервисной архитектуре с четким разделением ответственности:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │     Redis       │
│   (Svelte)      │◄──►│   (FastAPI)     │◄──►│   (Cache)       │
│   Port 5173/80  │    │   Port 8000     │    │   Port 6379     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Nginx Proxy    │
                    │   (Optional)     │
                    │   Port 8080      │
                    └─────────────────┘
```

### Компоненты

#### Backend (Python/FastAPI)
- **API Layer**: RESTful endpoints
- **Business Logic**: Торговые стратегии и анализ
- **Data Layer**: Интеграция с Binance API
- **Models**: Pydantic модели данных

#### Frontend (Svelte)
- **Components**: Переиспользуемые UI компоненты
- **Stores**: Управление состоянием
- **Utils**: Вспомогательные функции
- **Charts**: TradingView Lightweight Charts

## 🚀 Настройка среды разработки

### Требования

- **Python**: 3.9+
- **Node.js**: 18+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd algotest

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Запуск в development режиме
cd ..
./scripts/docker-run.sh
```

### IDE настройка

#### VS Code

```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/node_modules": true,
    "**/.pytest_cache": true
  }
}
```

#### Рекомендуемые расширения

- **Python**: Python, Pylance
- **Svelte**: Svelte for VS Code
- **Docker**: Docker
- **Git**: GitLens

## 🏛 Backend разработка

### Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Конфигурация
│   ├── api/                 # API endpoints
│   │   ├── __init__.py
│   │   └── backtest.py      # Backtest endpoints
│   ├── models/              # Pydantic модели
│   │   ├── __init__.py
│   │   ├── strategy.py      # Модели стратегии
│   │   └── backtest.py      # Модели бэктеста
│   └── services/            # Бизнес-логика
│       ├── __init__.py
│       ├── data_fetcher.py  # Получение данных
│       ├── backtest.py      # Движок бэктеста
│       └── strategy/        # Торговые стратегии
│           ├── __init__.py
│           ├── hybrid_strategy.py
│           ├── volume_analyzer.py
│           ├── price_analyzer.py
│           ├── risk_manager.py
│           └── signal_combiner.py
├── tests/                   # Тесты
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_data_fetcher.py
│   └── test_integration.py
├── Dockerfile
├── requirements.txt
└── README.md
```

### API Development

#### Создание нового endpoint

```python
# app/api/backtest.py
from fastapi import APIRouter, HTTPException
from app.models.strategy import StrategyParams
from app.services.backtest import BacktestEngine

router = APIRouter()

@router.get("/new-endpoint")
async def new_endpoint():
    """Новый endpoint для функциональности."""
    try:
        # Бизнес-логика
        result = await some_service.process()
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Добавление в main.py

```python
# app/main.py
from app.api.backtest import router as backtest_router

app.include_router(backtest_router, prefix="/api/v1", tags=["backtest"])
```

### Модели данных

#### Создание новой модели

```python
# app/models/new_model.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class NewModel(BaseModel):
    """Новая модель данных."""
    
    id: int = Field(..., description="Уникальный идентификатор")
    name: str = Field(..., min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Сервисы

#### Создание нового сервиса

```python
# app/services/new_service.py
import logging
from typing import List, Dict, Any
from app.models.new_model import NewModel

logger = logging.getLogger(__name__)

class NewService:
    """Новый сервис для бизнес-логики."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        logger.info("NewService initialized")
    
    async def process_data(self, data: List[Dict[str, Any]]) -> List[NewModel]:
        """Обработка данных."""
        try:
            results = []
            for item in data:
                # Обработка каждого элемента
                result = NewModel(**item)
                results.append(result)
            
            logger.info(f"Processed {len(results)} items")
            return results
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            raise
```

### Тестирование

#### Unit тесты

```python
# tests/test_new_service.py
import pytest
from app.services.new_service import NewService

class TestNewService:
    """Тесты для NewService."""
    
    def setup_method(self):
        """Настройка для каждого теста."""
        self.service = NewService({"test": True})
    
    def test_process_data_success(self):
        """Тест успешной обработки данных."""
        data = [{"id": 1, "name": "test"}]
        results = self.service.process_data(data)
        
        assert len(results) == 1
        assert results[0].name == "test"
    
    def test_process_data_empty(self):
        """Тест обработки пустых данных."""
        results = self.service.process_data([])
        assert len(results) == 0
```

#### Integration тесты

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_new_endpoint():
    """Тест нового endpoint."""
    response = client.get("/api/v1/new-endpoint")
    
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
```

## 🎨 Frontend разработка

### Структура проекта

```
frontend/
├── src/
│   ├── main.js              # Точка входа
│   ├── App.svelte           # Главный компонент
│   ├── components/          # Компоненты
│   │   ├── Chart.svelte     # График
│   │   ├── Controls.svelte  # Управление
│   │   ├── StrategyForm.svelte # Форма стратегии
│   │   └── Statistics.svelte # Статистика
│   ├── stores/              # Управление состоянием
│   │   ├── backtest.js      # Состояние бэктеста
│   │   └── config.js        # Конфигурация
│   └── utils/               # Утилиты
│       ├── api.js           # API клиент
│       └── chart.js         # Функции графика
├── public/
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

### Создание компонента

#### Базовый компонент

```svelte
<!-- src/components/NewComponent.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  
  // Props
  export let title = 'Default Title';
  export let data = [];
  export let loading = false;
  
  // Event dispatcher
  const dispatch = createEventDispatcher();
  
  // Reactive statements
  $: hasData = data && data.length > 0;
  
  // Methods
  function handleClick() {
    dispatch('click', { data });
  }
</script>

<div class="new-component">
  <h3>{title}</h3>
  
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if hasData}
    <div class="content">
      {#each data as item}
        <div class="item">{item}</div>
      {/each}
    </div>
  {:else}
    <div class="empty">No data available</div>
  {/if}
  
  <button on:click={handleClick}>Action</button>
</div>

<style>
  .new-component {
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
  
  .loading {
    text-align: center;
    color: #666;
  }
  
  .empty {
    text-align: center;
    color: #999;
  }
  
  .item {
    padding: 0.5rem;
    margin: 0.25rem 0;
    background: #f5f5f5;
    border-radius: 2px;
  }
  
  button {
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
  
  button:hover {
    background: #0056b3;
  }
</style>
```

### Управление состоянием

#### Создание store

```javascript
// src/stores/newStore.js
import { writable } from 'svelte/store';

// Initial state
const initialState = {
  items: [],
  loading: false,
  error: null
};

// Create writable store
function createNewStore() {
  const { subscribe, set, update } = writable(initialState);

  return {
    subscribe,
    
    // Actions
    setLoading: (loading) => update(state => ({ ...state, loading })),
    
    setError: (error) => update(state => ({ ...state, error, loading: false })),
    
    addItem: (item) => update(state => ({
      ...state,
      items: [...state.items, item]
    })),
    
    removeItem: (id) => update(state => ({
      ...state,
      items: state.items.filter(item => item.id !== id)
    })),
    
    clearItems: () => update(state => ({
      ...state,
      items: []
    }))
  };
}

// Export store instance
export const newStore = createNewStore();
```

### API интеграция

#### Расширение API клиента

```javascript
// src/utils/api.js
class ApiClient {
  // ... existing methods ...
  
  // New API method
  async getNewData(params) {
    const queryParams = new URLSearchParams();
    
    if (params.id) {
      queryParams.append('id', params.id);
    }
    
    return this.request(`/new-data?${queryParams.toString()}`);
  }
  
  async createNewItem(data) {
    return this.request('/new-items', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
}
```

## 🧪 Тестирование

### Backend тесты

#### Запуск тестов

```bash
cd backend
source .venv/bin/activate

# Все тесты
pytest

# Конкретный файл
pytest tests/test_new_service.py

# С покрытием
pytest --cov=app tests/

# Verbose output
pytest -v
```

#### Тестовые данные

```python
# tests/fixtures.py
import pytest
from app.models.strategy import StrategyParams

@pytest.fixture
def sample_strategy_params():
    """Фикстура с параметрами стратегии."""
    return StrategyParams(
        symbol="BTC/USDT",
        interval="15m",
        lookback_period=20,
        volume_threshold=1.5,
        take_profit=0.02,
        stop_loss=0.01,
        initial_capital=10000
    )

@pytest.fixture
def sample_candles():
    """Фикстура с тестовыми свечами."""
    return [
        {
            "timestamp": "2023-01-01T00:00:00Z",
            "open": 50000,
            "high": 51000,
            "low": 49000,
            "close": 50500,
            "volume": 1000
        },
        # ... more candles
    ]
```

### Frontend тесты

#### Настройка тестирования

```bash
cd frontend
npm install --save-dev @testing-library/svelte vitest jsdom
```

#### Тест компонента

```javascript
// src/components/__tests__/NewComponent.test.js
import { render, screen, fireEvent } from '@testing-library/svelte';
import NewComponent from '../NewComponent.svelte';

describe('NewComponent', () => {
  test('renders with default title', () => {
    render(NewComponent);
    expect(screen.getByText('Default Title')).toBeInTheDocument();
  });
  
  test('renders with custom title', () => {
    render(NewComponent, { title: 'Custom Title' });
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });
  
  test('dispatches click event', () => {
    const { component } = render(NewComponent, { data: ['test'] });
    const handleClick = vi.fn();
    component.$on('click', handleClick);
    
    fireEvent.click(screen.getByText('Action'));
    expect(handleClick).toHaveBeenCalled();
  });
});
```

## 🐳 Docker разработка

### Development контейнер

```dockerfile
# Dockerfile.dev
FROM python:3.9-slim

WORKDIR /app

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    isort \
    flake8

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Development command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Docker Compose для разработки

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  backend-dev:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app
      - /app/__pycache__
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend-dev:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    environment:
      - NODE_ENV=development
    command: npm run dev -- --host 0.0.0.0
```

## 🔧 Инструменты разработки

### Code Quality

#### Python

```bash
# Black (форматирование)
black app/ tests/

# isort (сортировка импортов)
isort app/ tests/

# flake8 (линтер)
flake8 app/ tests/

# mypy (типизация)
mypy app/
```

#### JavaScript/Svelte

```bash
# Prettier (форматирование)
npx prettier --write src/

# ESLint (линтер)
npx eslint src/

# TypeScript (если используется)
npx tsc --noEmit
```

### Git Hooks

#### Pre-commit

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Backend checks
cd backend
source .venv/bin/activate
black --check app/ tests/
isort --check-only app/ tests/
flake8 app/ tests/
pytest tests/ -q

# Frontend checks
cd ../frontend
npm run lint
npm run format:check

echo "All checks passed!"
```

### CI/CD

#### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest tests/ --cov=app

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: 18
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm test
```

## 📚 Документация

### API документация

FastAPI автоматически генерирует документацию:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Документирование кода

#### Python docstrings

```python
def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio for given returns.
    
    Args:
        returns: List of portfolio returns
        risk_free_rate: Risk-free rate (default: 2%)
        
    Returns:
        Sharpe ratio value
        
    Raises:
        ValueError: If returns list is empty
        
    Example:
        >>> returns = [0.01, 0.02, -0.01, 0.03]
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe ratio: {sharpe:.2f}")
    """
    if not returns:
        raise ValueError("Returns list cannot be empty")
    
    # Implementation...
    return sharpe_ratio
```

#### JSDoc для JavaScript

```javascript
/**
 * Calculate moving average for given data.
 * @param {number[]} data - Array of numeric values
 * @param {number} period - Moving average period
 * @returns {number[]} Array of moving average values
 * @throws {Error} If data is empty or period is invalid
 * @example
 * const data = [1, 2, 3, 4, 5];
 * const ma = calculateMovingAverage(data, 3);
 * console.log(ma); // [2, 3, 4]
 */
function calculateMovingAverage(data, period) {
  if (!data || data.length === 0) {
    throw new Error('Data cannot be empty');
  }
  
  if (period <= 0 || period > data.length) {
    throw new Error('Invalid period');
  }
  
  // Implementation...
  return movingAverages;
}
```

## 🚀 Деплой

### Production сборка

```bash
# Backend
cd backend
docker build -t backtest-backend:latest .

# Frontend
cd frontend
docker build -t backtest-frontend:latest .

# Запуск
docker-compose up -d
```

### Environment переменные

```bash
# .env.production
LOG_LEVEL=INFO
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
REDIS_URL=redis://redis:6379
```

### Мониторинг

```bash
# Health checks
curl http://localhost:8000/api/v1/health
curl http://localhost:80/health

# Logs
docker-compose logs -f

# Metrics
docker stats
```

---

**Удачной разработки!** 🚀

Для вопросов и предложений обращайтесь в наше сообщество разработчиков.
