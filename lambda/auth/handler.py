"""
Auth Lambda - User authentication and tier management
Handles registration, login, token refresh, and subscription validation
"""
import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

from validation import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ValidateSubscriptionRequest,
    validate_request
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')

# Environment variables
USERS_TABLE_NAME = os.environ['USERS_TABLE']
USER_POOL_ID = os.environ['USER_POOL_ID']
USER_POOL_CLIENT_ID = os.environ['USER_POOL_CLIENT_ID']

FREE_TRIAL_QUERY_LIMIT = 3

users_table = dynamodb.Table(USERS_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Auth operations.
    Routes requests based on HTTP path.
    """
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    
    try:
        if path == '/auth/register' and http_method == 'POST':
            return handle_register(event)
        elif path == '/auth/login' and http_method == 'POST':
            return handle_login(event)
        elif path == '/auth/refresh' and http_method == 'POST':
            return handle_refresh(event)
        elif path == '/auth/validate-subscription' and http_method == 'POST':
            return handle_validate_subscription(event)
        else:
            return format_response(404, {'error': 'Not found'})
    
    except Exception as e:
        logger.exception("Unhandled error in lambda_handler")
        return format_response(500, {'error': 'Internal server error'})


def get_user_tier(user_id: str) -> Dict[str, Any]:
    """
    Get user tier status: 'free', 'premium', or 'paywall'.
    
    Logic:
    1. Fetch user profile from DynamoDB
    2. If user not found, return error (don't silently grant trials)
    3. If premium and not expired, return 'premium'
    4. If premium but expired, persist the expiration and fall through
    5. If free trial queries < limit, return 'free'
    6. If free trial queries >= limit, return 'paywall'
    
    Requirements: 1.1, 1.2, 1.3
    """
    try:
        db_result = users_table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PROFILE',
            }
        )
    except ClientError as e:
        logger.error("DynamoDB error fetching user %s: %s", user_id, e)
        return _tier_error("Failed to fetch user profile")
    
    if 'Item' not in db_result:
        # Missing profile likely means a registration sync bug.
        # Flag it distinctly so callers can decide how to handle it.
        logger.warning("No DynamoDB profile found for user %s", user_id)
        return _tier_error("User profile not found")
    
    user = db_result['Item']
    is_premium = user.get('isPremium', False)
    
    # --- Premium path ---
    if is_premium:
        expired = _check_premium_expired(user, user_id)
        if not expired:
            return {
                'tier': 'premium',
                'isPremium': True,
                'premiumExpiresAt': user.get('premiumExpiresAt'),
                'freeTrialQueriesUsed': user.get('freeTrialQueriesUsed', 0),
                'freeTrialQueriesRemaining': 0,
            }
        # Premium expired — fall through to free/paywall logic
    
    # --- Free / Paywall path ---
    free_trial_queries_used = user.get('freeTrialQueriesUsed', 0)
    free_trial_queries_remaining = max(0, FREE_TRIAL_QUERY_LIMIT - free_trial_queries_used)
    
    if free_trial_queries_used >= FREE_TRIAL_QUERY_LIMIT:
        return {
            'tier': 'paywall',
            'isPremium': False,
            'freeTrialQueriesUsed': free_trial_queries_used,
            'freeTrialQueriesRemaining': 0,
            'freeTrialExhaustedAt': user.get('freeTrialExhaustedAt'),
        }
    
    return {
        'tier': 'free',
        'isPremium': False,
        'freeTrialQueriesUsed': free_trial_queries_used,
        'freeTrialQueriesRemaining': free_trial_queries_remaining,
    }


def _check_premium_expired(user: Dict[str, Any], user_id: str) -> bool:
    """
    Check whether the user's premium subscription has expired.
    If expired, persist the change back to DynamoDB so we don't
    re-evaluate on every request.
    
    Returns True if premium is expired, False if still active.
    """
    premium_expires_at = user.get('premiumExpiresAt')
    if premium_expires_at is None:
        # No expiration set — treat as perpetual premium
        return False
    
    # Validate that the stored value is actually a numeric timestamp
    if not isinstance(premium_expires_at, (int, float)):
        logger.error(
            "Invalid premiumExpiresAt type for user %s: %s (%s)",
            user_id, premium_expires_at, type(premium_expires_at).__name__,
        )
        # Fail closed: treat invalid data as expired so it gets corrected
        _persist_premium_expiration(user_id)
        return True
    
    current_time = int(datetime.now(timezone.utc).timestamp())
    if current_time <= premium_expires_at:
        return False
    
    # Premium has expired — write it back to DynamoDB
    _persist_premium_expiration(user_id)
    return True


def _persist_premium_expiration(user_id: str) -> None:
    """
    Write the premium expiration back to DynamoDB so subsequent
    calls skip the re-evaluation.
    """
    try:
        users_table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PROFILE',
            },
            UpdateExpression='SET isPremium = :false, premiumExpiredAt = :now',
            ConditionExpression='isPremium = :true',
            ExpressionAttributeValues={
                ':false': False,
                ':true': True,
                ':now': int(datetime.now(timezone.utc).timestamp()),
            },
        )
        logger.info("Persisted premium expiration for user %s", user_id)
    except ClientError as e:
        # ConditionalCheckFailed means another request already flipped it.
        # Any other error is worth logging but not worth failing the request.
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            logger.error(
                "Failed to persist premium expiration for user %s: %s",
                user_id, e,
            )


def increment_free_trial_usage(user_id: str) -> Dict[str, Any]:
    """
    Atomically increment freeTrialQueriesUsed with a condition guard
    to prevent exceeding the limit. Call this from your query handler
    BEFORE executing the query.
    
    Returns the updated usage count on success, or an error dict if
    the trial is already exhausted.
    """
    try:
        db_result = users_table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PROFILE',
            },
            UpdateExpression=(
                'SET freeTrialQueriesUsed = if_not_exists(freeTrialQueriesUsed, :zero) + :one'
            ),
            ConditionExpression=(
                'attribute_not_exists(freeTrialQueriesUsed) OR freeTrialQueriesUsed < :limit'
            ),
            ExpressionAttributeValues={
                ':zero': 0,
                ':one': 1,
                ':limit': FREE_TRIAL_QUERY_LIMIT,
            },
            ReturnValues='UPDATED_NEW',
        )
        new_count = int(db_result['Attributes']['freeTrialQueriesUsed'])
        
        # If this was the last free query, record when the trial was exhausted
        if new_count >= FREE_TRIAL_QUERY_LIMIT:
            _mark_trial_exhausted(user_id)
        
        return {
            'success': True,
            'freeTrialQueriesUsed': new_count,
            'freeTrialQueriesRemaining': max(0, FREE_TRIAL_QUERY_LIMIT - new_count),
        }
    
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'success': False,
                'error': 'Free trial exhausted',
                'tier': 'paywall',
            }
        logger.error("Failed to increment trial usage for user %s: %s", user_id, e)
        return {
            'success': False,
            'error': 'Failed to update trial usage',
        }


def _mark_trial_exhausted(user_id: str) -> None:
    """Record the timestamp when the free trial was exhausted."""
    try:
        users_table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PROFILE',
            },
            UpdateExpression='SET freeTrialExhaustedAt = :now',
            ExpressionAttributeValues={
                ':now': int(datetime.now(timezone.utc).timestamp()),
            },
        )
    except ClientError as e:
        logger.error("Failed to mark trial exhausted for user %s: %s", user_id, e)


def _tier_error(message: str) -> Dict[str, Any]:
    """
    Return a consistent error response from get_user_tier.
    Surfaces a safe message — internal details stay in logs.
    """
    return {
        'tier': 'error',
        'isPremium': False,
        'freeTrialQueriesUsed': 0,
        'freeTrialQueriesRemaining': 0,
        'error': message,
    }


# ---------------------------------------------------------------------------
# Route handlers (stubs)
# ---------------------------------------------------------------------------

def handle_register(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle user registration with Pydantic validation
    Requirements: 8.1, 9.5
    """
    body = event.get('body', '{}')
    
    # Validate request with Pydantic
    validated, error = validate_request(RegisterRequest, body)
    if error:
        return format_response(400, error)
    
    try:
        # Create user in Cognito
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=validated.email,
            UserAttributes=[
                {'Name': 'email', 'Value': validated.email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
            TemporaryPassword=validated.password,
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        cognito_user_id = response['User']['Username']
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=validated.email,
            Password=validated.password,
            Permanent=True
        )
        
        # Create user profile in DynamoDB
        current_time = int(datetime.now(timezone.utc).timestamp())
        users_table.put_item(
            Item={
                'PK': f'USER#{cognito_user_id}',
                'SK': 'PROFILE',
                'GSI1PK': f'EMAIL#{validated.email}',
                'email': validated.email,
                'name': validated.name,
                'cognitoId': cognito_user_id,
                'rank': 'tenderfoot',
                'isPremium': False,
                'freeTrialQueriesUsed': 0,
                'createdAt': current_time,
                'updatedAt': current_time,
            }
        )
        
        # Initiate auth to get tokens
        auth_response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=USER_POOL_CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': validated.email,
                'PASSWORD': validated.password,
            }
        )
        
        return format_response(201, {
            'userId': cognito_user_id,
            'email': validated.email,
            'accessToken': auth_response['AuthenticationResult']['AccessToken'],
            'refreshToken': auth_response['AuthenticationResult']['RefreshToken'],
            'expiresIn': auth_response['AuthenticationResult']['ExpiresIn'],
            'tier': 'free',
            'freeTrialQueriesRemaining': 3
        })
    
    except cognito.exceptions.UsernameExistsException:
        return format_response(409, {'error': 'User already exists'})
    except ClientError as e:
        logger.error("Registration error: %s", e)
        return format_response(500, {'error': 'Registration failed'})


def handle_login(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user login with email/password or Apple Sign In"""
    body = event.get('body', '{}')
    
    # Validate request with Pydantic
    validated, error = validate_request(LoginRequest, body)
    if error:
        return format_response(400, error)
    
    # TODO: Implement Apple Sign In flow in Phase 1
    # TODO: Implement standard email/password login
    return format_response(501, {'error': 'Not implemented yet'})


def handle_refresh(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle token refresh."""
    # TODO: Implement in Phase 1
    return format_response(501, {'error': 'Not implemented yet'})


def handle_validate_subscription(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle StoreKit subscription validation."""
    # TODO: Implement in Phase 1
    return format_response(501, {'error': 'Not implemented yet'})


def format_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Format API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        },
        'body': json.dumps(body),
    }
