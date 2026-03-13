"""
Pydantic models for request validation
Prevents PII, validates email format, enforces password complexity
Requirements: 8.1, 9.5
"""
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, Field


class RegisterRequest(BaseModel):
    """
    User registration request validation
    
    Requirements:
    - Valid email format
    - Password: min 8 chars, uppercase, lowercase, numbers
    - Prevent PII in name fields
    """
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=100)
    
    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """
        Enforce password complexity requirements
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        return v
    
    @field_validator('name')
    @classmethod
    def prevent_pii_in_name(cls, v: Optional[str]) -> Optional[str]:
        """
        Prevent PII in name field
        - No email addresses
        - No phone numbers
        - No street addresses (basic check)
        """
        if v is None:
            return v
        
        # Check for email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', v):
            raise ValueError('Name cannot contain email addresses')
        
        # Check for phone numbers (US and international formats)
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # (123) 456-7890
            r'\b\+\d{1,3}\s*\d{1,14}\b',  # +1 1234567890
        ]
        for pattern in phone_patterns:
            if re.search(pattern, v):
                raise ValueError('Name cannot contain phone numbers')
        
        # Check for street addresses (basic patterns)
        address_patterns = [
            r'\b\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b',
        ]
        for pattern in address_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Name cannot contain street addresses')
        
        # Check for special characters that might indicate injection attempts
        if re.search(r'[<>{}[\]\\]', v):
            raise ValueError('Name contains invalid characters')
        
        return v
    
    @field_validator('email')
    @classmethod
    def prevent_special_characters_in_email(cls, v: str) -> str:
        """
        Additional email validation beyond EmailStr
        Prevent special characters that might cause issues
        """
        # EmailStr already validates format, but add extra checks
        local_part = v.split('@')[0]
        
        # Prevent consecutive dots
        if '..' in local_part:
            raise ValueError('Email cannot contain consecutive dots')
        
        # Prevent leading/trailing dots in local part
        if local_part.startswith('.') or local_part.endswith('.'):
            raise ValueError('Email local part cannot start or end with a dot')
        
        return v.lower()  # Normalize to lowercase


class LoginRequest(BaseModel):
    """User login request validation"""
    email: EmailStr
    password: str
    apple_token: Optional[str] = None  # For Sign in with Apple
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower()


class RefreshTokenRequest(BaseModel):
    """Token refresh request validation"""
    refresh_token: str = Field(min_length=1)


class ValidateSubscriptionRequest(BaseModel):
    """StoreKit subscription validation request"""
    user_id: str = Field(min_length=1)
    receipt_data: str = Field(min_length=1)
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id_format(cls, v: str) -> str:
        """Ensure user_id doesn't contain injection attempts"""
        if re.search(r'[<>{}[\]\\;]', v):
            raise ValueError('Invalid user_id format')
        return v


def validate_request(model_class: type[BaseModel], body: str) -> tuple[Optional[BaseModel], Optional[dict]]:
    """
    Validate request body against Pydantic model
    
    Returns:
        (validated_model, None) on success
        (None, error_dict) on validation failure
    """
    try:
        import json
        data = json.loads(body)
        validated = model_class(**data)
        return validated, None
    except json.JSONDecodeError:
        return None, {'error': 'Invalid JSON', 'details': 'Request body must be valid JSON'}
    except ValueError as e:
        # Pydantic validation error
        return None, {'error': 'Validation failed', 'details': str(e)}
    except Exception as e:
        return None, {'error': 'Validation failed', 'details': 'Invalid request format'}
