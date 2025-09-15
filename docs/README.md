# BackTest Trading Bot

> **MVP BackTest Trading Bot** - Профессиональная система для бэктестинга торговых стратегий на криптовалютных рынках

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docs.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://python.org/)
[![Svelte](https://img.shields.io/badge/Svelte-4.0+-orange.svg)](https://svelte.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red.svg)](https://fastapi.tiangolo.com/)

## 🚀 Быстрый старт

### Вариант 1: Docker (Рекомендуется)

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd algotest

# Запустите в development режиме
./scripts/docker-run.sh

# Или в production режиме
./scripts/docker-run.sh -m prod
```

**Доступные сервисы:**
- **Frontend**: http://localhost:5173 (dev) / http://localhost:80 (prod)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Вариант 2: Локальная разработка

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (в новом терминале)
cd frontend
npm install
npm run dev
```

## 📊 Возможности

### 🎯 Основные функции
- **Гибридная стратегия**: Объединяет анализ объема, цены и управление рисками
- **Интерактивные графики**: TradingView Lightweight Charts с маркерами сделок
- **Адаптивный интерфейс**: Многопанельный макет для всех устройств
- **Реальное время**: Горячая перезагрузка и live обновления
- **API интеграция**: Binance данные через ccxt

### 📈 Торговая стратегия
- **Анализ объема**: Адаптивные пороги и детекция всплесков
- **Анализ цены**: Мультитаймфреймный анализ трендов
- **Управление рисками**: Динамический размер позиций и TP/SL
- **Комбинирование сигналов**: Взвешенная система оценки качества

### 🛠 Технические особенности
- **Микросервисная архитектура**: Backend (Python) + Frontend (Svelte)
- **Контейнеризация**: Docker + Docker Compose
- **API First**: RESTful API с автоматической документацией
- **Тестирование**: Unit + Integration тесты
- **Мониторинг**: Health checks и логирование

## 🏗 Архитектура

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

## 📁 Структура проекта

```
algotest/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   └── main.py         # FastAPI app
│   ├── tests/              # Backend tests
│   ├── Dockerfile          # Backend container
│   └── requirements.txt    # Python dependencies
├── frontend/               # Svelte frontend
│   ├── src/
│   │   ├── components/     # Svelte components
│   │   ├── stores/         # State management
│   │   └── utils/          # Utilities
│   ├── Dockerfile          # Frontend container
│   └── package.json        # Node dependencies
├── docs/                   # Documentation
├── scripts/                # Management scripts
├── docker-compose.yml      # Production setup
├── docker-compose.dev.yml  # Development setup
└── README.md              # This file
```

## 🔧 Конфигурация

### Environment Variables

#### Backend
```bash
LOG_LEVEL=INFO                    # Logging level
DEBUG=false                       # Debug mode
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Frontend
```bash
NODE_ENV=development              # Environment
API_BASE_URL=http://localhost:8000  # Backend URL
```

### Параметры стратегии

| Параметр | Описание | По умолчанию | Диапазон |
|----------|----------|--------------|----------|
| `lookback_period` | Период анализа | 20 | 5-100 |
| `volume_threshold` | Порог объема | 1.5 | 1.0-5.0 |
| `min_price_change` | Минимальное изменение цены | 0.005 | 0.001-0.1 |
| `take_profit` | Тейк-профит | 0.02 | 0.001-0.5 |
| `stop_loss` | Стоп-лосс | 0.01 | 0.001-0.5 |
| `initial_capital` | Начальный капитал | 10000 | 1000+ |

## 📚 API Документация

### Основные endpoints

```bash
# Health check
GET /api/v1/health

# Доступные символы
GET /api/v1/symbols

# Доступные интервалы
GET /api/v1/intervals

# Конфигурация
GET /api/v1/config

# Запуск бэктеста
GET /api/v1/backtest?symbol=BTC/USDT&interval=15m&take_profit=0.02&stop_loss=0.01

# Информация о стратегии
GET /api/v1/strategy/info
```

### Пример запроса

```bash
curl -X GET "http://localhost:8000/api/v1/backtest?symbol=BTC/USDT&interval=15m&take_profit=0.02&stop_loss=0.01" \
  -H "accept: application/json"
```

### Ответ

```json
{
  "candles": [...],
  "trades": [...],
  "statistics": {
    "total_trades": 15,
    "win_rate": 0.67,
    "total_pnl": 1250.50,
    "sharpe_ratio": 1.85
  },
  "parameters": {...},
  "execution_time": 2.34,
  "success": true
}
```

## 🧪 Тестирование

### Backend тесты

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Frontend тесты

```bash
cd frontend
npm test
```

### Integration тесты

```bash
# Запуск всех тестов
docker-compose -f docker-compose.dev.yml up -d
pytest tests/test_integration.py -v
```

## 🐳 Docker

### Development

```bash
# Запуск в development режиме
docker-compose -f docker-compose.dev.yml up -d

# Просмотр логов
docker-compose -f docker-compose.dev.yml logs -f

# Остановка
docker-compose -f docker-compose.dev.yml down
```

### Production

```bash
# Запуск в production режиме
docker-compose up -d

# Масштабирование
docker-compose up -d --scale backend=3

# Мониторинг
docker-compose ps
docker stats
```

## 📊 Мониторинг

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/v1/health

# Frontend health
curl http://localhost:80/health

# Container status
docker-compose ps
```

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f backend

# Последние 100 строк
docker-compose logs --tail=100
```

## 🔒 Безопасность

### Best Practices

- ✅ Non-root пользователи в контейнерах
- ✅ Security headers в Nginx
- ✅ Rate limiting на API endpoints
- ✅ Health checks для мониторинга
- ✅ Resource limits для предотвращения злоупотреблений

### Network Security

```yaml
networks:
  backtest-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 🚀 Деплой

### Локальный деплой

```bash
# Production сборка
./scripts/docker-run.sh -m prod

# Проверка статуса
curl http://localhost:80/health
```

### Cloud деплой

```bash
# AWS ECS
aws ecs create-service --cluster backtest-cluster --service-name backtest-service

# Google Cloud Run
gcloud run deploy backtest-bot --source .

# Azure Container Instances
az container create --resource-group backtest-rg --name backtest-container
```

## 📈 Производительность

### Оптимизация

- **Кэширование**: Redis для API ответов
- **Сжатие**: Gzip для статических ресурсов
- **CDN**: Для статических файлов
- **Load Balancing**: Для масштабирования

### Мониторинг

```bash
# Resource usage
docker stats

# Network usage
docker network ls

# Volume usage
docker system df
```

## 🐛 Troubleshooting

### Частые проблемы

#### 1. Port уже используется

```bash
# Проверить что использует порт
lsof -i :8000

# Остановить процесс
kill -9 <PID>
```

#### 2. Container не запускается

```bash
# Проверить логи
docker-compose logs backend

# Перезапустить
docker-compose restart backend
```

#### 3. API недоступен

```bash
# Проверить health
curl http://localhost:8000/api/v1/health

# Проверить сеть
docker network ls
```

### Debug режим

```bash
# Включить debug логи
export DEBUG=true
docker-compose up

# Подробные логи
docker-compose logs -f --tail=100
```

## 🤝 Вклад в проект

### Development workflow

```bash
# Fork репозитория
git clone <your-fork>
cd algotest

# Создать feature branch
git checkout -b feature/new-feature

# Внести изменения
# ...

# Запустить тесты
pytest tests/ -v

# Commit и push
git commit -m "Add new feature"
git push origin feature/new-feature

# Создать Pull Request
```

### Code Style

- **Python**: Black + isort
- **JavaScript**: Prettier + ESLint
- **Commits**: Conventional Commits
- **Tests**: pytest + coverage

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) файл для деталей.

## 🆘 Поддержка

### Документация

- [Docker Deployment Guide](docs/docker-deployment.md)
- [API Documentation](http://localhost:8000/docs)
- [Architecture Overview](docs/architecture-plan.md)

### Сообщество

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Wiki**: [Project Wiki](https://github.com/your-repo/wiki)

### Контакты

- **Email**: support@backtest-bot.com
- **Discord**: [BackTest Bot Community](https://discord.gg/backtest-bot)
- **Twitter**: [@BackTestBot](https://twitter.com/backtestbot)

---

**BackTest Trading Bot** - Профессиональные инструменты для трейдинга и анализа рынков 🚀