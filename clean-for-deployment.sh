#!/bin/bash
# Script to clean up large files before deployment

echo "Starting ultra-aggressive pre-deployment cleanup..."

# Remove ALL Hugging Face cache
echo "Removing ALL HuggingFace cache (will be downloaded when needed)..."
rm -rf .cache/huggingface

# Remove Playwright browser cache
echo "Removing Playwright browser cache..."
rm -rf .cache/ms-playwright

# Remove node modules that will be reinstalled during deployment
echo "Removing node_modules (will be reinstalled during deployment)..."
rm -rf node_modules

# Remove Python virtual environments
echo "Removing Python virtual environments..."
rm -rf .venv
rm -rf venv
rm -rf *env

# Remove all log files
echo "Removing log files..."
find . -name "*.log" -type f -delete
find . -name "*.log.*" -type f -delete

# Remove Python cache files
echo "Removing Python cache files..."
find . -name "*.pyc" -type f -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.cpython-*" -type f -delete 2>/dev/null || true

# Remove test data while preserving important assets
echo "Removing test data files while preserving important assets..."
rm -rf attached_assets/chrome-headless-shell-win32.zip

# Preserve important images but remove others
mkdir -p temp_assets
cp wS_token_400.png temp_assets/ 2>/dev/null || true
cp market_visualization_1740761270.png temp_assets/ 2>/dev/null || true
cp SonicLidzRound2.png temp_assets/ 2>/dev/null || true

# Delete non-essential images
find . -name "*.png" -type f -not -path "./public/*" -not -path "./dist/*" -delete
find . -name "*.jpg" -type f -not -path "./public/*" -not -path "./dist/*" -delete
find . -name "*.jpeg" -type f -not -path "./public/*" -not -path "./dist/*" -delete
find . -name "*.gif" -type f -not -path "./public/*" -not -path "./dist/*" -delete

# Move important images back
cp temp_assets/* . 2>/dev/null || true
rm -rf temp_assets

# Remove test output files
rm -rf output*.txt
rm -rf *test_output.txt
rm -rf logs/*.log
rm -rf logs/*.txt
rm -rf tests
find . -name "test_*.py" -not -name "test_telegram.py" -not -name "test_webbrowser_connection.py" -not -name "test_goat_connection.py" -delete

# Clean up cache directories
echo "Cleaning up cache directories..."
rm -rf .cache/pip
find .cache -type f -name "*.bin" -delete 2>/dev/null || true
find .cache -type f -name "*.tar.gz" -delete 2>/dev/null || true
find .cache -type f -name "*.whl" -delete 2>/dev/null || true
rm -rf .cache/torch
rm -rf .cache/tensorflow
rm -rf .cache/models
rm -rf .cache/transformers
rm -rf .cache/matplotlib
rm -rf .cache/tf_keras_vis

# Git cleanup - remove .git directory for deployment
echo "Removing Git history..."
rm -rf .git

# Clean ChromaDB files (they can be regenerated)
echo "Cleaning ChromaDB files..."
rm -rf chroma_db

# Remove test models and large unused data
echo "Removing test models and large data..."
rm -rf agents/models
rm -rf src/models
rm -rf trained_models
rm -rf test_fixtures
rm -rf migrations
rm -rf .pytest_cache

# Remove development files not needed in production
echo "Removing development files..."
rm -rf .vscode
rm -rf .idea
rm -rf *.ipynb
rm -rf .ipynb_checkpoints

# Preserve important documentation
mkdir -p temp_docs
cp README.md temp_docs/ 2>/dev/null || true
cp DEPLOYMENT_GUIDE.md temp_docs/ 2>/dev/null || true
cp README_TELEGRAM.md temp_docs/ 2>/dev/null || true

# Remove other markdown files
find . -name "*.md" -not -name "README.md" -not -name "DEPLOYMENT_GUIDE.md" -not -name "README_TELEGRAM.md" -delete
rm -rf LICENSE
rm -rf CHANGELOG
rm -rf .github
rm -rf docs

# Move important docs back
cp temp_docs/* . 2>/dev/null || true
rm -rf temp_docs
find . -name "*.test.js" -type f -delete
find . -name "*.test.ts" -type f -delete
find . -name "*.spec.js" -type f -delete
find . -name "*.spec.ts" -type f -delete

# Remove large JavaScript files that will be rebuilt
echo "Removing large JavaScript files..."
rm -rf dist/assets/*.map
find dist/assets -type f -name "*.js.map" -delete 2>/dev/null || true

# Remove large unwanted Python packages
echo "Removing large unwanted Python packages..."
rm -rf .local/lib/python*/site-packages/tensorflow
rm -rf .local/lib/python*/site-packages/torchvision
rm -rf .local/lib/python*/site-packages/torch/testing

# Remove temp files
echo "Removing temp files..."
find . -name ".DS_Store" -type f -delete
find . -name "Thumbs.db" -type f -delete
find . -name "*~" -type f -delete
find . -name "*.tmp" -type f -delete
find . -name "*.temp" -type f -delete
find . -name "*.swp" -type f -delete
find /tmp -type f -delete 2>/dev/null || true

# Print directory sizes after cleanup
echo "Directory sizes after cleanup:"
du -sh .cache/* 2>/dev/null | sort -hr
du -sh . 2>/dev/null

echo "Cleanup complete. Ready for deployment!"