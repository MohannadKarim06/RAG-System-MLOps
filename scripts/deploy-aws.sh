#!/bin/bash

# RAG System MLOps - AWS Deployment Script
# This script automates the deployment of the RAG system to AWS

set -e

echo "☁️  RAG System MLOps - AWS Deployment Starting..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME=${STACK_NAME:-rag-system}
KEY_PAIR_NAME=${KEY_PAIR_NAME:-rag-system-key}
INSTANCE_TYPE=${INSTANCE_TYPE:-t3.medium}
DOMAIN_NAME=${DOMAIN_NAME:-""}

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

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure'"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed. Some features may not work properly."
        echo "Install with: sudo apt-get install jq (Ubuntu) or brew install jq (Mac)"
    fi
    
    print_success "Prerequisites check passed!"
}

# Load environment variables
load_environment() {
    print_status "Loading environment configuration..."
    
    if [ ! -f .env ]; then
        print_error ".env file not found. Please run setup-local.sh first or create .env file."
        exit 1
    fi
    
    # Source environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Validate required variables
    required_vars=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "S3_BUCKET" "PINECONE_API_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required environment variable $var is not set in .env file"
            exit 1
        fi
    done
    
    print_success "Environment loaded successfully!"
}

# Create S3 bucket
create_s3_bucket() {
    print_status "Creating S3 bucket: $S3_BUCKET"
    
    if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
        print_warning "S3 bucket $S3_BUCKET already exists"
    else
        if [ "$AWS_REGION" = "us-east-1" ]; then
            aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION"
        else
            aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" \
                --create-bucket-configuration LocationConstraint="$AWS_REGION"
        fi
        
        # Enable versioning
        aws s3api put-bucket-versioning --bucket "$S3_BUCKET" \
            --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption --bucket "$S3_BUCKET" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
        
        print_success "S3 bucket created and configured!"
    fi
}

# Create ECR repositories
create_ecr_repositories() {
    print_status "Creating ECR repositories..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # Create repositories
    for repo in "rag-fastapi" "rag-streamlit"; do
        if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" &>/dev/null; then
            print_warning "ECR repository $repo already exists"
        else
            aws ecr create-repository --repository-name "$repo" --region "$AWS_REGION"
            print_success "Created ECR repository: $repo"
        fi
    done
    
    export ECR_URI
    print_success "ECR repositories ready!"
}

# Build and push Docker images
build_and_push_images() {
    print_status "Building and pushing Docker images..."
    
    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_URI"
    
    # Build and push FastAPI image
    print_status "Building FastAPI image..."
    docker build -t "$ECR_URI/rag-fastapi:latest" -f Dockerfile.fastapi .
    docker push "$ECR_URI/rag-fastapi:latest"
    
    # Build and push Streamlit image
    print_status "Building Streamlit image..."
    docker build -t "$ECR_URI/rag-streamlit:latest" -f Dockerfile.streamlit .
    docker push "$ECR_URI/rag-streamlit:latest"
    
    print_success "Docker images built and pushed!"
}

# Create key pair
create_key_pair() {
    print_status "Creating EC2 key pair..."
    
    if aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" --region "$AWS_REGION" &>/dev/null; then
        print_warning "Key pair $KEY_PAIR_NAME already exists"
    else
        aws ec2 create-key-pair --key-name "$KEY_PAIR_NAME" --region "$AWS_REGION" \
            --query 'KeyMaterial' --output text > "${KEY_PAIR_NAME}.pem"
        chmod 400 "${KEY_PAIR_NAME}.pem"
        print_success "Key pair created: ${KEY_PAIR_NAME}.pem"
        print_warning "Keep this file secure and don't commit it to version control!"
    fi
}

# Create CloudFormation template
create_cloudformation_template() {
    print_status "Creating CloudFormation template..."
    
    mkdir -p cloudformation
    
    cat > cloudformation/rag-stack.yaml << 'EOL'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'RAG System MLOps Infrastructure'

Parameters:
  KeyPairName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: Name of the EC2 Key Pair
  
  InstanceType:
    Type: String
    Default: t3.medium
    Description: EC2 instance type
  
  S3BucketName:
    Type: String
    Description: S3 bucket for file storage
  
  VpcCIDR:
    Type: String
    Default: 10.0.0.0/16
    Description: CIDR block for VPC

Resources:
  # VPC and Networking
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: !Ref VpcCIDR
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: RAG-VPC

  PublicSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: RAG-Public-Subnet

  PrivateSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [1, !GetAZs '']
      Tags:
        - Key: Name
          Value: RAG-Private-Subnet

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: RAG-IGW

  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      InternetGatewayId: !Ref InternetGateway
      VpcId: !Ref VPC

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: RAG-Public-Routes

  DefaultPublicRoute:
    Type: AWS::EC2::Route
    DependsOn: InternetGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnetRouteTableAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      RouteTableId: !Ref PublicRouteTable
      SubnetId: !Ref PublicSubnet

  # Security Groups
  WebSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: RAG-Web-SG
      GroupDescription: Security group for web traffic
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 8000
          ToPort: 8000
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 8501
          ToPort: 8501
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: RAG-Web-SG

  # IAM Role for EC2
  EC2Role:
    Type: AWS::IAM::Role
    Properties:
      RoleName: RAG-EC2-Role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonS3FullAccess
        - arn:aws:iam::aws:policy/AmazonBedrockFullAccess
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
      Policies:
        - PolicyName: ECRAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - ecr:GetAuthorizationToken
                  - ecr:BatchCheckLayerAvailability
                  - ecr:GetDownloadUrlForLayer
                  - ecr:BatchGetImage
                Resource: '*'

  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      InstanceProfileName: RAG-EC2-Profile
      Roles:
        - !Ref EC2Role

  # RDS Database
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Subnet group for RDS
      SubnetIds:
        - !Ref PublicSubnet
        - !Ref PrivateSubnet
      Tags:
        - Key: Name
          Value: RAG-DB-SubnetGroup

  RDSInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: rag-postgres
      DBInstanceClass: db.t3.micro
      Engine: postgres
      EngineVersion: '15.4'
      MasterUsername: raguser
      MasterUserPassword: ragpassword123
      AllocatedStorage: '20'
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !Ref WebSecurityGroup
      PubliclyAccessible: false
      BackupRetentionPeriod: 7
      Tags:
        - Key: Name
          Value: RAG-Database

  # ElastiCache Redis
  CacheSubnetGroup:
    Type: AWS::ElastiCache::SubnetGroup
    Properties:
      CacheSubnetGroupName: rag-cache-subnet-group
      Description: Subnet group for ElastiCache
      SubnetIds:
        - !Ref PublicSubnet
        - !Ref PrivateSubnet

  RedisCache:
    Type: AWS::ElastiCache::CacheCluster
    Properties:
      CacheClusterId: rag-redis
      CacheNodeType: cache.t3.micro
      Engine: redis
      NumCacheNodes: 1
      CacheSubnetGroupName: !Ref CacheSubnetGroup
      VpcSecurityGroupIds:
        - !Ref WebSecurityGroup
      Tags:
        - Key: Name
          Value: RAG-Redis

  # EC2 Instance
  WebServer:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-0abcdef1234567890  # Ubuntu 22.04 LTS (update this)
      InstanceType: !Ref InstanceType
      KeyName: !Ref KeyPairName
      SecurityGroupIds:
        - !Ref WebSecurityGroup
      SubnetId: !Ref PublicSubnet
      IamInstanceProfile: !Ref EC2InstanceProfile
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          apt-get update
          apt-get install -y docker.io docker-compose awscli
          systemctl start docker
          systemctl enable docker
          usermod -aG docker ubuntu
          
          # Install Docker Compose v2
          curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
          chmod +x /usr/local/bin/docker-compose
          
          # Clone repository (you'll need to update this with your actual repo)
          cd /home/ubuntu
          git clone https://github.com/yourusername/RAG-System-MLOps.git
          cd RAG-System-MLOps
          
          # Set up environment
          cat > .env << EOF
          AWS_REGION=${AWS::Region}
          S3_BUCKET=${S3BucketName}
          DATABASE_URL=postgresql://raguser:ragpassword123@${RDSInstance.Endpoint.Address}:5432/ragdb
          REDIS_URL=redis://${RedisCache.RedisEndpoint.Address}:6379
          EOF
          
          chown -R ubuntu:ubuntu /home/ubuntu/RAG-System-MLOps
      Tags:
        - Key: Name
          Value: RAG-WebServer

Outputs:
  PublicIP:
    Description: Public IP of the web server
    Value: !GetAtt WebServer.PublicIp
    Export:
      Name: !Sub ${AWS::StackName}-PublicIP
  
  DatabaseEndpoint:
    Description: RDS Database endpoint
    Value: !GetAtt RDSInstance.Endpoint.Address
    Export:
      Name: !Sub ${AWS::StackName}-DBEndpoint
  
  RedisEndpoint:
    Description: ElastiCache Redis endpoint
    Value: !GetAtt RedisCache.RedisEndpoint.Address
    Export:
      Name: !Sub ${AWS::StackName}-RedisEndpoint
EOL

    print_success "CloudFormation template created!"
}

# Deploy CloudFormation stack
deploy_cloudformation() {
    print_status "Deploying CloudFormation stack..."
    
    # Get latest Ubuntu AMI ID
    UBUNTU_AMI=$(aws ec2 describe-images \
        --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
        --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
        --output text \
        --region "$AWS_REGION")
    
    # Update template with correct AMI ID
    sed -i.bak "s/ami-0abcdef1234567890/$UBUNTU_AMI/g" cloudformation/rag-stack.yaml
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &>/dev/null; then
        print_status "Updating existing CloudFormation stack..."
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://cloudformation/rag-stack.yaml \
            --parameters \
                ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR_NAME" \
                ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
                ParameterKey=S3BucketName,ParameterValue="$S3_BUCKET" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION"
    else
        print_status "Creating new CloudFormation stack..."
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://cloudformation/rag-stack.yaml \
            --parameters \
                ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR_NAME" \
                ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
                ParameterKey=S3BucketName,ParameterValue="$S3_BUCKET" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION"
    fi
    
    # Wait for stack completion
    print_status "Waiting for CloudFormation stack to complete..."
    aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$AWS_REGION" 2>/dev/null || \
    aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$AWS_REGION"
    
    print_success "CloudFormation stack deployed successfully!"
}

# Get stack outputs
get_stack_outputs() {
    print_status "Retrieving stack outputs..."
    
    STACK_OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs' \
        --output json)
    
    PUBLIC_IP=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="PublicIP") | .OutputValue')
    DB_ENDPOINT=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="DatabaseEndpoint") | .OutputValue')
    REDIS_ENDPOINT=$(echo "$STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="RedisEndpoint") | .OutputValue')
    
    export PUBLIC_IP DB_ENDPOINT REDIS_ENDPOINT
    
    print_success "Stack outputs retrieved!"
}

# Configure DNS (if domain provided)
configure_dns() {
    if [ -n "$DOMAIN_NAME" ]; then
        print_status "Configuring DNS for domain: $DOMAIN_NAME"
        
        # Check if hosted zone exists
        HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
            --dns-name "$DOMAIN_NAME" \
            --query "HostedZones[?Name=='${DOMAIN_NAME}.'].Id" \
            --output text | sed 's|/hostedzone/||')
        
        if [ -n "$HOSTED_ZONE_ID" ]; then
            # Create A record
            cat > dns-record.json << EOF
{
    "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "$DOMAIN_NAME",
            "Type": "A",
            "TTL": 300,
            "ResourceRecords": [{
                "Value": "$PUBLIC_IP"
            }]
        }
    }]
}
EOF
            
            aws route53 change-resource-record-sets \
                --hosted-zone-id "$HOSTED_ZONE_ID" \
                --change-batch file://dns-record.json
            
            rm dns-record.json
            print_success "DNS configured for $DOMAIN_NAME"
        else
            print_warning "Hosted zone for $DOMAIN_NAME not found. Please configure DNS manually."
        fi
    fi
}

# Final setup on EC2 instance
setup_ec2_instance() {
    print_status "Setting up application on EC2 instance..."
    
    # Wait for EC2 instance to be ready
    print_status "Waiting for EC2 instance to be ready..."
    sleep 60
    
    # SSH key setup
    SSH_OPTIONS="-i ${KEY_PAIR_NAME}.pem -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    
    # Copy environment file and docker-compose
    print_status "Copying configuration files..."
    scp $SSH_OPTIONS .env "ubuntu@$PUBLIC_IP:/home/ubuntu/RAG-System-MLOps/"
    scp $SSH_OPTIONS docker-compose.yaml "ubuntu@$PUBLIC_IP:/home/ubuntu/RAG-System-MLOps/"
    
    # Execute setup on remote server
    ssh $SSH_OPTIONS "ubuntu@$PUBLIC_IP" << 'ENDSSH'
        cd /home/ubuntu/RAG-System-MLOps
        
        # Login to ECR
        aws ecr get-login-password --region ${AWS_REGION} | \
            docker login --username AWS --password-stdin ${ECR_URI}
        
        # Update docker-compose to use ECR images
        sed -i 's|build:|# build:|g' docker-compose.yaml
        sed -i "s|rag-fastapi:latest|${ECR_URI}/rag-fastapi:latest|g" docker-compose.yaml
        sed -i "s|rag-streamlit:latest|${ECR_URI}/rag-streamlit:latest|g" docker-compose.yaml
        
        # Start services
        docker-compose up -d
        
        # Wait for services to be ready
        sleep 30
        
        echo "Services started successfully!"
        docker-compose ps
ENDSSH
    
    print_success "EC2 instance setup completed!"
}

# Display deployment information
show_deployment_info() {
    print_success "🎉 AWS Deployment Completed Successfully!"
    echo ""
    echo "📊 Deployment Information:"
    echo "  • Stack Name:      $STACK_NAME"
    echo "  • Region:          $AWS_REGION"
    echo "  • Public IP:       $PUBLIC_IP"
    echo "  • Database:        $DB_ENDPOINT"
    echo "  • Redis:           $REDIS_ENDPOINT"
    echo ""
    echo "🌐 Access URLs:"
    if [ -n "$DOMAIN_NAME" ]; then
        echo "  • Application:     https://$DOMAIN_NAME"
        echo "  • Streamlit UI:    https://$DOMAIN_NAME"
        echo "  • API Docs:        https://$DOMAIN_NAME/api/docs"
    else
        echo "  • Application:     http://$PUBLIC_IP"
        echo "  • Streamlit UI:    http://$PUBLIC_IP:8501"
        echo "  • API Docs:        http://$PUBLIC_IP:8000/docs"
    fi
    echo ""
    echo "🔐 SSH Access:"
    echo "  ssh -i ${KEY_PAIR_NAME}.pem ubuntu@$PUBLIC_IP"
    echo ""
    echo "🛠️ Management Commands:"
    echo "  • View logs:       ssh ubuntu@$PUBLIC_IP 'cd RAG-System-MLOps && docker-compose logs'"
    echo "  • Restart:         ssh ubuntu@$PUBLIC_IP 'cd RAG-System-MLOps && docker-compose restart'"
    echo "  • Update:          ./deploy-aws.sh --update"
    echo ""
    echo "💰 Cost Estimation:"
    echo "  • EC2 (t3.medium): ~$30/month"
    echo "  • RDS (db.t3.micro): ~$15/month"
    echo "  • ElastiCache: ~$15/month"
    echo "  • Data transfer: Variable"
    echo ""
    echo "⚠️  Important Notes:"
    echo "  • Save your key file: ${KEY_PAIR_NAME}.pem"
    echo "  • Configure SSL certificate for production"
    echo "  • Set up monitoring and backups"
    echo "  • Review security group settings"
    echo ""
}

# Cleanup function
cleanup_deployment() {
    print_status "Cleaning up AWS resources..."
    
    # Delete CloudFormation stack
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$AWS_REGION"
    
    print_status "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$AWS_REGION"
    
    # Delete ECR repositories
    aws ecr delete-repository --repository-name "rag-fastapi" --region "$AWS_REGION" --force 2>/dev/null || true
    aws ecr delete-repository --repository-name "rag-streamlit" --region "$AWS_REGION" --force 2>/dev/null || true
    
    # Delete S3 bucket
    aws s3 rm "s3://$S3_BUCKET" --recursive 2>/dev/null || true
    aws s3api delete-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" 2>/dev/null || true
    
    # Delete key pair
    aws ec2 delete-key-pair --key-name "$KEY_PAIR_NAME" --region "$AWS_REGION" 2>/dev/null || true
    rm -f "${KEY_PAIR_NAME}.pem"
    
    print_success "AWS resources cleaned up!"
}

# Main execution function
main() {
    check_prerequisites
    load_environment
    create_s3_bucket
    create_ecr_repositories
    build_and_push_images
    create_key_pair
    create_cloudformation_template
    deploy_cloudformation
    get_stack_outputs
    configure_dns
    setup_ec2_instance
    show_deployment_info
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "RAG System MLOps - AWS Deployment Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h       Show this help message"
        echo "  --cleanup        Delete all AWS resources"
        echo "  --update         Update existing deployment"
        echo "  --dry-run        Validate template without deployment"
        echo ""
        echo "Environment Variables:"
        echo "  AWS_REGION       AWS region (default: us-east-1)"
        echo "  STACK_NAME       CloudFormation stack name (default: rag-system)"
        echo "  KEY_PAIR_NAME    EC2 key pair name (default: rag-system-key)"
        echo "  INSTANCE_TYPE    EC2 instance type (default: t3.medium)"
        echo "  DOMAIN_NAME      Domain name for DNS configuration (optional)"
        echo ""
        echo "Examples:"
        echo "  $0                           # Deploy with defaults"
        echo "  DOMAIN_NAME=myapp.com $0     # Deploy with custom domain"
        echo "  INSTANCE_TYPE=t3.large $0    # Deploy with larger instance"
        echo "  $0 --cleanup                 # Clean up all resources"
        echo ""
        exit 0
        ;;
    --cleanup)
        print_status "Starting AWS resource cleanup..."
        load_environment
        cleanup_deployment
        exit 0
        ;;
    --update)
        print_status "Updating existing deployment..."
        check_prerequisites
        load_environment
        build_and_push_images
        deploy_cloudformation
        get_stack_outputs
        setup_ec2_instance
        show_deployment_info
        exit 0
        ;;
    --dry-run)
        print_status "Validating CloudFormation template..."
        create_cloudformation_template
        aws cloudformation validate-template \
            --template-body file://cloudformation/rag-stack.yaml \
            --region "$AWS_REGION"
        print_success "Template validation successful!"
        exit 0
        ;;
    *)
        main
        ;;
esac