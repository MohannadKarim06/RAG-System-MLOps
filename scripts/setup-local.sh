#!/bin/bash

# RAG System MLOps - Local Development Setup Script
# This script sets up the entire development environment

set -e

echo "🚀 RAG System MLOps - Local Setup Starting..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed!"
}

# Create environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    if [ ! -f .env ]; then
        cat > .env << EOL
# AWS Configuration (Required for production features)
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name

# Pinecone Configuration (Required for vector search)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=rag-documents

# Database Configuration (Auto-configured for local development)
DATABASE_URL=postgresql://raguser:ragpassword@postgres:5432/ragdb

# Redis Configuration (Auto-configured for local development)
REDIS_URL=redis://redis:6379

# Application Configuration
STREAMLIT_SECRET_KEY=your-streamlit-secret-key-$(openssl rand -hex 16)
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Development Settings
MAX_FILE_SIZE=10485760
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CHUNKS_PER_QUERY=5
EOL
        print_success "Environment file created: .env"
        print_warning "Please update .env with your actual AWS and Pinecone credentials!"
    else
        print_success "Environment file already exists: .env"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating required directories..."
    
    mkdir -p nginx/ssl
    mkdir -p monitoring
    mkdir -p logs
    
    print_success "Directories created successfully!"
}

# Generate self-signed SSL certificates for local development
generate_ssl_certs() {
    print_status "Generating SSL certificates for local development..."
    
    if [ ! -f nginx/ssl/cert.pem ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        print_success "SSL certificates generated!"
    else
        print_success "SSL certificates already exist!"
    fi
}

# Pull required Docker images
pull_docker_images() {
    print_status "Pulling required Docker images..."
    
    docker-compose pull
    
    print_success "Docker images pulled successfully!"
}

# Build custom Docker images
build_docker_images() {
    print_status "Building custom Docker images..."
    
    docker-compose build --no-cache
    
    print_success "Docker images built successfully!"
}

# Initialize database
init_database() {
    print_status "Initializing database..."
    
    # Start only PostgreSQL first
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Check if database is responding
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U raguser -d ragdb > /dev/null 2>&1; then
            print_success "Database is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Database failed to start after 30 attempts"
            exit 1
        fi
        sleep 2
        echo -n "."
    done
}

# Start all services
start_services() {
    print_status "Starting all services..."
    
    docker-compose up -d
    
    print_success "All services started!"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for FastAPI
    print_status "Checking FastAPI service..."
    for i in {1..60}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_success "FastAPI service is ready!"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "FastAPI service not responding, but continuing..."
            break
        fi
        sleep 2
        echo -n "."
    done
    
    # Wait for Streamlit
    print_status "Checking Streamlit service..."
    for i in {1..60}; do
        if curl -f http://localhost:8501 > /dev/null 2>&1; then
            print_success "Streamlit service is ready!"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "Streamlit service not responding, but continuing..."
            break
        fi
        sleep 2
        echo -n "."
    done
}

# Display service status
show_status() {
    print_status "Service Status:"
    echo ""
    docker-compose ps
    echo ""
}

# Display access information
show_access_info() {
    print_success "🎉 RAG System MLOps is now running!"
    echo ""
    echo "📱 Access URLs:"
    echo "  • Streamlit UI:    http://localhost:8501"
    echo "  • FastAPI Docs:    http://localhost:8000/docs"
    echo "  • FastAPI Health:  http://localhost:8000/health"
    echo "  • Prometheus:      http://localhost:9090"
    echo ""
    echo "🔧 Management Commands:"
    echo "  • View logs:       docker-compose logs -f"
    echo "  • Stop services:   docker-compose down"
    echo "  • Restart:         docker-compose restart"
    echo "  • Clean up:        docker-compose down -v --rmi all"
    echo ""
    echo "⚠️  Important Notes:"
    echo "  • Update .env with your AWS and Pinecone credentials"
    echo "  • SSL certificates are self-signed (browser will show warning)"
    echo "  • First startup may take a few minutes"
    echo ""
}

# Cleanup function for errors
cleanup_on_error() {
    print_error "Setup failed. Cleaning up..."
    docker-compose down -v 2>/dev/null || true
}

# Main execution
main() {
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Execute setup steps
    check_prerequisites
    create_env_file
    create_directories
    generate_ssl_certs
    pull_docker_images
    build_docker_images
    init_database
    start_services
    wait_for_services
    show_status
    show_access_info
    
    print_success "Local development setup completed successfully! 🚀"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "RAG System MLOps - Local Development Setup"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --clean        Clean up existing containers and volumes"
        echo "  --rebuild      Force rebuild of Docker images"
        echo "  --quick        Skip image pulling and building (use existing)"
        echo ""
        echo "Examples:"
        echo "  $0              # Normal setup"
        echo "  $0 --clean     # Clean setup from scratch"
        echo "  $0 --rebuild   # Rebuild Docker images"
        echo "  $0 --quick     # Quick start with existing images"
        echo ""
        exit 0
        ;;
    --clean)
        print_status "Cleaning up existing setup..."
        docker-compose down -v --rmi all 2>/dev/null || true
        docker system prune -f 2>/dev/null || true
        rm -rf nginx/ssl/*.pem 2>/dev/null || true
        print_success "Cleanup completed!"
        main
        ;;
    --rebuild)
        print_status "Force rebuilding Docker images..."
        docker-compose down 2>/dev/null || true
        docker-compose build --no-cache --pull
        main
        ;;
    --quick)
        print_status "Quick start mode - using existing images..."
        check_prerequisites
        create_env_file
        create_directories
        generate_ssl_certs
        start_services
        wait_for_services
        show_status
        show_access_info
        print_success "Quick setup completed! 🚀"
        ;;
    *)
        main
        ;;
esac