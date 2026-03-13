# AWS Deployment for Parks Finder

This directory contains AWS SAM (Serverless Application Model) templates for deploying the Parks Finder backend to AWS.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    iPhone App                            │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   API Gateway                            │
│              (REST API + CORS)                           │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Lambda (FastAPI + Mangum)                   │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   /query    │  │   /parks    │  │     /users      │  │
│  │  (RAG AI)   │  │  (CRUD)     │  │  (Auth/Profile) │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
             ▼                            ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│    RDS PostgreSQL       │    │        S3 Bucket         │
│    (db.t3.micro)        │    │    - Park data JSON      │
│                         │    │    - User photos         │
│  - Users                │    │    - ChromaDB vectors    │
│  - Reviews              │    └──────────────────────────┘
│  - Conversations        │
│  - Saved Parks          │    ┌──────────────────────────┐
└─────────────────────────┘    │       Cognito            │
                               │    - User Pool           │
                               │    - Apple Sign-In       │
                               └──────────────────────────┘
```

## Prerequisites

1. **AWS CLI** - Install and configure with your credentials
   ```bash
   brew install awscli
   aws configure
   ```

2. **AWS SAM CLI** - For building and deploying
   ```bash
   brew install aws-sam-cli
   ```

3. **Python 3.11** - For Lambda runtime
   ```bash
   brew install python@3.11
   ```

## Quick Start

### 1. Deploy to Development

```bash
# Set your database password
export DB_PASSWORD="your-secure-password"

# Deploy
./deploy.sh dev
```

### 2. Deploy to Production

```bash
export DB_PASSWORD="your-production-password"
./deploy.sh prod
```

## Manual Deployment Steps

### Build

```bash
cd aws
sam build --config-env dev
```

### Validate Template

```bash
sam validate --lint
```

### Deploy

```bash
sam deploy \
  --config-env dev \
  --parameter-overrides "Environment=dev DatabasePassword=your-password" \
  --guided
```

### View Logs

```bash
sam logs -n ApiFunction --stack-name parks-finder-dev --tail
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | dev/staging/prod | dev |
| `DB_HOST` | RDS endpoint | (from CloudFormation) |
| `DB_NAME` | Database name | parks_finder |
| `DB_USER` | Database user | parks_admin |
| `DB_PASSWORD` | Database password | (required) |
| `OLLAMA_ENDPOINT` | External Ollama API | (optional) |

### Estimated Costs (Monthly)

| Resource | Dev | Production |
|----------|-----|------------|
| RDS (db.t3.micro) | $15 | $30 (Multi-AZ) |
| Lambda | $0-5 | $10-50 |
| API Gateway | $3.50/million | $3.50/million |
| NAT Gateway | $32 | $32 |
| S3 | $1-5 | $5-20 |
| **Total** | **~$50** | **~$100+** |

### Cost Optimization Tips

1. **Use Lambda Reserved Concurrency** - Prevent runaway costs
2. **RDS Stop/Start** - Stop dev database when not in use
3. **Remove NAT Gateway in Dev** - Use VPC endpoints instead
4. **Use S3 Lifecycle Rules** - Auto-delete old versions

## Updating the iOS App

After deployment, update `APIService.swift`:

```swift
#if DEBUG
private let baseURL = "http://localhost:8000"  // Local development
#else
private let baseURL = "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod"
#endif
```

## LLM Considerations

The RAG system uses Ollama for local LLM inference. For AWS Lambda:

### Option 1: External Ollama Server (Recommended for Dev)
- Run Ollama on an EC2 instance
- Set `OLLAMA_ENDPOINT` to the EC2 endpoint
- Cost: ~$30/month for t3.medium

### Option 2: Use Claude API (Recommended for Prod)
- Replace Ollama with Anthropic's Claude API
- Update `server.py` to use `langchain-anthropic`
- Cost: Pay per token (~$0.01/query)

### Option 3: Amazon Bedrock
- Use AWS-native Claude or other models
- Native VPC integration
- Cost: Pay per token

## Troubleshooting

### Lambda Timeout
If the Lambda times out, increase the timeout in `template.yaml`:
```yaml
Timeout: 120  # seconds
```

### Database Connection Issues
Check security group rules allow Lambda to connect to RDS on port 5432.

### CORS Errors
Verify the API Gateway CORS configuration matches your app's origin.

## Clean Up

To delete all resources:

```bash
sam delete --stack-name parks-finder-dev
```

**Warning**: This will delete the RDS database and all data!
