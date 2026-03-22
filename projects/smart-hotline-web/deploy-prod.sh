#!/bin/bash
# Production deployment script for Smart Hotline Next.js app

set -e

echo "🚀 Deploying Smart Hotline Next.js app to production..."

cd /root/projects/smart-hotline-web/nextjs-app

# Step 1: Create production environment file
echo "📝 Creating production environment file..."
cat > .env.production << EOF
# AVR Backend API Configuration
NEXT_PUBLIC_AVR_BACKEND_URL=http://localhost:3001
NEXT_PUBLIC_AVR_AGENT_BASE_URL=http://localhost:5002
NEXT_PUBLIC_AVR_SOPHIE_AGENT_URL=http://localhost:5007
NEXT_PUBLIC_AVR_FRONTEND_URL=http://localhost:8888

# Smart Hotline Configuration
NEXT_PUBLIC_SITE_URL=https://smart-hotline.com
NEXT_PUBLIC_APP_ENV=production

# API Timeouts (in milliseconds)
NEXT_PUBLIC_API_TIMEOUT=15000
EOF

# Step 2: Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install --production
else
    echo "Dependencies already installed"
fi

# Step 3: Build the app
echo "🔨 Building Next.js app..."
npm run build

# Step 4: Stop existing PM2 process if running
echo "🛑 Stopping existing PM2 process..."
pm2 stop smart-hotline-web 2>/dev/null || true
pm2 delete smart-hotline-web 2>/dev/null || true

# Step 5: Start with PM2
echo "🚀 Starting app with PM2..."
pm2 start npm --name "smart-hotline-web" -- start

# Step 6: Save PM2 configuration
echo "💾 Saving PM2 configuration..."
pm2 save

# Step 7: Configure PM2 to start on boot
echo "🔧 Setting up PM2 startup..."
pm2 startup 2>/dev/null || true

# Step 8: Check status
echo "📊 Checking deployment status..."
sleep 2
pm2 status smart-hotline-web

echo "✅ Deployment complete!"
echo "🌐 App should be accessible at: http://194.163.187.192:3000"
echo "📈 Check logs with: pm2 logs smart-hotline-web"