#!/bin/bash
# Docker management script for Email Delivery Monitor

set -e

IMAGE_NAME="email-delivery-monitor"
CONTAINER_NAME="email-delivery-monitor"
VERSION="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function check_env_file() {
    if [[ ! -f .env ]]; then
        log_warn ".env file not found. Creating from template..."
        if [[ -f .env.template ]]; then
            cp .env.template .env
            log_warn "Please edit .env file with your actual credentials before deploying!"
            return 1
        else
            log_error ".env.template not found!"
            return 1
        fi
    fi
    return 0
}

function build_image() {
    log_info "Building Docker image: $IMAGE_NAME:$VERSION"
    docker build -t "$IMAGE_NAME:$VERSION" .
    log_info "Build completed successfully"
}

function run_container() {
    if ! check_env_file; then
        log_error "Environment configuration required before running"
        exit 1
    fi
    
    log_info "Starting container: $CONTAINER_NAME"
    
    # Stop existing container if running
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_warn "Container $CONTAINER_NAME is already running. Stopping..."
        docker stop "$CONTAINER_NAME"
        docker rm "$CONTAINER_NAME"
    fi
    
    # Create required directories
    mkdir -p ./logs ./credentials ./config
    
    # Run container
    docker run -d \
        --name "$CONTAINER_NAME" \
        --env-file .env \
        -v "$(pwd)/logs:/app/logs" \
        -v "$(pwd)/credentials:/app/credentials" \
        --restart unless-stopped \
        "$IMAGE_NAME:$VERSION"
    
    log_info "Container started successfully. ID: $(docker ps -q -f name="$CONTAINER_NAME")"
}

function stop_container() {
    log_info "Stopping container: $CONTAINER_NAME"
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        docker stop "$CONTAINER_NAME"
        docker rm "$CONTAINER_NAME"
        log_info "Container stopped and removed"
    else
        log_warn "Container $CONTAINER_NAME is not running"
    fi
}

function show_logs() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_info "Showing logs for container: $CONTAINER_NAME"
        docker logs -f "$CONTAINER_NAME"
    else
        log_error "Container $CONTAINER_NAME is not running"
        exit 1
    fi
}

function show_status() {
    log_info "Container Status:"
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        docker ps -f name="$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        log_info "Resource Usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" "$CONTAINER_NAME"
    else
        log_warn "Container $CONTAINER_NAME is not running"
    fi
    
    # Show recent logs
    if docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo ""
        log_info "Recent Logs (last 10 lines):"
        docker logs --tail 10 "$CONTAINER_NAME" 2>/dev/null || log_warn "No logs available"
    fi
}

function run_test() {
    if ! docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_error "Container $CONTAINER_NAME is not running. Start it first with: $0 start"
        exit 1
    fi
    
    log_info "Running email delivery test..."
    docker exec "$CONTAINER_NAME" python email_delivery_monitor.py --test
}

function shell_access() {
    if ! docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_error "Container $CONTAINER_NAME is not running. Start it first with: $0 start"
        exit 1
    fi
    
    log_info "Opening shell in container: $CONTAINER_NAME"
    docker exec -it "$CONTAINER_NAME" /bin/bash
}

function cleanup() {
    log_info "Cleaning up Docker resources..."
    
    # Stop and remove container
    if docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
    fi
    
    # Remove image
    if docker images -q "$IMAGE_NAME:$VERSION" | grep -q .; then
        docker rmi "$IMAGE_NAME:$VERSION"
    fi
    
    # Clean up unused resources
    docker system prune -f
    
    log_info "Cleanup completed"
}

function show_help() {
    echo "Email Delivery Monitor - Docker Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build     Build Docker image"
    echo "  start     Start container (builds image if needed)"
    echo "  stop      Stop and remove container"
    echo "  restart   Stop and start container"
    echo "  logs      Show container logs (follow mode)"
    echo "  status    Show container status and recent logs"
    echo "  test      Run single email delivery test"
    echo "  shell     Open shell in running container"
    echo "  cleanup   Stop container and clean up Docker resources"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build              # Build the Docker image"
    echo "  $0 start              # Start monitoring"
    echo "  $0 logs               # View logs"
    echo "  $0 test               # Run a test"
    echo "  $0 status             # Check status"
    echo ""
}

# Main script logic
case "${1:-help}" in
    build)
        build_image
        ;;
    start)
        if ! docker images -q "$IMAGE_NAME:$VERSION" | grep -q .; then
            log_info "Image not found. Building first..."
            build_image
        fi
        run_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        stop_container
        sleep 2
        run_container
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    test)
        run_test
        ;;
    shell)
        shell_access
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
