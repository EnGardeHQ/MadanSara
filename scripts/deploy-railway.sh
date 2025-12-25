#!/bin/bash
#
# Railway Deployment Script for Madan Sara Microservice
#
# This script deploys Madan Sara to Railway using the Railway CLI
# with GitHub subdirectory integration.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Madan Sara Railway Deployment                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}✗ Railway CLI not found${NC}"
    echo "  Install it with: npm install -g @railway/cli"
    echo "  Or: brew install railway"
    exit 1
fi

echo -e "${GREEN}✓ Railway CLI found${NC}"

# Check if logged in
if ! railway whoami &> /dev/null; then
    echo -e "${YELLOW}⚠ Not logged in to Railway${NC}"
    echo "  Logging in..."
    railway login
fi

echo -e "${GREEN}✓ Logged in to Railway${NC}"

# Set project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "  Project root: $PROJECT_ROOT"

# Service name
SERVICE_NAME="madan-sara"
echo "  Service name: $SERVICE_NAME"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}⚠ No .env file found${NC}"
    echo "  Creating from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo -e "${YELLOW}  Please edit .env with your configuration${NC}"
    read -p "Press enter when ready to continue..."
fi

# Ask for environment
echo ""
echo "Select environment:"
echo "  1) Production"
echo "  2) Staging"
read -p "Choice (1 or 2): " ENV_CHOICE

if [ "$ENV_CHOICE" = "1" ]; then
    RAILWAY_ENV="production"
elif [ "$ENV_CHOICE" = "2" ]; then
    RAILWAY_ENV="staging"
else
    echo -e "${RED}✗ Invalid choice${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment: $RAILWAY_ENV${NC}"

# Link to Railway project
echo ""
echo -e "${YELLOW}➜ Linking to Railway project...${NC}"

# Check if already linked
if [ ! -f "$PROJECT_ROOT/.railway" ]; then
    railway link
else
    echo -e "${GREEN}✓ Already linked to Railway project${NC}"
fi

# Set environment
railway environment $RAILWAY_ENV

# Push environment variables
echo ""
echo -e "${YELLOW}➜ Setting environment variables...${NC}"

# Read .env and set variables
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue

    # Remove quotes from value
    value=$(echo $value | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")

    # Set in Railway
    railway variables set "$key=$value" --environment $RAILWAY_ENV
done < "$PROJECT_ROOT/.env"

echo -e "${GREEN}✓ Environment variables set${NC}"

# Set required shared variables
echo ""
echo -e "${YELLOW}➜ Setting shared En Garde variables...${NC}"

# These should be shared across all microservices
railway variables set SERVICE_NAME="$SERVICE_NAME" --environment $RAILWAY_ENV
railway variables set SERVICE_TYPE="intelligence-microservice" --environment $RAILWAY_ENV
railway variables set PYTHON_VERSION="3.11" --environment $RAILWAY_ENV

echo -e "${GREEN}✓ Shared variables set${NC}"

# Deploy
echo ""
echo -e "${YELLOW}➜ Deploying to Railway...${NC}"
echo "  This may take a few minutes..."

railway up --detach --environment $RAILWAY_ENV

echo ""
echo -e "${GREEN}✓ Deployment initiated${NC}"

# Get deployment status
echo ""
echo -e "${YELLOW}➜ Getting deployment status...${NC}"
sleep 5  # Wait for deployment to start

railway status --environment $RAILWAY_ENV

# Get service URL
echo ""
echo -e "${YELLOW}➜ Getting service URL...${NC}"
SERVICE_URL=$(railway domain --environment $RAILWAY_ENV 2>/dev/null || echo "Not yet assigned")

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Complete                                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Service: ${GREEN}$SERVICE_NAME${NC}"
echo -e "  Environment: ${GREEN}$RAILWAY_ENV${NC}"
echo -e "  URL: ${GREEN}$SERVICE_URL${NC}"
echo ""
echo "Next steps:"
echo "  1. Check logs: railway logs --environment $RAILWAY_ENV"
echo "  2. Test health: curl $SERVICE_URL/health"
echo "  3. View in Railway: railway open"
echo ""
echo -e "${GREEN}✓ Done!${NC}"
