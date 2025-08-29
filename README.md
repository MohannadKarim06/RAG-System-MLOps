# RAG System MLOps - Document Question Answering Platform

> **Note**: This project is currently not deployed on AWS due to resource constraints, but complete deployment instructions are provided below for anyone who wants to deploy it.

## 📋 Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [System Architecture Diagrams](#system-architecture-diagrams)
6. [Prerequisites](#prerequisites)
7. [Local Development Setup](#local-development-setup)
8. [AWS Deployment](#aws-deployment)
9. [API Documentation](#api-documentation)
10. [User Interface](#user-interface)
11. [Monitoring & Observability](#monitoring--observability)
12. [Security Features](#security-features)
13. [Performance Optimization](#performance-optimization)
14. [Troubleshooting](#troubleshooting)
15. [Contributing](#contributing)
16. [License](#license)

## 🎯 Overview

The RAG (Retrieval-Augmented Generation) System is a production-ready MLOps platform that enables users to upload documents and interact with them through natural language queries. The system combines the power of vector similarity search with large language models to provide accurate, contextual answers based on uploaded documents.

### Key Capabilities
- **Document Processing**: Automatic text extraction and chunking from PDF files
- **Semantic Search**: Vector-based similarity search using embeddings
- **AI-Powered QA**: Context-aware question answering using Claude 3 Sonnet
- **Multi-User Support**: Isolated user environments with API key authentication
- **Production Ready**: Containerized deployment with monitoring and security
- **Scalable Architecture**: Microservices design with load balancing

![Alt Text](images/folder/filename.png)

## 🏗️ Architecture

### High-Level Architecture
The system follows a microservices architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│   Nginx Proxy    │────│   FastAPI App   │
│   (Frontend)    │    │  (Load Balancer) │    │   (Backend)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
                  ┌────▼────┐    ┌────────────┐    ┌────▼────┐    ┌──────────────┐    ┌──▼─────┐
                  │PostgreSQL│    │   Redis    │    │   AWS   │    │  Pinecone    │    │   S3   │
                  │(Metadata)│    │ (Caching)  │    │Bedrock  │    │ (Vectors)    │    │(Files) │
                  └─────────┘    └────────────┘    └─────────┘    └──────────────┘    └────────┘
```

### Data Flow Architecture
```
User Upload → PDF Processing → Text Chunking → Embedding Generation → Vector Storage
     ↓
User Query → Query Embedding → Similarity Search → Context Retrieval → LLM Response
```

## 🚀 Features

### Core Features
- ✅ **Document Upload & Processing**: PDF text extraction with intelligent chunking
- ✅ **Semantic Search**: Vector similarity search powered by AWS Titan embeddings
- ✅ **AI Question Answering**: Claude 3 Sonnet integration via AWS Bedrock
- ✅ **Multi-User Support**: Isolated user environments with API authentication
- ✅ **File Management**: Upload, list, and delete documents with metadata tracking
- ✅ **Caching**: Redis-based response caching for improved performance
- ✅ **Rate Limiting**: API rate limits to prevent abuse
- ✅ **Real-time UI**: Streamlit-based chat interface with file management

### MLOps Features
- ✅ **Containerization**: Docker containers for all services
- ✅ **Orchestration**: Docker Compose for local development
- ✅ **CI/CD Pipeline**: GitHub Actions for automated deployment
- ✅ **Infrastructure as Code**: Complete AWS deployment automation
- ✅ **Monitoring**: Prometheus metrics collection
- ✅ **Load Balancing**: Nginx proxy with SSL termination
- ✅ **Security**: JWT authentication, rate limiting, HTTPS
- ✅ **Scalability**: Horizontal scaling support
- ✅ **Observability**: Comprehensive logging and health checks

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **Pydantic**: Data validation and settings management
- **AsyncPG**: Asynchronous PostgreSQL driver
- **Redis**: In-memory caching and session storage

### AI/ML
- **AWS Bedrock**: Claude 3 Sonnet for text generation
- **AWS Titan**: Text embeddings for semantic search
- **Pinecone**: Vector database for similarity search
- **PyMuPDF**: PDF text extraction

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **PostgreSQL**: Relational database
- **Redis**: Caching layer
- **Nginx**: Reverse proxy and load balancer
- **Prometheus**: Metrics and monitoring

### Frontend
- **Streamlit**: Interactive web application
- **Requests**: HTTP client for API communication

### Cloud Services
- **AWS S3**: File storage
- **AWS Bedrock**: AI model hosting
- **AWS EC2**: Compute instances
- **AWS CloudWatch**: Logging and monitoring

## 📊 System Architecture Diagrams

### 1. Service Architecture
```mermaid
graph TB
    Client[Web Client] --> Nginx[Nginx Load Balancer]
    Nginx --> Streamlit[Streamlit UI]
    Nginx --> FastAPI[FastAPI Backend]
    
    FastAPI --> PostgreSQL[(PostgreSQL)]
    FastAPI --> Redis[(Redis Cache)]
    FastAPI --> S3[AWS S3]
    FastAPI --> Pinecone[Pinecone Vector DB]
    FastAPI --> Bedrock[AWS Bedrock]
    
    Prometheus[Prometheus] --> FastAPI
    Prometheus --> PostgreSQL
    Prometheus --> Redis
```

### 2. Data Processing Pipeline
```mermaid
graph LR
    A[PDF Upload] --> B[Text Extraction]
    B --> C[Text Chunking]
    C --> D[Generate Embeddings]
    D --> E[Store in Pinecone]
    E --> F[Update Metadata]
    F --> G[Cache Results]
```

### 3. Query Processing Flow
```mermaid
graph LR
    A[User Query] --> B[Check Cache]
    B --> C{Cache Hit?}
    C -->|Yes| D[Return Cached Result]
    C -->|No| E[Generate Query Embedding]
    E --> F[Vector Similarity Search]
    F --> G[Retrieve Context]
    G --> H[Generate LLM Response]
    H --> I[Cache Response]
    I --> J[Return to User]
```

### 4. Deployment Architecture
```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Public Subnet"
                ALB[Application Load Balancer]
                NAT[NAT Gateway]
            end
            
            subgraph "Private Subnet"
                EC2[EC2 Instance]
                RDS[(RDS PostgreSQL)]
                ElastiCache[(ElastiCache Redis)]
            end
        end
        
        S3[(S3 Bucket)]
        Bedrock[AWS Bedrock]
        CloudWatch[CloudWatch]
    end
    
    Pinecone[Pinecone Cloud]
    
    Client[Users] --> ALB
    ALB --> EC2
    EC2 --> RDS
    EC2 --> ElastiCache
    EC2 --> S3
    EC2 --> Bedrock
    EC2 --> Pinecone
    EC2 --> CloudWatch
```

## 📁 Project Structure

```
RAG-System-MLOps/
├── 📁 app/                          # Main application code
│   ├── 📄 __init__.py
│   ├── 📄 main.py                   # FastAPI application entry point
│   ├── 📄 config.py                 # Configuration management
│   ├── 📄 database.py               # Database models and operations
│   ├── 📁 services/                 # Business logic services
│   │   ├── 📄 __init__.py
│   │   ├── 📄 file_service.py       # File processing and S3 operations
│   │   ├── 📄 rag_service.py        # RAG pipeline and LLM integration
│   │   └── 📄 embedding_service.py  # Vector embeddings and Pinecone
│   └── 📁 utils/                    # Utility functions
│       ├── 📄 __init__.py
│       ├── 📄 logger.py             # Logging configuration
│       ├── 📄 exceptions.py         # Custom exception classes
│       └── 📄 text_processor.py     # Text chunking and processing
│
├── 📁 ui/                           # Streamlit frontend
│   ├── 📄 app.py                    # Main Streamlit application
│   └── 📁 .streamlit/
│       └── 📄 secrets.toml          # Streamlit secrets
│
├── 📁 .github/                      # GitHub Actions CI/CD
│   └── 📁 workflows/
│       └── 📄 deploy.yml            # Automated deployment pipeline
│
├── 📁 cloudformation/               # Infrastructure as Code
│   └── 📄 rag-stack.yaml           # AWS CloudFormation template
│
├── 📁 nginx/                        # Reverse proxy configuration
│   ├── 📄 nginx.conf                # Nginx configuration
│   └── 📁 ssl/                      # SSL certificates
│       ├── 📄 cert.pem
│       └── 📄 key.pem
│
├── 📁 monitoring/                   # Observability configuration
│   └── 📄 prometheus.yml           # Prometheus metrics config
│
├── 📁 scripts/                      # Deployment and utility scripts
│   ├── 📄 setup-local.sh           # Local development setup
│   ├── 📄 deploy-aws.sh            # AWS deployment automation
│   └── 📄 backup-data.sh           # Data backup utilities
│
├── 📁 tests/                        # Test suites
│   ├── 📄 __init__.py
│   ├── 📄 test_api.py               # API endpoint tests
│   ├── 📄 test_services.py          # Service layer tests
│   └── 📄 test_integration.py       # Integration tests
│
├── 📁 docs/                         # Additional documentation
│   ├── 📄 api.md                    # API documentation
│   ├── 📄 deployment.md            # Deployment guides
│   └── 📄 troubleshooting.md       # Common issues and solutions
│
├── 📄 docker-compose.yaml          # Local development orchestration
├── 📄 Dockerfile.fastapi           # FastAPI container definition
├── 📄 Dockerfile.streamlit         # Streamlit container definition
├── 📄 requirements.txt             # Python dependencies
├── 📄 requirements.streamlit.txt   # Streamlit-specific dependencies
├── 📄 .env.example                 # Environment variables template
├── 📄 .gitignore                   # Git ignore patterns
└── 📄 README.md                    # Project documentation
```

### Key Components Explanation

- **`app/`**: Core FastAPI application with modular service architecture
- **`ui/`**: Streamlit-based user interface for document interaction
- **`services/`**: Business logic layer with clear separation of concerns
- **`.github/workflows/`**: Automated CI/CD pipeline for deployment
- **`cloudformation/`**: Infrastructure as Code for AWS resources
- **`nginx/`**: Production-ready reverse proxy with SSL support
- **`monitoring/`**: Observability stack with Prometheus metrics
- **`scripts/`**: Automation scripts for setup and deployment

## 📋 Prerequisites

### Required Accounts & Services
1. **AWS Account** with the following services enabled:
   - S3 (file storage)
   - Bedrock (AI models)
   - EC2 (compute)
   - VPC (networking)
   - IAM (permissions)

2. **Pinecone Account** for vector database

3. **Domain Name** (optional, for SSL)

### Required Software
- Docker and Docker Compose
- Git
- AWS CLI (for deployment)
- Python 3.11+ (for local development)

## 🏃‍♂️ Local Development Setup

### Quick Start Script

Create and run the setup script:

```bash
chmod +x setup-local.sh
./setup-local.sh
```

### Manual Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd RAG-System-MLOps
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Start services**
```bash
docker-compose up -d
```

4. **Access the application**
- Streamlit UI: http://localhost:8501
- FastAPI Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090

### Environment Variables

Create a `.env` file with the following variables:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=rag-documents

# Database Configuration
DATABASE_URL=postgresql://raguser:ragpassword@postgres:5432/ragdb

# Redis Configuration
REDIS_URL=redis://redis:6379

# Application Configuration
STREAMLIT_SECRET_KEY=your-streamlit-secret-key
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

## ☁️ AWS Deployment

### Prerequisites
1. AWS CLI installed and configured
2. Docker installed for building images
3. Domain name configured (optional)

### Deployment Script

Use the automated deployment script:

```bash
chmod +x deploy-aws.sh
./deploy-aws.sh
```

### Manual Deployment Steps

1. **Create S3 Bucket**
```bash
aws s3 mb s3://your-rag-system-bucket --region us-east-1
```

2. **Build and Push Docker Images**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Build and push images
docker build -t your-account.dkr.ecr.us-east-1.amazonaws.com/rag-fastapi:latest -f Dockerfile.fastapi .
docker build -t your-account.dkr.ecr.us-east-1.amazonaws.com/rag-streamlit:latest -f Dockerfile.streamlit .

docker push your-account.dkr.ecr.us-east-1.amazonaws.com/rag-fastapi:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/rag-streamlit:latest
```

3. **Launch EC2 Instance**
```bash
# Create security group
aws ec2 create-security-group --group-name rag-system-sg --description "RAG System Security Group"

# Add rules
aws ec2 authorize-security-group-ingress --group-name rag-system-sg --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name rag-system-sg --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name rag-system-sg --protocol tcp --port 443 --cidr 0.0.0.0/0

# Launch instance
aws ec2 run-instances --image-id ami-0abcdef1234567890 --count 1 --instance-type t3.medium --key-name your-key-pair --security-group-ids sg-12345678
```

4. **Setup RDS and ElastiCache**
```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier rag-postgres \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username raguser \
    --master-user-password yourpassword \
    --allocated-storage 20

# Create ElastiCache cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id rag-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1
```

### Infrastructure as Code (CloudFormation)

For production deployments, use the provided CloudFormation template:

```bash
aws cloudformation create-stack \
    --stack-name rag-system \
    --template-body file://cloudformation/rag-stack.yaml \
    --parameters ParameterKey=KeyPairName,ParameterValue=your-key-pair \
    --capabilities CAPABILITY_IAM
```

## 📚 API Documentation

### Authentication
All API endpoints require Bearer token authentication:
```http
Authorization: Bearer your-api-key
```

### Core Endpoints

#### Create User
```http
POST /users
```
**Response:**
```json
{
  "user_id": "uuid",
  "api_key": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "file_count": 0
}
```

#### Upload Document
```http
POST /upload
Content-Type: multipart/form-data
```
**Parameters:**
- `file`: PDF file (max 10MB)

**Response:**
```json
{
  "message": "File uploaded and processed successfully",
  "filename": "document.pdf",
  "chunk_count": 25,
  "file_id": "uuid"
}
```

#### Ask Question
```http
POST /ask
Content-Type: application/json
```
**Request:**
```json
{
  "question": "What is the main topic of the document?"
}
```
**Response:**
```json
{
  "answer": "The main topic is...",
  "sources": [
    {
      "filename": "document.pdf",
      "score": 0.95
    }
  ],
  "chunk_count": 3
}
```

#### List Files
```http
GET /files
```
**Response:**
```json
{
  "files": [
    {
      "id": "uuid",
      "filename": "document.pdf",
      "chunk_count": 25,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Delete File
```http
DELETE /files/{file_id}
```

#### Update Configuration
```http
PUT /config
Content-Type: application/json
```
**Request:**
```json
{
  "system_prompt": "You are a helpful assistant..."
}
```

### Rate Limits
- File uploads: 5 per hour
- Questions: 100 per hour

## 🖥️ User Interface

The system provides an intuitive Streamlit-based web interface with the following features:

### Main Interface
- **Authentication**: API key management and user creation
- **Document Upload**: Drag-and-drop PDF upload with progress tracking
- **Chat Interface**: Real-time conversation with documents
- **File Management**: View, delete, and manage uploaded documents
- **Settings**: Customize system prompts and preferences

### Screenshots

[**Insert UI Screenshot Here**]
*Caption: Main chat interface showing document upload, conversation history, and file management*

### Key UI Features
- 📱 **Responsive Design**: Works on desktop and mobile
- 🔄 **Real-time Updates**: Live chat with typing indicators
- 📎 **Source Attribution**: See which documents were used for each answer
- 🎨 **Clean Interface**: Intuitive design with clear navigation
- ⚡ **Fast Performance**: Cached responses for quick interactions

## 📊 Monitoring & Observability

### Metrics Collection
The system collects comprehensive metrics using Prometheus:

- **Application Metrics**:
  - Request count and latency
  - Error rates
  - Active users
  - Document processing times

- **Infrastructure Metrics**:
  - CPU and memory usage
  - Database connection pools
  - Redis cache hit rates
  - Storage utilization

### Health Checks
- **Application Health**: `/health` endpoint
- **Database Health**: Connection and query tests
- **External Services**: AWS Bedrock and Pinecone connectivity
- **Cache Health**: Redis availability

### Logging
Structured logging with different levels:
- **INFO**: Normal operations
- **WARN**: Potential issues
- **ERROR**: Failed operations
- **DEBUG**: Detailed debugging information

### Alerting
Configure alerts for:
- High error rates (>5%)
- Response time degradation (>2s)
- Resource utilization (>80%)
- Service downtime

## 🔒 Security Features

### Authentication & Authorization
- **API Key Authentication**: UUID-based API keys
- **User Isolation**: Complete data separation between users
- **Rate Limiting**: Prevent abuse with request limits

### Data Security
- **Encryption in Transit**: HTTPS/TLS for all communications
- **Encryption at Rest**: AWS S3 encryption for stored files
- **Secure Headers**: HSTS, CSP, and XSS protection
- **Input Validation**: Comprehensive request validation

### Infrastructure Security
- **Network Isolation**: VPC with private subnets
- **Security Groups**: Restrictive firewall rules
- **IAM Roles**: Least privilege access
- **Secrets Management**: Environment-based secret storage

### Compliance
- **Data Privacy**: User data isolation
- **Audit Logging**: Complete request logging
- **GDPR Ready**: Data deletion capabilities

## ⚡ Performance Optimization

### Caching Strategy
- **Response Caching**: Redis-based query result caching
- **CDN Integration**: Static asset optimization
- **Database Indexing**: Optimized database queries

### Scaling Features
- **Horizontal Scaling**: Multiple FastAPI instances
- **Load Balancing**: Nginx-based request distribution
- **Connection Pooling**: Efficient database connections
- **Async Processing**: Non-blocking I/O operations

### Resource Optimization
- **Vector Search**: Efficient similarity search
- **Text Chunking**: Optimized chunk sizes
- **Memory Management**: Garbage collection tuning
- **Container Optimization**: Multi-stage Docker builds

## 🐛 Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
docker-compose logs fastapi

# Verify environment variables
docker-compose config

# Restart services
docker-compose restart
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U raguser -d ragdb -c "SELECT 1;"

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### Vector Search Not Working
```bash
# Verify Pinecone connection
curl -X GET "https://controller.YOUR_ENVIRONMENT.pinecone.io/actions/whoami" \
     -H "Api-Key: YOUR_API_KEY"

# Check index status
python -c "
import pinecone
pinecone.init(api_key='YOUR_KEY')
print(pinecone.list_indexes())
"
```

#### AWS Bedrock Issues
```bash
# Test AWS credentials
aws bedrock list-foundation-models --region us-east-1

# Check IAM permissions
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::ACCOUNT:role/ROLE \
    --action-names bedrock:InvokeModel \
    --resource-arns "*"
```

### Performance Issues
- **High Memory Usage**: Increase container memory limits
- **Slow Responses**: Check Redis cache configuration
- **Database Timeouts**: Optimize queries and add indexes
- **Rate Limit Errors**: Adjust rate limiting configuration

### Monitoring Commands
```bash
# Check system resources
docker stats

# View application logs
docker-compose logs -f --tail=100

# Monitor database performance
docker-compose exec postgres pg_stat_activity

# Check Redis cache
docker-compose exec redis redis-cli info memory
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Install pre-commit hooks: `pre-commit install`
4. Make changes and commit: `git commit -m "Add new feature"`
5. Push and create PR: `git push origin feature/new-feature`

### Code Standards
- **Python**: Follow PEP 8 style guide
- **Docker**: Multi-stage builds and layer optimization
- **Documentation**: Update README for any new features
- **Testing**: Add tests for new functionality

### Pull Request Process
1. Update documentation
2. Add/update tests
3. Ensure CI passes
4. Request code review
5. Merge after approval

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🎯 Project Highlights for MLOps Portfolio

This project demonstrates several key MLOps competencies:

### ✅ **Production-Ready Architecture**
- Microservices design with Docker containerization
- Load balancing and reverse proxy setup
- Comprehensive monitoring and logging
- Security best practices implementation

### ✅ **CI/CD & DevOps**
- GitHub Actions pipeline for automated deployment
- Infrastructure as Code approach
- Automated testing and quality checks
- Containerized deployment strategy

### ✅ **Scalability & Performance**
- Horizontal scaling capabilities
- Caching layer for performance optimization
- Efficient vector database integration
- Resource monitoring and optimization

### ✅ **AI/ML Integration**
- Production ML model deployment (Claude 3)
- Vector embeddings and similarity search
- Real-time inference capabilities
- Model version management

### ✅ **Data Engineering**
- ETL pipeline for document processing
- Vector database management
- Data validation and quality checks
- Efficient data storage strategies

This project showcases the ability to build, deploy, and maintain production ML systems with modern MLOps practices and tools.
