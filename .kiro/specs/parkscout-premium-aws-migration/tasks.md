# Implementation Plan: ParkScout Premium & AWS Migration

## Overview

This implementation plan transforms ParkScout from a monolithic FastAPI application into a scalable, cost-effective AWS serverless architecture with a freemium business model. The plan prioritizes the Photo Safety Pipeline (automated face blurring) as the "Secret Sauce" differentiator for mom-centric safety, implements critical AWS best practices for production readiness, and establishes a foundation for sustainable growth.

**Key Technical Improvements**:
- **RDS Proxy**: Prevents connection exhaustion when 50+ Lambdas spin up simultaneously
- **S3 Object Lambda**: Blurs photos on-the-fly, eliminating duplicate storage and URL exposure risks
- **DynamoDB Write Sharding**: Prevents hot partitions on popular parks with 1,000+ reviews
- **Provisioned Concurrency**: Eliminates cold start latency for AI Chat Lambda

**Implementation Language**: Python 3.11 for all Lambda functions (with Go optimization option for Parks Lambda)

---

## Quick Start - Sprint 0 (Phase 1 Foundation)

**Immediate Priority**: Set up the Users Table in DynamoDB and the Auth Lambda to establish authentication foundation.

### Sprint 0 Tasks

- [x] 0.1 Create SAM/CDK template for Python 3.11 Lambda infrastructure
  - Define Lambda function configurations
  - Set up API Gateway with CORS
  - Configure IAM roles with least privilege
  - _Requirements: 9.1, 11.1_

- [x] 0.2 Implement getUserTier logic in Auth Lambda
  - Check isPremium flag in DynamoDB
  - For free users, check freeTrialQueriesUsed (0-3)
  - Return tier status: 'free', 'premium', or 'paywall'
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 0.3 Use Pydantic for request validation
  - Validate email format and prevent special characters
  - Prevent PII in registration fields
  - Validate password complexity requirements
  - _Requirements: 8.1, 9.5_

- [ ] 0.4 Set up DynamoDB Users Table with GSI
  - Create table with PK: USER#<userId>, SK: PROFILE
  - Add GSI for email lookups (GSI1PK: EMAIL#<email>)
  - Include isPremium, freeTrialQueriesUsed fields
  - _Requirements: 13.1, 13.2_


- [x] 0.5 Configure AWS Secrets Manager for Claude API Key
  - Store Claude API key in Secrets Manager
  - Grant Lambda IAM role access to secret
  - Implement secret retrieval in Lambda init
  - **Constraint**: No hardcoded credentials in code
  - _Requirements: 9.1_

**Why Start Here**: This establishes the authentication foundation and tiered access model that everything else depends on. The getUserTier logic is the gatekeeper for all premium features.

---

## Phase 1: Core Infrastructure & Authentication

### Task 1: AWS Cognito User Pool Setup

- [ ] 1.1 Create Cognito User Pool with password policies
  - Configure password requirements: min 8 chars, uppercase, lowercase, numbers
  - Enable MFA support for future use
  - Set up email verification workflow
  - _Requirements: 9.1, 9.2, 9.5_

- [ ] 1.2 Configure Sign in with Apple as identity provider
  - Register app with Apple Developer Portal
  - Configure Cognito to accept Apple ID tokens
  - Set up attribute mapping for email and name
  - _Requirements: 4.1, 4.3, 4.4_

- [ ] 1.3 Implement JWT token validation middleware
  - Validate Cognito JWT signatures
  - Check token expiration
  - Extract user claims (userId, email, tier)
  - _Requirements: 9.3_

- [ ]* 1.4 Write property test for token validation
  - **Property 15: JWT Token Validation**
  - **Validates: Requirements 9.3**


### Task 2: iOS Authentication Implementation

- [ ] 2.1 Implement Sign in with Apple flow in SwiftUI
  - Add AuthenticationServices framework
  - Create Apple Sign In button
  - Handle authorization response
  - _Requirements: 4.1, 4.2, 4.5_

- [ ] 2.2 Implement TokenManager with iOS Keychain
  - Store access and refresh tokens securely
  - Implement automatic token refresh logic
  - Handle token expiration gracefully
  - _Requirements: 7.1, 7.2, 7.4_

- [ ] 2.3 Implement BiometricAuthManager
  - Check biometric availability (Face ID/Touch ID)
  - Prompt for biometric authentication on app launch
  - Fall back to password after 3 failed attempts
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ]* 2.4 Write property test for automatic token refresh
  - **Property 12: Automatic Token Refresh**
  - **Validates: Requirements 7.2**

- [ ]* 2.5 Write unit tests for biometric auth edge cases
  - Test hardware unavailable scenario
  - Test 3 failed attempts lockout
  - Test user cancellation handling
  - _Requirements: 5.4_


### Task 3: DynamoDB Schema Implementation

- [ ] 3.1 Create Users Table with optimized schema
  - PK: USER#<userId>, SK: PROFILE
  - Attributes: email, cognitoId, rank, isPremium, premiumExpiresAt
  - Add freeTrialQueriesUsed, freeTrialExhaustedAt fields
  - Add appleSubscriptionId for webhook correlation
  - _Requirements: 13.1, 1.1_

- [ ] 3.2 Create Reviews Table with write sharding strategy
  - PK: PARK#<parkId>#<shardId>, SK: REVIEW#<reviewId>
  - **Sharding Strategy**: Use shardId 0-9 calculated from reviewId hash
  - **Rationale**: Popular parks (e.g., Clemyjontri) could get 1,000+ reviews in a weekend, creating hot partitions where one physical DynamoDB slice handles all writes
  - Ensure Sort Key (REVIEW#<reviewId>) uses UUID for entropy
  - Add GSI1: PK=USER#<userId>, SK=REVIEW#<timestamp> for user's reviews
  - **Query Pattern**: When retrieving park reviews, query across all 10 shards and merge results
  - _Requirements: 13.1, 13.2_

- [ ] 3.3 Create Badges Table
  - PK: USER#<userId>, SK: BADGE#<badgeId>#<parkId>
  - Add GSI1: PK=PARK#<parkId>, SK=BADGE#<amenityType>
  - _Requirements: 13.1_

- [ ] 3.4 Create Amenity Verifications Table
  - PK: PARK#<parkId>, SK: AMENITY#<amenityType>
  - Store verification array with userId, verified, timestamp
  - Track verifiedCount and masterBadgeAwarded flag
  - _Requirements: 15.2, 15.3_

- [ ]* 3.5 Write property test for optimistic locking
  - **Property 20: Optimistic Locking for Reviews**
  - **Validates: Requirements 13.5**


### Task 4: StoreKit 2 Integration

- [ ] 4.1 Configure App Store Connect products
  - Create subscription product IDs
  - Set up pricing tiers
  - Configure subscription groups
  - _Requirements: 6.1_

- [ ] 4.2 Implement SubscriptionManager in iOS
  - Handle purchase flow with StoreKit 2
  - Implement receipt verification
  - Handle subscription restoration
  - Display subscription status in settings
  - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [ ] 4.3 Create subscription validation endpoint in Auth Lambda
  - Validate StoreKit receipts with Apple servers
  - Update isPremium flag in DynamoDB
  - Set premiumExpiresAt timestamp
  - _Requirements: 6.3_

- [ ]* 4.4 Write property test for premium tier update
  - **Property 3: Premium Tier Update Timeliness**
  - **Validates: Requirements 1.6**

---

## Phase 2: Photo Safety Pipeline (CRITICAL PRIORITY - Secret Sauce)

**Strategic Priority**: This is the differentiator that judges will love. Even if other features are incomplete, a fully functional automated safety pipeline for kids' privacy is a winning feature on its own.

### Task 5: S3 Bucket Configuration with Object Lambda

- [ ] 5.1 Create S3 buckets with security policies
  - Create private bucket for original photos (secure storage)
  - Configure bucket policies: no public access
  - Enable versioning for audit trail
  - Set up lifecycle policies: delete originals after 90 days
  - _Requirements: 12.1, 16.4_


- [ ] 5.2 Configure S3 Object Lambda for on-the-fly blurring
  - **Pro Builder Move**: Replace "Upload → Trigger → Process → Save New File" with S3 Object Lambda
  - **Benefits**: 
    - Reduced storage costs (store only original)
    - No risk of unblurred URL exposure via direct URLs
    - Simpler architecture (no duplicate files)
  - Create S3 Object Lambda Access Point
  - Configure Lambda function to blur images on GET requests
  - Set up IAM policies for Object Lambda access
  - _Requirements: 16.4_

- [ ] 5.3 Configure CloudFront with S3 Object Lambda origin
  - Create CloudFront distribution
  - Set S3 Object Lambda Access Point as origin
  - Configure 30-day cache TTL
  - Enable WebP format with JPEG fallback
  - _Requirements: 12.2, 12.4, 12.5_

### Task 6: AWS Rekognition Integration

- [ ] 6.1 Implement face detection with Rekognition
  - Call DetectFaces API with uploaded image
  - Extract face bounding box coordinates
  - Handle multiple faces in single image
  - _Requirements: 16.4_

- [ ] 6.2 Implement content moderation with Rekognition
  - Call DetectModerationLabels API
  - Define inappropriate content thresholds
  - Reject flagged images before storage
  - _Requirements: 16.5, 16.7_

- [ ]* 6.3 Write unit tests for Rekognition integration
  - Test face detection with multiple faces
  - Test content moderation thresholds
  - Test API error handling
  - _Requirements: 16.4, 16.5_


### Task 7: Face Blurring Implementation (CRITICAL - Secret Sauce)

- [ ] 7.1 Implement Gaussian blur processing with Pillow
  - Load image from S3 in Object Lambda function
  - Convert Rekognition percentages to pixel coordinates
  - Add 20% padding around face bounding boxes
  - Apply Gaussian blur with radius=20 for strong anonymization
  - Return blurred image in response
  - _Requirements: 16.4_

- [ ] 7.2 Handle edge cases in face blurring
  - Partially visible faces at image edges
  - Multiple faces at different scales
  - Faces with accessories (sunglasses, hats)
  - Low-light or blurry photos
  - _Requirements: 16.4_

- [ ]* 7.3 Write property test for face blurring (CRITICAL)
  - **Property 24: Face Detection and Blurring**
  - **Validates: Requirements 16.4**
  - Generate random images with 0-10 faces
  - Verify all detected faces are blurred
  - Run 100+ iterations with varying image sizes, positions, lighting

- [ ]* 7.4 Write visual regression tests
  - Use test images with known faces
  - Verify faces are not recognizable after blurring
  - Compare blur radius consistency across images
  - Test edge cases: faces at borders, multiple faces, accessories
  - _Requirements: 16.4_

- [ ]* 7.5 Write integration tests for full pipeline
  - Test: Upload → S3 → Object Lambda → Rekognition → Blur → Response
  - Use real Rekognition API (not mocked)
  - Verify CloudFront URL returns blurred image
  - Test with concurrent requests (10+ simultaneous)
  - _Requirements: 16.4_


### Task 8: Photo Upload Flow

- [ ] 8.1 Implement presigned URL generation in Photos Lambda
  - Generate presigned S3 PUT URLs with 5-minute expiration
  - Include content-type validation
  - Return photoId and uploadUrl to client
  - _Requirements: 12.3, 16.3_

- [ ] 8.2 Implement iOS photo upload with compression
  - Compress images to <2MB before upload
  - Use presigned URL for direct S3 upload
  - Display upload progress
  - Handle upload failures with retry
  - _Requirements: 16.1, 16.2_

- [ ]* 8.3 Write property test for presigned URL generation
  - **Property 19: Presigned URL Generation**
  - **Validates: Requirements 12.3**

- [ ]* 8.4 Write property test for image compression
  - **Property 23: Image Compression**
  - **Validates: Requirements 16.2**

### Task 9: Google Places Photo Integration

- [ ] 9.1 Implement Google Places API client
  - Fetch park photos from Places API
  - Handle API rate limits and errors
  - Extract photo references and attributions
  - _Requirements: 16a.1_

- [ ] 9.2 Implement photo caching strategy
  - Cache Google Places photos in S3
  - Set 30-day refresh cycle
  - Serve cached photos through CloudFront
  - _Requirements: 16a.3, 16a.4_

- [ ]* 9.3 Write property test for photo cache strategy
  - **Property 26: Photo Cache Strategy**
  - **Validates: Requirements 16a.3**

---

## Phase 3: Aurora Serverless v2 with pgvector & RDS Proxy


### Task 10: Aurora Serverless v2 Setup with RDS Proxy

- [ ] 10.1 Create Aurora Serverless v2 cluster with pgvector
  - Configure PostgreSQL 15+ with pgvector extension
  - Set minimum capacity to 0.5 ACU (scales to zero)
  - Configure auto-pause after 5 minutes of inactivity
  - Enable encryption at rest with AWS KMS
  - _Requirements: 10.1_

- [ ] 10.2 Create database schema with vector indices
  - Create parks table with vector(1536) column for embeddings
  - Create HNSW index for vector similarity search
  - Create GiST index for location-based queries
  - Create GIN indices for amenity filtering
  - _Requirements: 10.1, 10.2_

- [ ] 10.3 Configure RDS Proxy for connection management (CRITICAL)
  - **Problem**: Standard connection pools fail when 50+ Lambdas spin up simultaneously and exhaust Aurora connection limits (typically 100-200 connections)
  - **Solution**: RDS Proxy sits between Lambdas and Aurora, managing a persistent connection pool
  - **Benefits**:
    - Handles connection pooling even when Lambdas spin down
    - Faster failover than direct connections
    - Reduces connection overhead and latency
  - Create RDS Proxy with target group pointing to Aurora cluster
  - Configure connection pooling settings:
    - Max connections per Lambda: 2
    - Connection borrow timeout: 30 seconds
    - Idle client timeout: 1800 seconds
  - Enable IAM authentication for secure access
  - Update Lambda functions to connect via RDS Proxy endpoint (not direct Aurora endpoint)
  - _Requirements: 10.5, 11.5_


- [ ]* 10.4 Write property test for vector search performance
  - **Property 17: Vector Search Performance**
  - **Validates: Requirements 10.5**

### Task 11: Data Migration from ChromaDB

- [ ] 11.1 Export existing ChromaDB embeddings
  - Extract all park embeddings and metadata
  - Validate embedding dimensions (1536)
  - Create migration manifest with checksums
  - _Requirements: 10.3_

- [ ] 11.2 Import embeddings to Aurora pgvector
  - Batch insert embeddings into parks table
  - Verify data integrity with checksums
  - Build HNSW indices after import
  - _Requirements: 10.3_

- [ ]* 11.3 Write property test for data migration integrity
  - **Property 40: Data Migration Integrity**
  - **Validates: Requirements 25.1, 25.2**

### Task 12: Vector Search Implementation

- [ ] 12.1 Implement semantic search with pgvector
  - Query using cosine similarity (1 - embedding <=> query_vector)
  - Apply filters for amenities, rating, distance
  - Return top-k results with similarity scores
  - _Requirements: 10.2_

- [ ] 12.2 Implement hybrid search (text + vector)
  - Combine full-text search with vector similarity
  - Weight and merge results
  - Apply ranking algorithm
  - _Requirements: 10.2_

- [ ]* 12.3 Write property test for vector search storage
  - **Property 16: Vector Search Storage**
  - **Validates: Requirements 10.1, 10.2**


---

## Phase 4: Lambda Functions & API Gateway

### Task 13: API Gateway Configuration

- [ ] 13.1 Create API Gateway REST API
  - Define resource paths and methods
  - Configure CORS for iOS app
  - Set up request/response models
  - _Requirements: 14.1_

- [ ] 13.2 Implement rate limiting with usage plans
  - Create usage plan for free tier: 100 req/min
  - Create usage plan for premium tier: 500 req/min
  - Associate API keys with usage plans
  - Configure throttling and quota limits
  - _Requirements: 14.2, 14.3, 14.4_

- [ ] 13.3 Configure API key validation
  - Require API keys for all requests
  - Implement key rotation strategy
  - Set up key validation middleware
  - _Requirements: 14.5_

- [ ]* 13.4 Write property test for rate limiting enforcement
  - **Property 4: Rate Limiting Enforcement**
  - **Validates: Requirements 2.1, 2.2, 14.2, 14.3**

- [ ]* 13.5 Write property test for rate limit reset
  - **Property 5: Rate Limit Reset**
  - **Validates: Requirements 2.3**

### Task 14: Auth Lambda Implementation

- [ ] 14.1 Implement user registration endpoint
  - Validate input with Pydantic
  - Create Cognito user
  - Create DynamoDB user profile
  - Return JWT tokens
  - _Requirements: 9.1, 9.2_


- [ ] 14.2 Implement login endpoint with Apple Sign In support
  - Accept email/password or Apple ID token
  - Validate credentials with Cognito
  - Link Apple accounts to existing users via email GSI
  - Return JWT tokens
  - _Requirements: 4.3, 9.1_

- [ ] 14.3 Implement token refresh endpoint
  - Validate refresh token
  - Issue new access token
  - Handle expired refresh tokens
  - _Requirements: 7.2_

- [ ]* 14.4 Write property test for Apple token validation
  - **Property 10: Apple Token Validation**
  - **Validates: Requirements 4.3**

### Task 15: Parks Lambda Implementation (Optimized)

- [ ] 15.1 Implement park search endpoint
  - Query Aurora pgvector via RDS Proxy for semantic search
  - Apply filters (amenities, distance, rating)
  - Return paginated results
  - Target: <100ms execution time
  - _Requirements: 10.2, 18.1_

- [ ] 15.2 Implement park details endpoint
  - Fetch park data from Aurora via RDS Proxy
  - Include verified amenities and badges
  - Fetch weather data from Weather API
  - Cache results in ElastiCache
  - _Requirements: 18.1, 23.1_

- [ ] 15.3 Optimize Parks Lambda for performance
  - **Option A**: Use lightweight Python with minimal dependencies
  - **Option B**: Rewrite in Go for <200ms cold starts and <50ms warm execution
  - Minimize deployment package size (<10MB)
  - Reuse RDS Proxy connections across invocations
  - _Requirements: 11.4, 11.5_


- [ ]* 15.4 Write property test for Lambda response time
  - **Property 18: Lambda Response Time**
  - **Validates: Requirements 11.4**

### Task 16: AI Chat Lambda with Provisioned Concurrency

- [ ] 16.1 Implement LLM orchestration logic
  - Build context from user query, park data, weather
  - Call Claude API with structured prompts
  - Parse and format LLM responses
  - _Requirements: 1.2, 23.6_

- [ ] 16.2 Implement query caching with ElastiCache
  - Normalize queries (lowercase, remove punctuation, stem)
  - Check cache before calling LLM
  - Store responses for queries asked by 3+ users
  - Set 7-day TTL on cached entries
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 16.3 Implement RAG retrieval from Aurora
  - Generate query embedding
  - Retrieve relevant parks via RDS Proxy
  - Include park data in LLM context
  - _Requirements: 10.2_

- [ ] 16.4 Configure Provisioned Concurrency
  - **Problem**: Claude API (2-5s) + Lambda cold start (1-3s) = 3-8s total latency = Broken UX
  - **Solution**: Provisioned Concurrency keeps 2 instances warm
  - Set provisioned concurrent executions to 2
  - Create alias pointing to latest version
  - Route API Gateway to alias (not $LATEST)
  - **Cost**: ~$22/month for 2 warm instances (acceptable for UX improvement)
  - _Requirements: 11.4_


- [ ] 16.5 Implement free trial query tracking
  - Check freeTrialQueriesUsed for free users
  - Increment counter on each query
  - Return remaining queries in response
  - Show paywall when exhausted (3 queries)
  - _Requirements: 1.1_

- [ ]* 16.6 Write property test for AI chat access control
  - **Property 2: AI Chat Access Control**
  - **Validates: Requirements 1.1, 1.2**

- [ ]* 16.7 Write property test for free trial query tracking
  - **Property 2a: Free Trial Query Tracking**
  - **Validates: Requirements 1.1**

- [ ]* 16.8 Write property test for free trial exhaustion
  - **Property 2b: Free Trial Exhaustion**
  - **Validates: Requirements 1.1**

- [ ]* 16.9 Write property test for query cache hit
  - **Property 6: Query Cache Hit**
  - **Validates: Requirements 3.1**

- [ ]* 16.10 Write property test for query cache threshold
  - **Property 7: Query Cache Threshold**
  - **Validates: Requirements 3.2**

- [ ]* 16.11 Write property test for query cache expiration
  - **Property 8: Query Cache Expiration**
  - **Validates: Requirements 3.3**

- [ ]* 16.12 Write property test for query normalization
  - **Property 9: Query Normalization for Caching**
  - **Validates: Requirements 3.4**

- [ ]* 16.13 Write property test for weather data in LLM context
  - **Property 37: Weather Data in LLM Context**
  - **Validates: Requirements 23.6**

- [ ]* 16.14 Write property test for weather-aware recommendations
  - **Property 38: Weather-Aware Recommendations**
  - **Validates: Requirements 23.7**


### Task 17: Webhook Lambda for App Store Notifications

- [ ] 17.1 Implement webhook endpoint for App Store Server Notifications V2
  - Accept POST requests with signed payloads
  - Validate Apple's JWT signature
  - Decode notification payload
  - _Requirements: 6.3, 6.4_

- [ ] 17.2 Implement subscription lifecycle event handlers
  - Handle DID_CHANGE_RENEWAL_STATUS (cancellation)
  - Handle DID_RENEW (renewal)
  - Handle EXPIRED (expiration)
  - Handle REFUND (refund)
  - Handle REVOKE (revocation)
  - Update isPremium flag in DynamoDB within 5 seconds
  - _Requirements: 6.4_

- [ ]* 17.3 Write property test for webhook subscription sync
  - **Property 3a: Webhook Subscription Sync**
  - **Validates: Requirements 1.6, 6.3**

- [ ]* 17.4 Write property test for subscription cancellation sync
  - **Property 3b: Subscription Cancellation Sync**
  - **Validates: Requirements 6.4**

---

## Phase 5: Tiered Access & Content Filtering

### Task 18: Tier Validation Middleware

- [ ] 18.1 Implement TierValidator middleware
  - Check user tier from DynamoDB
  - Validate feature access based on tier
  - Return 403 for unauthorized access
  - _Requirements: 1.7_


- [ ] 18.2 Implement content filtering for free users
  - Filter out review text for free users
  - Show only amenity tags and badges
  - Include upgrade prompts
  - _Requirements: 1.4_

- [ ] 18.3 Implement full content access for premium users
  - Return complete review text
  - Include photos and amenity tags
  - Show all park details
  - _Requirements: 1.5_

- [ ]* 18.4 Write property test for tiered content access
  - **Property 1: Tiered Content Access**
  - **Validates: Requirements 1.4, 1.5**

### Task 19: PII Detection and Protection

- [ ] 19.1 Implement PII detection regex patterns
  - Email addresses: RFC 5322 compliant regex
  - Phone numbers: US and international formats
  - Street addresses: common patterns
  - _Requirements: 8.1_

- [ ] 19.2 Implement PII scanning in review submission
  - Scan review text before storage
  - Redact or reject reviews with PII
  - Return explanation to user
  - Log PII detection events
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 19.3 Implement client-side PII warning
  - Detect potential PII in iOS app
  - Warn user before submission
  - Highlight detected PII
  - _Requirements: 8.4_

- [ ]* 19.4 Write property test for PII detection and rejection
  - **Property 13: PII Detection and Rejection**
  - **Validates: Requirements 8.1, 8.2**


---

## Phase 6: Merit Badge System & Gamification

### Task 20: Badge Engine Implementation

- [ ] 20.1 Define badge types and metadata
  - The Golden Throne (bathrooms)
  - The Fortress (fenced playgrounds)
  - The Solar Shield (shade)
  - The Caffeine Compass (nearby coffee)
  - The Smooth Roller (stroller paths)
  - _Requirements: 15.9_

- [ ] 20.2 Implement amenity verification logic
  - Accept verification from users
  - Track verification count per amenity
  - Award first verifier badge immediately
  - Award master badge when 3+ users verify
  - _Requirements: 15.2, 15.3_

- [ ] 20.3 Implement badge awarding logic
  - Check verification thresholds
  - Create badge award records in DynamoDB
  - Return badge data to client
  - _Requirements: 15.2, 15.3_

- [ ]* 20.4 Write property test for first verifier badge award
  - **Property 21: First Verifier Badge Award**
  - **Validates: Requirements 15.2**

- [ ]* 20.5 Write property test for master badge award
  - **Property 22: Master Badge Award**
  - **Validates: Requirements 15.3**

### Task 21: iOS Badge UI Implementation

- [ ] 21.1 Create badge celebration animation
  - Full-screen animation with badge icon
  - Congratulatory sound effect
  - Confetti or particle effects
  - _Requirements: 15.4, 15.5_


- [ ] 21.2 Implement badge display on park profiles
  - Show earned badges in visual row (Scout sash style)
  - Display greyed-out badges for unverified amenities
  - Add tap-to-verify prompts
  - _Requirements: 15.6, 15.7_

- [ ] 21.3 Implement social sharing for badges
  - Generate shareable badge images
  - Support sharing to Messages, Instagram, Facebook, Twitter
  - Track share events
  - _Requirements: 15.8, 24.4_

### Task 22: Scout Rank Progression

- [ ] 22.1 Implement rank calculation logic
  - Tenderfoot: 0 contributions (default)
  - Trailblazer: 5 reviews
  - Pathfinder: 10 amenity verifications
  - Park Legend: 50 total contributions
  - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

- [ ] 22.2 Implement contribution tracking
  - Track reviews, amenity verifications, photos, visits, shares
  - Update contribution count on each action
  - Check for rank-up after each contribution
  - _Requirements: 20.1_

- [ ] 22.3 Implement rank-up celebration
  - Display rank-up animation in iOS app
  - Show new rank badge and benefits
  - _Requirements: 20.6_

- [ ] 22.4 Implement rank-based weighting in recommendations
  - Apply weight multipliers: Tenderfoot (1.0), Trailblazer (1.5), Pathfinder (2.0), Park Legend (3.0)
  - Weight contributions in recommendation algorithm
  - _Requirements: 20.9_


- [ ]* 22.5 Write property test for initial rank assignment
  - **Property 32: Initial Rank Assignment**
  - **Validates: Requirements 20.2**

- [ ]* 22.6 Write property test for rank progression thresholds
  - **Property 33: Rank Progression Thresholds**
  - **Validates: Requirements 20.3, 20.4, 20.5**

- [ ]* 22.7 Write property test for rank-based contribution weighting
  - **Property 34: Rank-Based Contribution Weighting**
  - **Validates: Requirements 20.9**

### Task 23: Scout Challenges System

- [ ] 23.1 Define challenge types and goals
  - Visit challenges: visit N parks
  - Review challenges: write N reviews
  - Share challenges: share N parks
  - Amenity challenges: verify N amenities
  - _Requirements: 19.1_

- [ ] 23.2 Implement challenge progress tracking
  - Track user actions toward challenges
  - Update progress in DynamoDB
  - Check for challenge completion
  - _Requirements: 19.2, 19.3_

- [ ] 23.3 Implement challenge completion rewards
  - Award challenge-specific badges
  - Award rank progression points
  - Display completion celebration
  - _Requirements: 19.4_

- [ ] 23.4 Implement monthly rotating challenges
  - Auto-create new challenges each month
  - Archive completed challenges
  - Send push notifications for new challenges
  - _Requirements: 19.6, 19.8_


- [ ]* 23.5 Write property test for challenge progress tracking
  - **Property 30: Challenge Progress Tracking**
  - **Validates: Requirements 19.2, 19.3**

- [ ]* 23.6 Write property test for challenge completion rewards
  - **Property 31: Challenge Completion Rewards**
  - **Validates: Requirements 19.4**

---

## Phase 7: iOS App Features

### Task 24: Offline Mode Implementation

- [ ] 24.1 Implement local cache with Core Data
  - Cache park details, locations, amenities
  - Cache user profile and badges
  - Cache recent reviews (read-only)
  - _Requirements: 17.1_

- [ ] 24.2 Implement offline indicator UI
  - Display offline banner when disconnected
  - Show "last updated" timestamps on cached data
  - Disable features requiring connectivity
  - _Requirements: 17.2_

- [ ] 24.3 Implement sync queue for offline actions
  - Queue review submissions when offline
  - Queue amenity verifications
  - Queue photo uploads
  - _Requirements: 17.3_

- [ ] 24.4 Implement sync on reconnection
  - Detect connectivity restoration
  - Sync queued actions within 30 seconds
  - Handle sync conflicts
  - _Requirements: 17.4_

- [ ]* 24.5 Write property test for local data caching
  - **Property 27: Local Data Caching**
  - **Validates: Requirements 17.1**


- [ ]* 24.6 Write property test for offline queue and sync
  - **Property 28: Offline Queue and Sync**
  - **Validates: Requirements 17.3, 17.4**

### Task 25: Personalized Recommendations

- [ ] 25.1 Implement user activity tracking
  - Track park visits, reviews, badge progress
  - Store activity patterns in DynamoDB
  - _Requirements: 18.1_

- [ ] 25.2 Implement recommendation algorithm
  - Consider park features, distance, user preferences
  - Apply rank-based weighting
  - Generate personalized suggestions
  - _Requirements: 18.2, 18.3_

- [ ] 25.3 Implement tiered recommendation display
  - Show 5 recommendations for free users
  - Show 10 recommendations with AI descriptions for premium users
  - _Requirements: 18.5, 18.6_

- [ ]* 25.4 Write property test for personalized recommendations
  - **Property 29: Personalized Recommendations**
  - **Validates: Requirements 18.2, 18.3**

### Task 26: Weather Integration

- [ ] 26.1 Implement Weather API client
  - Fetch current weather for park locations
  - Fetch 3-day forecasts
  - Cache weather data for 30 minutes
  - _Requirements: 23.1, 23.3, 23.4_

- [ ] 26.2 Implement weather UI components
  - Display current conditions and temperature
  - Show weather icons (sunny, rainy, cloudy)
  - Display 3-day forecast
  - Show severe weather warnings
  - _Requirements: 23.1, 23.2, 23.4, 23.5_


### Task 27: Social Sharing Features

- [ ] 27.1 Implement shareable link generation
  - Generate deep links for parks
  - Include preview images and descriptions
  - Support universal links
  - _Requirements: 24.1, 24.2_

- [ ] 27.2 Implement social sharing UI
  - Add share button to park details
  - Support Messages, Instagram, Facebook, Twitter
  - Track share events without storing PII
  - _Requirements: 24.1, 24.4, 24.5_

- [ ] 27.3 Implement badge achievement sharing
  - Generate shareable badge images
  - Offer sharing after badge earned
  - _Requirements: 24.3_

- [ ]* 27.4 Write property test for shareable link generation
  - **Property 39: Shareable Link Generation**
  - **Validates: Requirements 24.2**

### Task 28: Leaderboards (Optional Feature)

- [ ] 28.1 Implement opt-in/opt-out settings
  - Add leaderboard toggle in user settings
  - Update opt-in status in DynamoDB
  - _Requirements: 21.1_

- [ ] 28.2 Implement leaderboard calculation
  - Rank by parks visited, reviews written, badges earned
  - Use anonymized identifiers (usernames only)
  - Calculate weekly, monthly, all-time rankings
  - _Requirements: 21.2, 21.3, 21.4_

- [ ] 28.3 Implement leaderboard UI
  - Display rankings with anonymized data
  - Show user's position if opted in
  - Filter by time period
  - _Requirements: 21.4_


- [ ]* 28.4 Write property test for leaderboard opt-in
  - **Property 35: Leaderboard Opt-In**
  - **Validates: Requirements 21.2**

- [ ]* 28.5 Write property test for leaderboard opt-out
  - **Property 36: Leaderboard Opt-Out**
  - **Validates: Requirements 21.5**

### Task 29: Enhanced Onboarding

- [ ] 29.1 Design onboarding screens (max 5)
  - Explain badge system
  - Explain challenges and progression
  - Explain AI chat feature
  - Show example park discovery
  - _Requirements: 22.1, 22.2_

- [ ] 29.2 Implement onboarding flow
  - Display on first launch
  - Allow skip at any point
  - Award "First Steps" badge on completion
  - _Requirements: 22.3, 22.4_

- [ ] 29.3 Implement onboarding state tracking
  - Track completion status
  - Don't show again after completion
  - _Requirements: 22.5_

---

## Phase 8: Monitoring, Metrics & Optimization

### Task 30: Cost Tracking and Metrics

- [ ] 30.1 Implement LLM call logging
  - Log all Claude API calls with timestamps
  - Track cost per call
  - Attribute costs to user tiers
  - _Requirements: 26.1_


- [ ] 30.2 Implement Lambda cost tracking
  - Track execution duration and memory usage
  - Calculate costs per function
  - Compare to pre-migration EC2 costs
  - _Requirements: 26.2_

- [ ] 30.3 Implement cache hit rate monitoring
  - Track cache hits vs misses
  - Calculate cost savings from reduced LLM calls
  - Generate monthly reports
  - _Requirements: 26.3_

- [ ] 30.4 Generate cost reduction reports
  - Compare pre-migration vs post-migration costs
  - Validate 60% LLM cost reduction target
  - _Requirements: 26.4, 26.5_

- [ ]* 30.5 Write property test for LLM call logging
  - **Property 41: LLM Call Logging**
  - **Validates: Requirements 26.1**

- [ ]* 30.6 Write property test for cache hit rate calculation
  - **Property 42: Cache Hit Rate Calculation**
  - **Validates: Requirements 26.3**

### Task 31: User Engagement Metrics

- [ ] 31.1 Implement user activity tracking
  - Track daily, weekly, monthly active users
  - Track session duration
  - Track feature usage patterns
  - _Requirements: 27.1, 27.4_

- [ ] 31.2 Implement conversion metrics
  - Track free-to-premium conversion rate
  - Track subscription retention
  - Track churn rate
  - _Requirements: 27.2_


- [ ] 31.3 Implement gamification metrics
  - Track badge earning rates
  - Track challenge completion rates
  - Track rank progression rates
  - _Requirements: 27.3_

- [ ] 31.4 Implement review submission metrics
  - Track review rates before/after photo upload
  - Track photo upload rates
  - _Requirements: 27.6_

- [ ] 31.5 Generate engagement reports
  - Create dashboards showing trends over time
  - Identify engagement patterns
  - _Requirements: 27.5_

- [ ]* 31.6 Write property test for user activity tracking
  - **Property 43: User Activity Tracking**
  - **Validates: Requirements 27.1**

- [ ]* 31.7 Write property test for conversion metrics calculation
  - **Property 44: Conversion Metrics Calculation**
  - **Validates: Requirements 27.2**

### Task 32: CloudWatch Monitoring and Alerting

- [ ] 32.1 Set up CloudWatch dashboards
  - API response times (p50, p95, p99)
  - Lambda cold start frequency and duration
  - Cache hit rates
  - Rate limit violations
  - Error rates
  - _Requirements: 11.4_

- [ ] 32.2 Configure CloudWatch alarms
  - Alert on p95 response time > 2 seconds
  - Alert on error rate > 1%
  - Alert on LLM costs > budget threshold
  - Alert on cache hit rate < 30%
  - Alert on DynamoDB throttling
  - Alert on S3 upload failure rate > 5%


- [ ] 32.3 Set up X-Ray tracing
  - Enable X-Ray for all Lambda functions
  - Trace API Gateway requests end-to-end
  - Identify performance bottlenecks

### Task 33: Performance Optimization

- [ ] 33.1 Optimize Aurora Serverless v2 queries
  - Analyze slow queries with pg_stat_statements
  - Add missing indices
  - Optimize vector search queries
  - _Requirements: 10.5_

- [ ] 33.2 Optimize Lambda cold starts
  - Minimize deployment package sizes
  - Use Lambda layers for shared dependencies
  - Consider Go runtime for Parks Lambda
  - _Requirements: 11.4_

- [ ] 33.3 Optimize ElastiCache usage
  - Tune cache TTLs
  - Implement cache warming for popular queries
  - Monitor cache memory usage

- [ ] 33.4 Optimize CloudFront caching
  - Tune cache behaviors
  - Implement cache invalidation strategy
  - Monitor cache hit rates

---

## Phase 9: Security Hardening

### Task 34: Security Best Practices

- [ ] 34.1 Implement least privilege IAM roles
  - Review and tighten Lambda execution roles
  - Remove unnecessary permissions
  - Use resource-based policies where appropriate


- [ ] 34.2 Enable encryption at rest
  - DynamoDB encryption with AWS KMS
  - S3 bucket encryption
  - Aurora encryption with AWS-managed keys
  - _Requirements: 12.1_

- [ ] 34.3 Enable encryption in transit
  - Enforce TLS 1.3 for all API endpoints
  - Use HTTPS for CloudFront distributions
  - Use SSL for Aurora connections

- [ ] 34.4 Implement secrets rotation
  - Rotate Claude API key quarterly
  - Rotate database credentials
  - Rotate API Gateway keys

- [ ] 34.5 Set up AWS WAF
  - Protect API Gateway from common attacks
  - Implement rate limiting at WAF level
  - Block malicious IP addresses

- [ ]* 34.6 Write property test for biometric token storage
  - **Property 11: Biometric Token Storage**
  - **Validates: Requirements 5.1, 7.1**

- [ ]* 34.7 Write property test for password policy enforcement
  - **Property 14: Password Policy Enforcement**
  - **Validates: Requirements 9.5**

### Task 35: Audit Logging

- [ ] 35.1 Implement CloudTrail logging
  - Log all API calls to AWS services
  - Enable log file validation
  - Store logs in S3 with lifecycle policies


- [ ] 35.2 Implement application-level audit logs
  - Log PII detection events
  - Log authentication events
  - Log subscription changes
  - Log badge awards and rank changes

- [ ] 35.3 Set up log retention policies
  - Retain CloudTrail logs for 1 year
  - Retain application logs for 90 days
  - Archive to Glacier for long-term storage

---

## Phase 10: Testing & Quality Assurance

### Task 36: Integration Testing

- [ ] 36.1 Set up LocalStack for local AWS testing
  - Configure DynamoDB, S3, Lambda emulation
  - Create test fixtures and seed data

- [ ] 36.2 Write integration tests for authentication flow
  - Test registration, login, token refresh
  - Test Apple Sign In integration
  - Test biometric authentication

- [ ] 36.3 Write integration tests for photo pipeline
  - Test full upload → blur → storage flow
  - Test with real Rekognition API
  - Test content moderation

- [ ] 36.4 Write integration tests for AI chat
  - Test query caching
  - Test RAG retrieval
  - Test weather integration

- [ ] 36.5 Write integration tests for badge system
  - Test amenity verification
  - Test badge awarding
  - Test rank progression


### Task 37: Load Testing

- [ ] 37.1 Create load test scenarios
  - Simulate 100 concurrent users
  - Test API Gateway rate limiting
  - Test Lambda auto-scaling
  - Test Aurora Serverless v2 scaling

- [ ] 37.2 Test RDS Proxy under load
  - Simulate 50+ concurrent Lambda invocations
  - Verify connection pooling works correctly
  - Measure latency improvements vs direct connections

- [ ] 37.3 Test photo pipeline under load
  - Simulate 10+ concurrent photo uploads
  - Measure end-to-end latency
  - Verify S3 Object Lambda performance

- [ ] 37.4 Analyze load test results
  - Identify bottlenecks
  - Optimize configurations
  - Validate performance targets

### Task 38: iOS UI Testing

- [ ] 38.1 Write UI tests for critical flows
  - Onboarding flow
  - Authentication flow
  - Park search and details
  - Review submission with photos
  - Badge earning celebration

- [ ] 38.2 Write UI tests for offline mode
  - Test offline indicator
  - Test cached data display
  - Test sync queue

- [ ] 38.3 Write UI tests for premium features
  - Test paywall display
  - Test subscription purchase flow
  - Test AI chat access


---

## Phase 11: Migration & Deployment

### Task 39: Data Migration Execution

- [ ] 39.1 Export existing data from SQLite
  - Export user accounts
  - Export reviews
  - Export badges
  - Validate data integrity

- [ ] 39.2 Transform data to DynamoDB schema
  - Map SQLite schema to DynamoDB
  - Handle data type conversions
  - Preserve relationships

- [ ] 39.3 Import data to DynamoDB
  - Batch write items
  - Verify import success
  - Validate data integrity with checksums

- [ ] 39.4 Migrate ChromaDB embeddings to Aurora
  - Export embeddings
  - Import to Aurora pgvector
  - Build indices
  - Validate search results

### Task 40: Feature Flags Implementation

- [ ] 40.1 Implement feature flag system
  - Use AWS AppConfig or LaunchDarkly
  - Define flags for all new features
  - Implement flag evaluation in backend

- [ ] 40.2 Configure gradual rollout strategy
  - Enable features for 10% of users initially
  - Monitor metrics and errors
  - Gradually increase to 100%


### Task 41: Deployment Pipeline

- [ ] 41.1 Set up CI/CD pipeline
  - Configure GitHub Actions or AWS CodePipeline
  - Run tests on every commit
  - Deploy to staging on merge to main

- [ ] 41.2 Implement canary deployments
  - Deploy to 5% of traffic initially
  - Monitor error rates and latency
  - Automatic rollback if error rate > 1%

- [ ] 41.3 Configure blue-green deployment for iOS
  - Maintain backward compatibility for 2 app versions
  - Support gradual app store rollout

### Task 42: Rollout Execution

- [ ] 42.1 Deploy to staging environment
  - Run full test suite
  - Perform manual QA
  - Validate all features

- [ ] 42.2 Deploy to production with 10% traffic
  - Monitor metrics closely
  - Validate cost reduction targets
  - Check for errors

- [ ] 42.3 Gradually increase to 100% traffic
  - Increase by 10% every 2 days
  - Monitor at each step
  - Roll back if issues detected

- [ ] 42.4 Decommission old infrastructure
  - Maintain old system for 30 days as backup
  - Archive old data
  - Shut down old servers

---

## Phase 12: Post-Launch Optimization

### Task 43: Performance Tuning

- [ ] 43.1 Analyze production metrics
  - Review CloudWatch dashboards
  - Identify slow queries
  - Find optimization opportunities


- [ ] 43.2 Optimize based on real usage patterns
  - Adjust cache TTLs
  - Tune Lambda memory allocations
  - Optimize database queries

- [ ] 43.3 Implement additional caching layers
  - Cache popular park searches
  - Cache user profiles
  - Cache badge data

### Task 44: Cost Optimization

- [ ] 44.1 Analyze actual costs vs projections
  - Review AWS Cost Explorer
  - Identify cost drivers
  - Validate 60% LLM cost reduction

- [ ] 44.2 Implement cost-saving measures
  - Adjust Lambda memory allocations
  - Optimize Aurora Serverless v2 scaling
  - Review and optimize S3 storage classes

- [ ] 44.3 Set up cost anomaly detection
  - Configure AWS Cost Anomaly Detection
  - Set up alerts for unexpected cost spikes

### Task 45: User Feedback and Iteration

- [ ] 45.1 Collect user feedback
  - Monitor app store reviews
  - Track support tickets
  - Analyze usage patterns

- [ ] 45.2 Prioritize improvements
  - Identify pain points
  - Plan feature enhancements
  - Address bugs and issues

- [ ] 45.3 Iterate on gamification features
  - Analyze badge earning rates
  - Adjust challenge difficulty
  - Add new badges and challenges based on feedback

---

## Notes


**Tasks marked with `*` are optional** and can be skipped for faster MVP delivery. However, property-based tests (especially Property 24 for face blurring) are highly recommended for production readiness.

**Critical Priorities for AWS Builder Competition**:
1. **Photo Safety Pipeline (Phase 2)**: The automated face blurring is the "Secret Sauce" differentiator
2. **RDS Proxy (Task 10.3)**: Prevents connection exhaustion under load - shows production-ready thinking
3. **S3 Object Lambda (Task 5.2)**: Modern, cost-effective approach that judges will appreciate
4. **DynamoDB Write Sharding (Task 3.2)**: Prevents hot partitions - demonstrates scalability expertise
5. **Provisioned Concurrency (Task 16.4)**: Eliminates cold start UX issues - shows user-centric design

**Implementation Language**: Python 3.11 for all Lambda functions, with optional Go optimization for Parks Lambda (Task 15.3) if performance targets aren't met.

**Testing Philosophy**:
- Unit tests validate specific examples and edge cases
- Property-based tests validate universal correctness across all inputs
- Both are complementary and necessary for comprehensive coverage
- Minimum 100 iterations per property test due to randomization

**Traceability**: Each task references specific requirements from requirements.md for full traceability.

**Checkpoints**: Natural checkpoints occur at the end of each phase. Ensure all tests pass and ask the user if questions arise before proceeding to the next phase.

