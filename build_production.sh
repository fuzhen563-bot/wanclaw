#!/bin/bash
# WanClaw Production Build Script
# Usage: ./build_production.sh [output_dir]

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${1:-$PROJECT_DIR/dist}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================="
echo " WanClaw Production Build"
echo " Output: $OUTPUT_DIR"
echo " Time:   $TIMESTAMP"
echo "========================================="

# Clean output
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Copy backend source
echo "[1/5] Copying backend source..."
rsync -a --exclude='__pycache__' --exclude='*.pyc' \
  "$PROJECT_DIR/wanclaw/" "$OUTPUT_DIR/wanclaw/"

# Copy frontend assets
echo "[2/5] Copying frontend assets..."
rsync -a "$PROJECT_DIR/wanclaw/frontend/static/" "$OUTPUT_DIR/wanclaw/frontend/static/"
cp "$PROJECT_DIR/wanclaw/frontend/admin.html" "$OUTPUT_DIR/wanclaw/frontend/"

# Copy config
echo "[3/5] Copying config..."
mkdir -p "$OUTPUT_DIR/wanclaw/backend/im_adapter/config"
cp "$PROJECT_DIR/wanclaw/backend/im_adapter/config/config.yaml" \
  "$OUTPUT_DIR/wanclaw/backend/im_adapter/config/"

# Copy deployment files
echo "[4/5] Copying deployment files..."
cp "$PROJECT_DIR/README.md" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/DEPLOYMENT_MULTI_PLATFORM.md" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/Dockerfile" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/docker-compose.yml" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/deploy.sh" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$PROJECT_DIR/monitor.py" "$OUTPUT_DIR/" 2>/dev/null || true
chmod +x "$OUTPUT_DIR/deploy.sh" 2>/dev/null || true

# Generate requirements.txt
echo "[5/5] Generating requirements.txt..."
cat > "$OUTPUT_DIR/requirements.txt" << 'EOF'
pydantic>=2.0
pyyaml>=6.0
fastapi>=0.100.0
uvicorn>=0.20.0
httpx>=0.24.0
websockets>=11.0
python-telegram-bot>=20.0
aiofiles>=23.0
structlog>=23.0
psutil>=5.9
EOF

# Calculate size
TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)
FILE_COUNT=$(find "$OUTPUT_DIR" -type f | wc -l)

echo ""
echo "========================================="
echo " Build Complete!"
echo "========================================="
echo " Output:     $OUTPUT_DIR"
echo " Size:       $TOTAL_SIZE"
echo " Files:      $FILE_COUNT"
echo " Timestamp:  $TIMESTAMP"
echo ""
echo " To deploy:"
echo "   cd $OUTPUT_DIR"
echo "   pip install -r requirements.txt"
echo "   uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000"
echo "========================================="
