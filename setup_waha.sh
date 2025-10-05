#!/bin/bash

echo "🚀 Setting up WAHA WhatsApp Bot"
echo "================================"

# Create sessions directory
echo "📁 Creating sessions directory..."
mkdir -p sessions

# Create .env file if it doesn't exist
if [ ! -f "Whatsappagent/.env" ]; then
    echo "📝 Creating .env file..."
    cat > Whatsappagent/.env << EOF
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Masumi Payment Configuration
PAYMENT_SERVICE_URL=your_payment_service_url
PAYMENT_API_KEY=your_payment_api_key
AGENT_IDENTIFIER=your_agent_identifier
SELLER_VKEY=your_seller_vkey
NETWORK=testnet
PAYMENT_AMOUNT=10000000
PAYMENT_UNIT=lovelace

# WAHA Configuration
WAHA_BASE_URL=http://localhost:3000
WAHA_SESSION_NAME=default
WAHA_API_KEY=your_waha_api_key_here
WEBHOOK_URL=http://localhost:8000/webhook

# Application Configuration
LOG_LEVEL=INFO
EOF
    echo "✅ .env file created. Please update it with your actual values."
else
    echo "✅ .env file already exists."
fi

echo ""
echo "🐳 Starting WAHA and Bot with Docker Compose..."
echo "This will start both WAHA and your bot application."
echo ""

# Check if we're on ARM architecture
if [[ $(uname -m) == "arm64" ]]; then
    echo "🍎 Detected ARM architecture (Apple Silicon)"
    echo "Using ARM-compatible WAHA image..."
fi

# Start the services
docker-compose up -d

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Check the logs: docker-compose logs -f"
echo "2. Open WAHA dashboard: http://localhost:3000/dashboard"
echo "3. Start a session and scan QR code"
echo "4. Test your bot by sending messages to WhatsApp"
echo ""
echo "Useful commands:"
echo "- View logs: docker-compose logs -f"
echo "- Stop services: docker-compose down"
echo "- Restart services: docker-compose restart"
echo "- Check status: docker-compose ps"
