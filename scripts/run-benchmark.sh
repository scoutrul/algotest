#!/bin/bash

# Performance Benchmark Runner Script
# Runs comprehensive performance benchmarks for the BackTest Trading Bot

set -e

echo "🚀 Starting Performance Benchmark Suite"
echo "========================================"

# Check if backend is running
if ! curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "❌ Backend is not running. Please start the backend first:"
    echo "   cd backend && uvicorn app.main:app --reload"
    exit 1
fi

echo "✅ Backend is running"

# Install benchmark dependencies if needed
echo "📦 Installing benchmark dependencies..."
cd backend
source ../.venv/bin/activate
pip install -q psutil memory-profiler

# Run benchmark
echo "🔍 Running performance benchmarks..."
python -m benchmarks.performance_benchmark

echo ""
echo "📊 Benchmark completed!"
echo "Check the generated benchmark_results_*.json file for detailed results"
echo ""
echo "💡 Next steps:"
echo "   - Review performance metrics"
echo "   - Identify bottlenecks"
echo "   - Implement optimizations"
echo "   - Re-run benchmarks to measure improvements"
