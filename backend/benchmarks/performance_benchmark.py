"""
Performance Benchmark Suite for BackTest Trading Bot

This module provides comprehensive performance testing and benchmarking
capabilities for the trading bot system.
"""

import asyncio
import time
import psutil
import memory_profiler
from typing import Dict, List, Any, Tuple
import statistics
import json
from datetime import datetime
import logging

from app.services.data_fetcher import DataFetcher
from app.services.strategy.hybrid_strategy import HybridStrategy
from app.models.strategy import StrategyParams
from app.models.backtest import BacktestRequest
from app.services.backtest import BacktestEngine

logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.start_memory = None
        
    def start_benchmark(self, test_name: str):
        """Start benchmarking a specific test."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        logger.info(f"Starting benchmark: {test_name}")
        
    def end_benchmark(self, test_name: str) -> Dict[str, Any]:
        """End benchmarking and return results."""
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        duration = end_time - self.start_time
        memory_delta = end_memory - self.start_memory
        
        result = {
            'test_name': test_name,
            'duration_seconds': round(duration, 4),
            'memory_start_mb': round(self.start_memory, 2),
            'memory_end_mb': round(end_memory, 2),
            'memory_delta_mb': round(memory_delta, 2),
            'timestamp': datetime.now().isoformat()
        }
        
        self.results[test_name] = result
        logger.info(f"Benchmark completed: {test_name} - {duration:.4f}s, {memory_delta:+.2f}MB")
        
        return result
    
    async def benchmark_data_fetching(self, symbol: str = "BTC/USDT", interval: str = "15m", limit: int = 1000) -> Dict[str, Any]:
        """Benchmark data fetching performance."""
        self.start_benchmark("data_fetching")
        
        try:
            fetcher = DataFetcher()
            data = await fetcher.fetch_candles(symbol, interval, limit)
            
            result = self.end_benchmark("data_fetching")
            result.update({
                'symbol': symbol,
                'interval': interval,
                'limit': limit,
                'data_points': len(data),
                'success': True
            })
            
        except Exception as e:
            result = self.end_benchmark("data_fetching")
            result.update({
                'error': str(e),
                'success': False
            })
            
        return result
    
    async def benchmark_strategy_calculation(self, data: List[Dict], params: StrategyParams) -> Dict[str, Any]:
        """Benchmark strategy calculation performance."""
        self.start_benchmark("strategy_calculation")
        
        try:
            strategy = HybridStrategy(params)
            signals = strategy.calculate_signals(data)
            
            result = self.end_benchmark("strategy_calculation")
            result.update({
                'data_points': len(data),
                'signals_generated': len(signals),
                'success': True
            })
            
        except Exception as e:
            result = self.end_benchmark("strategy_calculation")
            result.update({
                'error': str(e),
                'success': False
            })
            
        return result
    
    async def benchmark_backtest_execution(self, params: StrategyParams) -> Dict[str, Any]:
        """Benchmark complete backtest execution."""
        self.start_benchmark("backtest_execution")
        
        try:
            # Convert StrategyParams to BacktestRequest
            request = BacktestRequest(
                symbol=params.symbol,
                interval=params.interval,
                strategy_params=params
            )
            
            engine = BacktestEngine()
            result = await engine.run_backtest(request)
            
            benchmark_result = self.end_benchmark("backtest_execution")
            benchmark_result.update({
                'trades_count': len(result.trades) if result.trades else 0,
                'candles_count': len(result.candles) if result.candles else 0,
                'success': True
            })
            
        except Exception as e:
            benchmark_result = self.end_benchmark("backtest_execution")
            benchmark_result.update({
                'error': str(e),
                'success': False
            })
            
        return benchmark_result
    
    async def benchmark_api_endpoint(self, endpoint: str, params: Dict[str, Any], iterations: int = 10) -> Dict[str, Any]:
        """Benchmark API endpoint performance with multiple iterations."""
        import httpx
        
        durations = []
        successes = 0
        
        self.start_benchmark(f"api_endpoint_{endpoint}")
        
        try:
            async with httpx.AsyncClient() as client:
                for i in range(iterations):
                    start_time = time.time()
                    
                    try:
                        response = await client.get(f"http://localhost:8000{endpoint}", params=params)
                        duration = time.time() - start_time
                        durations.append(duration)
                        
                        if response.status_code == 200:
                            successes += 1
                            
                    except Exception as e:
                        logger.warning(f"API request {i+1} failed: {e}")
                        durations.append(float('inf'))
            
            result = self.end_benchmark(f"api_endpoint_{endpoint}")
            result.update({
                'endpoint': endpoint,
                'iterations': iterations,
                'successes': successes,
                'success_rate': successes / iterations,
                'avg_duration': round(statistics.mean([d for d in durations if d != float('inf')]), 4),
                'min_duration': round(min([d for d in durations if d != float('inf')]), 4),
                'max_duration': round(max([d for d in durations if d != float('inf')]), 4),
                'median_duration': round(statistics.median([d for d in durations if d != float('inf')]), 4)
            })
            
        except Exception as e:
            result = self.end_benchmark(f"api_endpoint_{endpoint}")
            result.update({
                'error': str(e),
                'success': False
            })
            
        return result
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
            'memory_available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
            'memory_percent': memory.percent,
            'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'disk_percent': round((disk.used / disk.total) * 100, 2)
        }
    
    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmark suite."""
        logger.info("Starting comprehensive performance benchmark")
        
        # System metrics
        system_metrics = self.get_system_metrics()
        
        # Test parameters
        test_params = StrategyParams(
            symbol="BTC/USDT",
            interval="15m",
            lookback_period=20,
            volume_threshold=1.5,
            take_profit=0.02,
            stop_loss=0.01,
            initial_capital=10000
        )
        
        # Run benchmarks
        benchmarks = {}
        
        # 1. Data fetching benchmark
        benchmarks['data_fetching'] = await self.benchmark_data_fetching()
        
        # 2. Strategy calculation benchmark (if data fetching succeeded)
        if benchmarks['data_fetching'].get('success'):
            fetcher = DataFetcher()
            data = await fetcher.fetch_candles("BTC/USDT", "15m", 1000)
            benchmarks['strategy_calculation'] = await self.benchmark_strategy_calculation(data, test_params)
        
        # 3. Complete backtest benchmark
        benchmarks['backtest_execution'] = await self.benchmark_backtest_execution(test_params)
        
        # 4. API endpoint benchmarks
        api_params = {
            'symbol': 'BTC/USDT',
            'interval': '15m',
            'take_profit': 0.02,
            'stop_loss': 0.01
        }
        
        benchmarks['api_health'] = await self.benchmark_api_endpoint('/api/v1/health', {}, 5)
        benchmarks['api_backtest'] = await self.benchmark_api_endpoint('/api/v1/backtest', api_params, 3)
        
        # Compile results
        comprehensive_results = {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': system_metrics,
            'benchmarks': benchmarks,
            'summary': self._generate_summary(benchmarks)
        }
        
        logger.info("Comprehensive benchmark completed")
        return comprehensive_results
    
    def _generate_summary(self, benchmarks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary from benchmark results."""
        summary = {
            'total_tests': len(benchmarks),
            'successful_tests': sum(1 for b in benchmarks.values() if b.get('success', False)),
            'failed_tests': sum(1 for b in benchmarks.values() if not b.get('success', True)),
            'performance_issues': [],
            'recommendations': []
        }
        
        # Analyze performance issues
        for test_name, result in benchmarks.items():
            if not result.get('success', True):
                summary['performance_issues'].append(f"{test_name}: {result.get('error', 'Unknown error')}")
            
            # Check for slow operations
            duration = result.get('duration_seconds', 0)
            if duration > 5.0:
                summary['performance_issues'].append(f"{test_name}: Slow operation ({duration:.2f}s)")
            
            # Check for high memory usage
            memory_delta = result.get('memory_delta_mb', 0)
            if memory_delta > 100:
                summary['performance_issues'].append(f"{test_name}: High memory usage ({memory_delta:.2f}MB)")
        
        # Generate recommendations
        if any('data_fetching' in issue for issue in summary['performance_issues']):
            summary['recommendations'].append("Consider implementing caching for data fetching")
        
        if any('strategy_calculation' in issue for issue in summary['performance_issues']):
            summary['recommendations'].append("Optimize strategy calculation algorithms")
        
        if any('api_endpoint' in issue for issue in summary['performance_issues']):
            summary['recommendations'].append("Implement API response caching and optimization")
        
        return summary
    
    def save_results(self, filename: str = None):
        """Save benchmark results to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Benchmark results saved to {filename}")


async def main():
    """Main function to run benchmarks."""
    benchmark = PerformanceBenchmark()
    
    try:
        results = await benchmark.run_comprehensive_benchmark()
        
        # Print summary
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*60)
        
        print(f"\nSystem Metrics:")
        for key, value in results['system_metrics'].items():
            print(f"  {key}: {value}")
        
        print(f"\nBenchmark Results:")
        for test_name, result in results['benchmarks'].items():
            status = "✅" if result.get('success', False) else "❌"
            duration = result.get('duration_seconds', 0)
            print(f"  {status} {test_name}: {duration:.4f}s")
        
        print(f"\nSummary:")
        summary = results['summary']
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Successful: {summary['successful_tests']}")
        print(f"  Failed: {summary['failed_tests']}")
        
        if summary['performance_issues']:
            print(f"\nPerformance Issues:")
            for issue in summary['performance_issues']:
                print(f"  ⚠️  {issue}")
        
        if summary['recommendations']:
            print(f"\nRecommendations:")
            for rec in summary['recommendations']:
                print(f"  💡 {rec}")
        
        # Save results
        benchmark.save_results()
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
