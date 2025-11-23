#!/bin/bash
# Project Cleanup Script
# Removes test files, old outputs, and organizes structure

echo "🧹 Starting project cleanup..."

# 1. Remove test files
echo "📝 Removing test files..."
rm -f test_*.py
rm -f debug_*.py
rm -rf tests/

# 2. Remove old chromedriver files
echo "🚗 Removing old chromedriver files..."
rm -f chromedriver-linux64.zip*
rm -f LICENSE.chromedriver
rm -f THIRD_PARTY_NOTICES.chromedriver

# 3. Clean outputs - keep only latest
echo "📊 Cleaning outputs folder..."
cd outputs/
# Keep latest JSON files
rm -f summaries.json summary_cache.json
# Keep latest PNGs, remove old ones
rm -f aspect_analysis.png menu_analysis.png
cd ..

# 4. Remove old scraped data (keep only latest)
echo "💾 Cleaning data/raw..."
cd data/raw/
# Keep only miku_reviews.csv (latest)
rm -f opentable_reviews.csv test_pipeline.csv
cd ../..

# 5. Remove temporary files
echo "🗑️  Removing temporary files..."
rm -f scraped_reviews.json
rm -f page_source.html
rm -f debug_page_source.html
rm -f download_nltk_data.py

# 6. Create .gitignore if missing
echo "📄 Creating .gitignore..."
cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Project specific
chromedriver-linux64/
chromedriver-linux64.zip*
*.log
debug_*.html
page_source.html

# Data
data/processed/*
!data/processed/.gitkeep

# Temp files
*.tmp
test_*.py
debug_*.py
scraped_reviews.json

# Environment
.env
GITIGNORE

# 7. Create .gitkeep for empty folders
touch data/processed/.gitkeep

echo "✅ Cleanup complete!"
echo ""
echo "📊 Project Status:"
echo "  • Test files: REMOVED"
echo "  • Old outputs: CLEANED"
echo "  • Data: ORGANIZED"
echo "  • Structure: READY"
