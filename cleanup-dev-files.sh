echo "🧹 Cleaning up development files..."

if [ -d "frontend/node_modules" ]; then
    echo "Removing frontend/node_modules..."
    rm -rf frontend/node_modules/
fi

sfind . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null


rm -f .DS_Store */.DS_Store
rm -f package-lock.json frontend/package-lock.json

echo "✅ Cleanup complete!"
echo "Your SplitMe app is ready for end users."