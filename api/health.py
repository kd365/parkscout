"""
Simple health check Lambda handler.
"""
import json
from datetime import datetime


def handler(event, context):
    """Health check endpoint for AWS Lambda."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "aws-lambda",
            "version": "1.0.0"
        })
    }
