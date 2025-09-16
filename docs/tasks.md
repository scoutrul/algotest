# Tasks - Source of Truth

## Current Task
**PLAN Mode**: Планирование MVP BackTest Trading Bot

### Complexity Level: 3 (Intermediate)
- Двухсервисная архитектура
- Интеграция с внешним API
- Интерактивная визуализация данных
- Алгоритмическая логика стратегии

### Active Tasks
- [ ] Оптимизация производительности
- [ ] Тестирование Docker деплоя
- [ ] Production deployment

### Creative Phases Completed
- [x] Strategy Design: Hybrid Adaptive Strategy
- [x] UI/UX Design: Adaptive Multi-Panel Layout

### Completed Tasks
- [x] Создан projectbrief.md
- [x] Создан tasks.md
- [x] Инициализирован git репозиторий
- [x] Создана базовая структура монорепозитория
- [x] Настроен .gitignore
- [x] Создан README.md
- [x] Инициализированы Memory Bank файлы
- [x] Сделан первый коммит
- [x] Определены требования MVP
- [x] Создан детальный план архитектуры
- [x] Спроектирована торговая стратегия
- [x] Создана структура папок backend/frontend
- [x] Настроены зависимости (requirements.txt, package.json)
- [x] Создана спецификация API
- [x] **Phase 1 Backend Complete**: Hybrid Strategy Engine реализован
  - DataFetcher: Binance интеграция с кэшированием
  - VolumeAnalyzer: Адаптивный анализ объемов
  - PriceAnalyzer: Многофакторный анализ цен
  - RiskManager: Динамическое управление рисками
  - SignalCombiner: Комбинирование сигналов
  - BacktestEngine: Полный движок бэктестинга
  - FastAPI: RESTful API с документацией
- [x] **Phase 2 Frontend Complete**: Adaptive UI Components реализованы
  - App.svelte: Адаптивный многопанельный макет
  - Chart.svelte: TradingView Lightweight Charts интеграция
  - StrategyForm.svelte: Интуитивная форма параметров
  - Statistics.svelte: Детальная статистика результатов
  - Controls.svelte: Управление символами и интервалами
  - Svelte Stores: Управление состоянием приложения
  - API Client: Интеграция с backend
- [x] **Phase 3 Integration Complete**: Система интегрирована и протестирована
  - Backend API: Все endpoints работают корректно
  - Frontend Integration: Успешная интеграция с backend
  - Integration Tests: 12/12 тестов прошли успешно
  - System Health: Backend + Frontend работают стабильно
  - API Validation: Валидация параметров и обработка ошибок
- [x] **Phase 4 Docker Complete**: Контейнеризация и деплой
  - Docker Images: Backend (Python) + Frontend (Nginx)
  - Docker Compose: Development + Production конфигурации
  - Orchestration: Redis + Nginx reverse proxy
  - Management Scripts: Build, run, monitor automation
  - Documentation: Comprehensive Docker deployment guide
- [x] **Phase 5 Documentation Complete**: Полная документация и руководства
  - README.md: Comprehensive project overview and quick start
  - User Guide: Complete user manual with best practices
  - Developer Guide: Technical documentation for contributors
  - API Documentation: Auto-generated FastAPI docs
  - Troubleshooting: Common issues and solutions
- [x] **Phase 6.1 Performance Analysis Complete**: Анализ производительности и baseline
  - Performance Benchmark Suite: Comprehensive benchmarking tools
  - Performance Middleware: Real-time monitoring and profiling
  - System Metrics: CPU, memory, disk usage tracking
  - API Performance: Response time and throughput monitoring
  - Baseline Results: Data fetching (7.24s), API backtest (0.49s)
  - Performance Issues Identified: Slow data fetching, high memory usage

### Next Steps
1. **Phase 6.2**: Backend Optimization (Caching, Connection Pooling)
2. **Phase 6.3**: Frontend Optimization (Bundle Size, Lazy Loading)
3. **Phase 6.4**: Infrastructure Optimization (Docker, Resource Limits)
4. **Phase 7**: Production deployment
5. **Phase 8**: Мониторинг и аналитика

## PLAN: Fix Historical Backfill on Chart (Level 3)

- **Status**: Planning complete → proceed to Implement Mode
- **Owner**: Frontend + Backend
- **Goal**: Восстановить автодогрузку исторических свечей при прокрутке графика влево без ломания вьюпорта и без дубликатов.

### Requirements Analysis
- **Функциональные**:
  - При достижении левого края видимой области должны автоматически уходить запросы на старшие свечи с `end_time` = timestamp самой старой загруженной свечи.
  - Новые свечи добавляются слева, вьюпорт остаётся «на месте» (логический диапазон сдвигается вправо на размер добавленного батча).
  - Не более N конкурентных запросов (N=2), кулдаун между триггерами ≥ 750ms.
  - Отсутствие дубликатов и «залипаний» курсора; корректная работа при смене символа/интервала.
- **Нефункциональные**:
  - Плавность скролла, отсутствие фризов.
  - Предсказуемые условия триггера, понятные логи для диагностики.

### Components Affected
- Frontend:
  - `frontend/src/components/Chart.svelte` — триггер backfill, курсор, плейсхолдеры, обновление вьюпорта.
  - `frontend/src/utils/api.js` — `getCandles` параметры и конечная точка.
- Backend:
  - `backend/app/api/market.py` vs `backend/app/api/basic.py` — конфликтующие `/api/v1/candles`.
  - `backend/app/main.py` — порядок подключения роутеров.

### Architecture Considerations
- Единый надёжный источник для backfill — реализация из `market.py` (чтение от биржи чанками назад по `end_time`).
- БД-роут стоит развести по другому пути (например, `/api/v1/db/candles`) либо задать приоритет `market.py`.
- На фронте триггер должен опираться на логические индексы и фиксированный порог «близости к левому краю», без избыточных эвристик.

### Implementation Strategy
- Упростить условия триггера в `Chart.svelte`:
  - Триггерить, когда `range.from <= oldestBarIdx + thresholdBars` (thresholdBars ≈ 50).
  - Убрать зависимость от `movedLeft/significantMovement`.
  - Оставить кулдаун и лимит конкуренции.
- Инициализировать левый буфер плейсхолдеров сразу после первой загрузки свечей (`ensureLeftBuffer`), чтобы корректно вычислять левый край.
- Починить курсорную логику:
  - Если пришли только дубликаты/пусто — сдвигать `backfillCursor` на `-intervalSec` и повторять ограниченно.
  - `lastRequestedCursor` обновлять на отправку; сбрасывать при изменении `backfillCursor` назад во времени.
- Разрулить backend-эндпоинты:
  - Зафиксировать использование `market.py` для `/api/v1/candles` (или изменить путь БД-эндпоинта).

### Detailed Steps
1) Frontend — диагностика и триггер
   - Добавить подробные логи в `subscribeVisibleLogicalRangeChange` и `performAutomaticBackfill` (range, windowWidth, oldestBarIdx, shouldTriggerBackfill, cursor).
   - Упростить условие триггера: `if (range.from <= oldestBarIdx + 50 && cooldown && !isLoadingMore && activeBackfillCount < 2) { performAutomaticBackfill(1) }`.
   - Вызывать `ensureLeftBuffer(500)` сразу после первичной установки `candles` и перед первым backfill.
2) Frontend — курсор и вьюпорт
   - В `performAutomaticBackfill` корректно обновлять `backfillCursor` после prepend и при пустом ответе сдвигать на `-intervalSec`.
   - После prepend сдвигать `visibleLogicalRange` вправо на `onlyNew.length`.
   - Сбросы при смене символа/интервала: обнулить `activeBackfillCount`, `reachedHistoryStart`, `lastRequestedCursor`, `backfillCursor`, `leftPlaceholders`, `lastLogicalRange`.
3) Backend — эндпоинты
   - Проверить порядок `include_router` в `main.py`, чтобы `/api/v1/candles` обслуживался реализацией из `market.py`.
   - Альтернатива: переименовать БД-эндпоинт в `/api/v1/db/candles` и обновить вызовы, если используются.
4) Тесты
   - Ручные сценарии: BTC/USDT × {1m,15m,1h}. Прокрутка влево 3–5 итераций, контроль Network и визуального заполнения слева, отсутствие «прыжков» вьюпорта.
   - Проверка на зум-ин/аут и смену символа/интервала.

### Dependencies
- Либрари: `lightweight-charts` (поддержка logical range API).
- Backend доступность `/api/v1/candles` с параметром `end_time`.

### Challenges & Mitigations
- **Конфликт роутов**: зафиксировать приоритет или развести пути.
- **Дубликаты/пробелы**: дедуп по `time`, корректный `backfillCursor` и фильтрация `onlyNew`.
- **Производительность**: кулдаун 750ms, `MAX_CONCURRENT_BACKFILLS=2`, размер батча до 1000.

### Creative Phase Components
- Не требуется отдельная архитектурная/алгоритмическая «креативная» фаза. Решение интеграционное.

### Testing Strategy
- Визуальные и сетевые проверки в браузере.
- Серверные логи подтверждают обработчик `market.py`.
- Регресс: начальный рендер, лайв-свечи, масштабирование, смена символа/интервала.

### Mode Transition
- Рекомендация: ⏭️ NEXT MODE: IMPLEMENT MODE
