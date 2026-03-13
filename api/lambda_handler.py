"""
AWS Lambda handler for FastAPI using Mangum.

This adapter allows the FastAPI application to run on AWS Lambda
behind API Gateway.
"""
from mangum import Mangum
from .server import app

# Create the Lambda handler
handler = Mangum(app, lifespan="off")
