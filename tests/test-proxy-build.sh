#!/bin/bash
# Local test script for proxy package build

set -e

echo "🧪 Testing USRP Proxy Package Build Locally"
echo "============================================="

# Check if we're in the right directory
if [[ ! -f "src/usrp_proxy_dxt/package.json" ]]; then
    echo "❌ Run this script from the uhd-mcp project root"
    exit 1
fi

echo "📦 Installing dependencies..."
cd src/usrp_proxy_dxt
npm install

echo "✅ Validating proxy extension..."
node -e "
import('./server/index.js').then(() => {
  console.log('✅ Proxy syntax valid');
}).catch(err => {
  console.error('❌ Syntax error:', err.message);
  process.exit(1);
});
" &
VALIDATE_PID=$!

# Wait for validation process to complete and check exit status
wait $VALIDATE_PID
VALIDATE_EXIT_CODE=$?
if [ $VALIDATE_EXIT_CODE -eq 0 ]; then
    echo "✅ Proxy validation completed"
else
    echo "❌ Proxy validation failed"
    exit 1
fi
echo "📋 Validating manifest..."
npm run validate

echo "📁 Creating test package..."
cd ../../
rm -rf test-proxy-package
mkdir -p test-proxy-package/usrp-proxy-dxt

# Copy files
cp -r src/usrp_proxy_dxt/* test-proxy-package/usrp-proxy-dxt/

# Clean up development files
rm -rf test-proxy-package/usrp-proxy-dxt/node_modules
rm -f test-proxy-package/usrp-proxy-dxt/package-lock.json

# Install production dependencies
cd test-proxy-package/usrp-proxy-dxt
npm install --omit=dev --no-package-lock

# Get version
VERSION=$(node -e "console.log(JSON.parse(require('fs').readFileSync('manifest.json', 'utf8')).version)")
BUILD_NUM="local-$(date +%s)"

echo "📦 Package version: $VERSION"
echo "🏗️  Build number: $BUILD_NUM"

# Create archives
cd ..
echo "📦 Creating tar.gz..."
tar -czf "../usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.tar.gz" .

echo "📦 Creating zip..."
zip -r "../usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.zip" . > /dev/null

cd ..

# Generate checksums
echo "🔐 Generating checksums..."
sha256sum "usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.tar.gz" > checksums-local.txt
sha256sum "usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.zip" >> checksums-local.txt

echo ""
echo "✅ Local package build completed successfully!"
echo ""
echo "📋 Generated files:"
echo "   📦 usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.tar.gz"
echo "   📦 usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.zip"
echo "   🔐 checksums-local.txt"
echo ""
echo "🧹 Cleanup:"
echo "   rm -rf test-proxy-package"
echo "   rm usrp-proxy-dxt-v${VERSION}-${BUILD_NUM}.*"
echo "   rm checksums-local.txt"
