#!/bin/bash
# Quick test script for the AI Backend API

echo "🧪 Running Test Suite for AI Backend API"
echo "========================================"
echo ""

# Run all tests with coverage
echo "📊 Running all tests with coverage..."
uv run pytest -v --cov=app --cov-report=term-missing --cov-report=html

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "📈 Coverage report generated:"
    echo "   - Terminal output above"
    echo "   - HTML report: htmlcov/index.html"
    echo ""
    echo "To view HTML coverage report, run:"
    echo "   open htmlcov/index.html  (macOS)"
    echo "   xdg-open htmlcov/index.html  (Linux)"
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi
