#!/bin/bash
# ============================================================
# Parks Finder AWS Deployment Script
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
DB_PASSWORD="${DB_PASSWORD:-}"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Parks Finder AWS Deployment${NC}"
echo -e "${GREEN}  Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}  Region: ${REGION}${NC}"
echo -e "${GREEN}============================================${NC}"

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"

    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI not installed${NC}"
        exit 1
    fi

    if ! command -v sam &> /dev/null; then
        echo -e "${RED}Error: AWS SAM CLI not installed${NC}"
        echo "Install with: brew install aws-sam-cli"
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}Error: AWS credentials not configured${NC}"
        echo "Run: aws configure"
        exit 1
    fi

    echo -e "${GREEN}Prerequisites OK${NC}"
}

# Prompt for database password if not set
get_db_password() {
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "\n${YELLOW}Enter database password:${NC}"
        read -s DB_PASSWORD
        if [ -z "$DB_PASSWORD" ]; then
            echo -e "${RED}Error: Database password is required${NC}"
            exit 1
        fi
    fi
}

# Build the SAM application
build() {
    echo -e "\n${YELLOW}Building SAM application...${NC}"
    cd "$(dirname "$0")"
    sam build --config-env "$ENVIRONMENT"
    echo -e "${GREEN}Build complete${NC}"
}

# Deploy to AWS
deploy() {
    echo -e "\n${YELLOW}Deploying to AWS...${NC}"

    sam deploy \
        --config-env "$ENVIRONMENT" \
        --parameter-overrides "Environment=${ENVIRONMENT} DatabasePassword=${DB_PASSWORD}" \
        --no-fail-on-empty-changeset

    echo -e "${GREEN}Deployment complete${NC}"
}

# Get outputs
get_outputs() {
    echo -e "\n${YELLOW}Deployment Outputs:${NC}"
    STACK_NAME="parks-finder-${ENVIRONMENT}"

    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
        --output text)

    USER_POOL_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
        --output text)

    USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
        --output text)

    echo -e "\n${GREEN}============================================${NC}"
    echo -e "${GREEN}API Endpoint: ${API_ENDPOINT}${NC}"
    echo -e "${GREEN}User Pool ID: ${USER_POOL_ID}${NC}"
    echo -e "${GREEN}Client ID: ${USER_POOL_CLIENT_ID}${NC}"
    echo -e "${GREEN}============================================${NC}"

    echo -e "\n${YELLOW}Update your iOS app's APIService.swift with:${NC}"
    echo "private let baseURL = \"${API_ENDPOINT}\""
}

# Upload park data to S3
upload_data() {
    echo -e "\n${YELLOW}Uploading park data to S3...${NC}"
    STACK_NAME="parks-finder-${ENVIRONMENT}"

    BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='DataBucketName'].OutputValue" \
        --output text)

    if [ -f "../source_data/fairfax_parks.json" ]; then
        aws s3 cp ../source_data/fairfax_parks.json "s3://${BUCKET_NAME}/data/fairfax_parks.json"
        echo -e "${GREEN}Park data uploaded to S3${NC}"
    else
        echo -e "${YELLOW}Warning: fairfax_parks.json not found${NC}"
    fi
}

# Initialize database
init_db() {
    echo -e "\n${YELLOW}Database initialization instructions:${NC}"
    echo "1. Connect to RDS using a bastion host or VPN"
    echo "2. Run the SQL migrations to create tables"
    echo "3. Load initial park data"
    echo ""
    echo "For development, you can use the local SQLite database."
}

# Main execution
main() {
    check_prerequisites
    get_db_password
    build
    deploy
    get_outputs
    upload_data
    init_db

    echo -e "\n${GREEN}============================================${NC}"
    echo -e "${GREEN}  Deployment Complete!${NC}"
    echo -e "${GREEN}============================================${NC}"
}

# Run main
main
