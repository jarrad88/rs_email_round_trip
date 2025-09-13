#!/bin/bash
# GitHub Repository Setup Verification Script

set -e

echo "🚀 Email Delivery Monitor - GitHub Deployment Setup"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
function log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
function log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if we're in the right directory
if [[ ! -f "email_delivery_monitor.py" ]]; then
    log_error "Please run this script from the project root directory"
    exit 1
fi

log_info "Checking project files for GitHub deployment..."

# Required files for GitHub deployment
required_files=(
    "Dockerfile"
    "docker-compose.yml" 
    "portainer-stack.yml"
    "config.docker.json"
    "requirements.txt"
    ".github/workflows/docker-build.yml"
    "PORTAINER_DEPLOYMENT.md"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        log_info "✓ Found: $file"
    else
        log_error "✗ Missing: $file"
        missing_files+=("$file")
    fi
done

if [[ ${#missing_files[@]} -gt 0 ]]; then
    log_error "Missing required files. Please ensure all files are present."
    exit 1
fi

log_info "All required files present!"

# Check Docker configuration
log_info "Validating Docker configuration..."

if grep -q "ghcr.io/jarrad88/rs_email_round_trip" docker-compose.yml; then
    log_info "✓ Docker Compose configured for GitHub Container Registry"
else
    log_warn "Docker Compose might not be configured for GitHub registry"
fi

if grep -q "ghcr.io/jarrad88/rs_email_round_trip" portainer-stack.yml; then
    log_info "✓ Portainer stack configured for GitHub Container Registry"  
else
    log_warn "Portainer stack might not be configured for GitHub registry"
fi

# Check GitHub Actions workflow
log_info "Validating GitHub Actions workflow..."

if [[ -f ".github/workflows/docker-build.yml" ]]; then
    if grep -q "jarrad88/rs_email_round_trip" .github/workflows/docker-build.yml; then
        log_info "✓ GitHub Actions workflow configured correctly"
    else
        log_warn "GitHub Actions workflow might need repository name update"
    fi
else
    log_error "GitHub Actions workflow file missing"
fi

# Environment variables check
log_info "Checking environment variable templates..."

required_env_vars=(
    "OFFICE365_TENANT_ID"
    "OFFICE365_CLIENT_ID"
    "OFFICE365_CLIENT_SECRET"
    "OFFICE365_SENDER_EMAIL"
    "GMAIL_RECIPIENT_EMAIL"
    "ZABBIX_SERVER"
)

env_files=("portainer-stack.yml" ".env.template")
for env_file in "${env_files[@]}"; do
    if [[ -f "$env_file" ]]; then
        log_info "Checking $env_file for required environment variables..."
        for var in "${required_env_vars[@]}"; do
            if grep -q "$var" "$env_file"; then
                log_info "  ✓ $var"
            else
                log_warn "  ✗ $var not found in $env_file"
            fi
        done
    fi
done

# Git repository check
log_info "Checking Git repository status..."

if git remote -v | grep -q "jarrad88/rs_email_round_trip"; then
    log_info "✓ Git remote configured for jarrad88/rs_email_round_trip"
else
    log_warn "Git remote might not be configured correctly"
    log_warn "Expected: https://github.com/jarrad88/rs_email_round_trip.git"
    log_warn "Current remotes:"
    git remote -v || log_warn "  No git remotes found"
fi

# Pre-deployment checklist
echo ""
log_info "🚀 Pre-Deployment Checklist:"
echo "================================"

echo "1. Push code to GitHub repository:"
echo "   git add ."
echo "   git commit -m 'Initial email delivery monitor setup'"
echo "   git push origin main"
echo ""

echo "2. Verify GitHub Actions build:"  
echo "   → Go to: https://github.com/jarrad88/rs_email_round_trip/actions"
echo "   → Check that the Docker build workflow runs successfully"
echo ""

echo "3. In Portainer, create new stack with:"
echo "   → Repository URL: https://github.com/jarrad88/rs_email_round_trip.git"
echo "   → Compose file: portainer-stack.yml"
echo "   → Authentication: Enable with GitHub token"
echo "   → Environment variables: Configure all required values"
echo ""

echo "4. After deployment:"
echo "   → Upload gmail_credentials.json to credentials volume"
echo "   → Complete Gmail OAuth flow via container console"
echo "   → Verify Zabbix metrics are being received"
echo ""

log_info "Setup verification complete! Ready for GitHub deployment."

# Optional: Test Docker build locally
read -p "Would you like to test Docker build locally? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Testing local Docker build..."
    
    if docker build -t email-delivery-monitor-test .; then
        log_info "✓ Docker build successful"
        
        # Test container can start
        if docker run --rm email-delivery-monitor-test python -c "from email_delivery_monitor import EmailDeliveryMonitor; print('Import test passed')"; then
            log_info "✓ Container test passed"
        else
            log_error "Container test failed"
        fi
        
        # Cleanup
        docker rmi email-delivery-monitor-test
    else
        log_error "Docker build failed"
    fi
fi

echo ""
log_info "🎉 All checks complete! You're ready to deploy via Portainer."
