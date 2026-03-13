"""
AI Chat Lambda - LLM interactions with Self-RAG validation
Implements Self-RAG (Self-Reflective Retrieval-Augmented Generation) for response validation
Requirements: 1.2, 23.6, 23.7
"""
import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import hashlib

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')

# Environment variables
USERS_TABLE_NAME = os.environ['USERS_TABLE']
CLAUDE_API_SECRET_ARN = os.environ['CLAUDE_API_SECRET_ARN']
WEATHER_API_SECRET_ARN = os.environ['WEATHER_API_SECRET_ARN']
CACHE_CLUSTER_ENDPOINT = os.environ.get('CACHE_CLUSTER_ENDPOINT')
DB_SECRET_ARN = os.environ['DB_SECRET_ARN']

users_table = dynamodb.Table(USERS_TABLE_NAME)

# Cache for secrets (Lambda container reuse)
_secrets_cache = {}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for AI Chat operations
    Implements Self-RAG for response validation
    """
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    
    try:
        if path == '/chat/query' and http_method == 'POST':
            return handle_query(event)
        else:
            return format_response(404, {'error': 'Not found'})
    
    except Exception as e:
        logger.exception("Unhandled error in lambda_handler")
        return format_response(500, {'error': 'Internal server error'})


def handle_query(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle AI chat query with Self-RAG validation
    
    Self-RAG Flow:
    1. Retrieve relevant context (RAG)
    2. Generate initial response
    3. Self-critique: Is response relevant and accurate?
    4. If critique fails, retrieve additional context and regenerate
    5. Return validated response
    """
    body = json.loads(event.get('body', '{}'))
    user_id = body.get('userId')
    query = body.get('query')
    conversation_id = body.get('conversationId')
    
    if not user_id or not query:
        return format_response(400, {'error': 'userId and query are required'})
    
    # Check user tier and free trial usage
    tier_info = get_user_tier(user_id)
    
    if tier_info['tier'] == 'paywall':
        return format_response(403, {
            'error': 'Free trial exhausted',
            'message': 'Upgrade to premium to continue using AI chat',
            'freeTrialQueriesUsed': tier_info['freeTrialQueriesUsed'],
            'tier': 'paywall'
        })
    
    # For free users, increment trial usage atomically
    if tier_info['tier'] == 'free':
        increment_result = increment_free_trial_usage(user_id)
        if not increment_result['success']:
            return format_response(403, {
                'error': 'Free trial exhausted',
                'message': 'Upgrade to premium to continue using AI chat',
                'tier': 'paywall'
            })
        tier_info = increment_result
    
    # Normalize query for caching
    normalized_query = normalize_query(query)
    cache_key = f"query:{hashlib.md5(normalized_query.encode()).hexdigest()}"
    
    # Check cache first
    cached_response = get_from_cache(cache_key)
    if cached_response:
        logger.info("Cache hit for query: %s", normalized_query[:50])
        return format_response(200, {
            'response': cached_response['response'],
            'cached': True,
            'sources': cached_response.get('sources', []),
            'remainingQueries': tier_info.get('freeTrialQueriesRemaining', 0),
            'tier': tier_info['tier']
        })
    
    # Self-RAG: Retrieve, Generate, Critique, Refine
    try:
        result = self_rag_pipeline(query, user_id)
        
        # Cache if query is popular (asked by 3+ users)
        increment_query_count(cache_key)
        query_count = get_query_count(cache_key)
        if query_count >= 3:
            cache_response(cache_key, result)
        
        return format_response(200, {
            'response': result['response'],
            'cached': False,
            'sources': result['sources'],
            'confidence': result['confidence'],
            'selfRagIterations': result['iterations'],
            'remainingQueries': tier_info.get('freeTrialQueriesRemaining', 0),
            'tier': tier_info['tier']
        })
    
    except Exception as e:
        logger.error("Error in Self-RAG pipeline: %s", e)
        return format_response(500, {'error': 'Failed to generate response'})


def self_rag_pipeline(query: str, user_id: str, max_iterations: int = 2) -> Dict[str, Any]:
    """
    Self-RAG pipeline for response validation
    
    Steps:
    1. Retrieve relevant parks from vector DB
    2. Get weather context
    3. Generate response with Claude
    4. Self-critique: Check relevance and accuracy
    5. If critique score < threshold, retrieve more context and retry
    6. Return best response
    
    This ensures responses are grounded in actual park data and weather conditions
    """
    claude_api_key = get_secret(CLAUDE_API_SECRET_ARN)
    weather_api_key = get_secret(WEATHER_API_SECRET_ARN)
    
    best_response = None
    best_confidence = 0.0
    iterations = 0
    
    for iteration in range(max_iterations):
        iterations += 1
        
        # Step 1: Retrieve relevant context
        parks = retrieve_relevant_parks(query, limit=5 + (iteration * 3))  # Expand search on retry
        weather_data = get_weather_context(parks)
        
        # Step 2: Generate response
        response = generate_response_with_claude(
            query=query,
            parks=parks,
            weather=weather_data,
            api_key=claude_api_key
        )
        
        # Step 3: Self-critique
        critique = self_critique_response(
            query=query,
            response=response,
            parks=parks,
            api_key=claude_api_key
        )
        
        logger.info(
            "Self-RAG iteration %d: confidence=%.2f, relevance=%s, accuracy=%s",
            iteration + 1,
            critique['confidence'],
            critique['is_relevant'],
            critique['is_accurate']
        )
        
        # Track best response
        if critique['confidence'] > best_confidence:
            best_confidence = critique['confidence']
            best_response = {
                'response': response,
                'sources': [{'parkId': p['id'], 'name': p['name']} for p in parks],
                'confidence': critique['confidence'],
                'iterations': iterations
            }
        
        # If confidence is high enough, return immediately
        if critique['confidence'] >= 0.85 and critique['is_relevant'] and critique['is_accurate']:
            logger.info("Self-RAG converged after %d iterations", iterations)
            return best_response
    
    # Return best response after max iterations
    logger.info("Self-RAG completed %d iterations, best confidence: %.2f", iterations, best_confidence)
    return best_response or {
        'response': "I'm having trouble finding relevant information. Could you rephrase your question?",
        'sources': [],
        'confidence': 0.0,
        'iterations': iterations
    }


def self_critique_response(
    query: str,
    response: str,
    parks: List[Dict],
    api_key: str
) -> Dict[str, Any]:
    """
    Self-critique: Validate response relevance and accuracy
    
    Uses Claude to evaluate:
    1. Is the response relevant to the query?
    2. Is the response grounded in the provided park data?
    3. Are there any hallucinations or unsupported claims?
    
    Returns confidence score (0.0-1.0)
    """
    critique_prompt = f"""You are a critical evaluator. Assess this AI response for a park recommendation query.

Query: {query}

Response: {response}

Available Park Data: {json.dumps([{'name': p['name'], 'amenities': p.get('amenities', [])} for p in parks[:3]], indent=2)}

Evaluate:
1. Is the response directly relevant to the query? (yes/no)
2. Is the response grounded in the provided park data? (yes/no)
3. Are there any unsupported claims or hallucinations? (yes/no)
4. Overall confidence score (0.0-1.0)

Respond in JSON format:
{{
  "is_relevant": true/false,
  "is_accurate": true/false,
  "has_hallucinations": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""
    
    try:
        # Call Claude for critique (using fast model for speed)
        critique_response = call_claude_api(
            prompt=critique_prompt,
            api_key=api_key,
            model="claude-3-haiku-20240307",  # Fastest model for critique
            max_tokens=300
        )
        
        critique = json.loads(critique_response)
        return critique
    
    except Exception as e:
        logger.error("Self-critique failed: %s", e)
        # Default to medium confidence on critique failure
        return {
            'is_relevant': True,
            'is_accurate': True,
            'has_hallucinations': False,
            'confidence': 0.7,
            'reasoning': 'Critique failed, assuming reasonable quality'
        }


def generate_response_with_claude(
    query: str,
    parks: List[Dict],
    weather: Dict,
    api_key: str
) -> str:
    """Generate response using Claude with park and weather context"""
    prompt = f"""You are a helpful park recommendation assistant for Fairfax County, Virginia.

User Query: {query}

Relevant Parks:
{json.dumps(parks, indent=2)}

Current Weather:
{json.dumps(weather, indent=2)}

Provide a helpful, accurate response based ONLY on the provided park data and weather information.
Be specific about park names, amenities, and weather conditions.
If the weather is relevant to the recommendation, mention it.
Keep the response concise (2-3 sentences)."""
    
    response = call_claude_api(
        prompt=prompt,
        api_key=api_key,
        model="claude-3-sonnet-20240229",
        max_tokens=500
    )
    
    return response


def call_claude_api(prompt: str, api_key: str, model: str, max_tokens: int) -> str:
    """
    Call Claude API
    TODO: Implement actual API call in Phase 2
    For now, return mock response
    """
    # Mock response for Sprint 0
    return f"Mock response for: {prompt[:50]}..."


def retrieve_relevant_parks(query: str, limit: int = 5) -> List[Dict]:
    """
    Retrieve relevant parks from Aurora pgvector
    TODO: Implement actual vector search in Phase 2
    """
    # Mock parks for Sprint 0
    return [
        {'id': 'park1', 'name': 'Clemyjontri Park', 'amenities': ['playground', 'accessible']},
        {'id': 'park2', 'name': 'Lake Fairfax Park', 'amenities': ['lake', 'trails']},
    ]


def get_weather_context(parks: List[Dict]) -> Dict:
    """
    Get weather data for park locations
    TODO: Implement actual weather API call in Phase 2
    """
    # Mock weather for Sprint 0
    return {
        'temperature': 72,
        'condition': 'sunny',
        'humidity': 45
    }


def get_user_tier(user_id: str) -> Dict[str, Any]:
    """Get user tier from Auth Lambda logic"""
    # Import from auth handler
    # For now, simplified version
    try:
        db_result = users_table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': 'PROFILE'}
        )
        if 'Item' not in db_result:
            return {'tier': 'error', 'error': 'User not found'}
        
        user = db_result['Item']
        is_premium = user.get('isPremium', False)
        
        if is_premium:
            return {'tier': 'premium', 'isPremium': True}
        
        free_trial_used = user.get('freeTrialQueriesUsed', 0)
        if free_trial_used >= 3:
            return {'tier': 'paywall', 'freeTrialQueriesUsed': free_trial_used}
        
        return {
            'tier': 'free',
            'freeTrialQueriesUsed': free_trial_used,
            'freeTrialQueriesRemaining': 3 - free_trial_used
        }
    except Exception as e:
        logger.error("Error getting user tier: %s", e)
        return {'tier': 'error', 'error': str(e)}


def increment_free_trial_usage(user_id: str) -> Dict[str, Any]:
    """Atomically increment free trial usage"""
    try:
        db_result = users_table.update_item(
            Key={'PK': f'USER#{user_id}', 'SK': 'PROFILE'},
            UpdateExpression='SET freeTrialQueriesUsed = if_not_exists(freeTrialQueriesUsed, :zero) + :one',
            ConditionExpression='attribute_not_exists(freeTrialQueriesUsed) OR freeTrialQueriesUsed < :limit',
            ExpressionAttributeValues={':zero': 0, ':one': 1, ':limit': 3},
            ReturnValues='UPDATED_NEW'
        )
        new_count = int(db_result['Attributes']['freeTrialQueriesUsed'])
        return {
            'success': True,
            'freeTrialQueriesUsed': new_count,
            'freeTrialQueriesRemaining': max(0, 3 - new_count),
            'tier': 'free' if new_count < 3 else 'paywall'
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {'success': False, 'error': 'Free trial exhausted', 'tier': 'paywall'}
        return {'success': False, 'error': str(e)}


def normalize_query(query: str) -> str:
    """Normalize query for caching"""
    return query.lower().strip()


def get_secret(secret_arn: str) -> str:
    """Get secret from Secrets Manager with caching"""
    if secret_arn in _secrets_cache:
        return _secrets_cache[secret_arn]
    
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_arn)
        secret = response['SecretString']
        _secrets_cache[secret_arn] = secret
        return secret
    except Exception as e:
        logger.error("Failed to get secret %s: %s", secret_arn, e)
        raise


def get_from_cache(key: str) -> Optional[Dict]:
    """Get from ElastiCache Redis - TODO: Implement in Phase 2"""
    return None


def cache_response(key: str, value: Dict) -> None:
    """Cache response in ElastiCache Redis - TODO: Implement in Phase 2"""
    pass


def increment_query_count(key: str) -> None:
    """Increment query count - TODO: Implement in Phase 2"""
    pass


def get_query_count(key: str) -> int:
    """Get query count - TODO: Implement in Phase 2"""
    return 0


def format_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Format API Gateway response"""
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
