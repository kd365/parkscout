# Requirements Document: ParkScout Premium & AWS Migration

## Introduction

This document specifies requirements for transforming ParkScout from a cost-intensive, monolithic parks discovery app into a scalable, secure, and monetizable platform. The improvements focus on five key areas: cost optimization through tiered access, enhanced security with native iOS authentication, AWS infrastructure migration for scalability, improved user experience with gamification, and expanded Scout-themed progression systems.

The system will maintain backward compatibility with existing park data and reviews while introducing premium features, serverless architecture, and enhanced engagement mechanisms.

## Glossary

- **ParkScout_App**: The iOS mobile application for discovering parks in Fairfax County
- **Backend_API**: The FastAPI-based server handling requests, LLM interactions, and data management
- **AI_Chat**: The Claude LLM-powered conversational interface for park recommendations
- **Free_User**: A user with basic access to park discovery, map view, and limited reviews
- **Premium_User**: A paid subscriber with access to AI chat, unlimited reviews, and advanced features
- **Badge_System**: The gamification mechanism that awards merit badges for verifying specific park amenities
- **Amenity_Badge**: A merit badge earned by verifying specific park features like fencing, shade, bathrooms, or stroller accessibility
- **Scout_Rank**: User progression level from Tenderfoot to Park Legend based on contributions
- **Scout_Intel**: User-contributed information including reviews, photos, and amenity verifications
- **Scout_Challenge**: A time-bound or milestone-based achievement goal
- **Vector_Database**: AWS-managed database for semantic search of park information (OpenSearch or Bedrock)
- **Rate_Limiter**: System component that restricts API request frequency per user
- **StoreKit**: Apple's framework for in-app purchases and subscriptions
- **Cognito**: AWS authentication and user management service
- **CloudFront**: AWS content delivery network for image distribution
- **DynamoDB**: AWS NoSQL database for user data and reviews
- **Lambda_Function**: AWS serverless compute function
- **API_Gateway**: AWS service for managing, securing, and routing API requests
- **Rekognition**: AWS service for image analysis, face detection, and content moderation
- **Biometric_Auth**: iOS Face ID or Touch ID authentication
- **Sign_In_With_Apple**: Apple's native authentication service
- **Query_Cache**: Storage mechanism for frequently requested AI responses
- **User_Progression**: System tracking user level, experience points, and milestones
- **Leaderboard**: Optional ranking system showing top scouts by activity
- **Photo_Upload**: Feature allowing users to attach images to park reviews
- **Offline_Mode**: App functionality available without internet connectivity
- **Token_Manager**: Component handling secure storage and refresh of authentication tokens
- **PII**: Personally Identifiable Information requiring protection

## Requirements

### Requirement 1: Tiered Access Model

**User Story:** As a product owner, I want to implement a freemium model with AI chat as a premium feature, so that I can reduce API costs while generating revenue from engaged users.

#### Acceptance Criteria

1. WHEN a Free_User attempts to access AI_Chat, THEN THE ParkScout_App SHALL display a paywall with subscription options
2. WHEN a Premium_User accesses AI_Chat, THEN THE ParkScout_App SHALL allow unlimited chat interactions within rate limits
3. THE ParkScout_App SHALL provide Free_Users with access to map view, park details, basic search, unlimited review submission, and amenity badge tagging
4. WHEN viewing park details, THEN THE ParkScout_App SHALL show Free_Users only amenity tags and badge information without full review text
5. WHEN viewing park details, THEN THE ParkScout_App SHALL show Premium_Users full review text, photos, and amenity tags
6. WHEN a user subscribes to premium, THEN THE Backend_API SHALL update the user tier within 30 seconds
7. THE Backend_API SHALL enforce tier restrictions on all protected endpoints

### Requirement 2: AI Chat Rate Limiting

**User Story:** As a system administrator, I want to implement rate limiting on AI queries, so that I can prevent abuse and control costs even for premium users.

#### Acceptance Criteria

1. WHEN a Premium_User makes AI_Chat requests, THEN THE Rate_Limiter SHALL allow up to 50 queries per hour
2. WHEN a user exceeds the rate limit, THEN THE Backend_API SHALL return an error with retry-after time
3. THE Rate_Limiter SHALL reset user quotas every hour on a rolling window basis
4. WHEN rate limit is approached, THEN THE ParkScout_App SHALL display remaining query count to the user
5. THE Backend_API SHALL log all rate limit violations for monitoring

### Requirement 3: Query Caching Strategy

**User Story:** As a system administrator, I want to cache common AI queries, so that I can reduce LLM API costs for frequently asked questions.

#### Acceptance Criteria

1. WHEN an AI_Chat query matches a cached response, THEN THE Backend_API SHALL return the cached result without calling the LLM
2. THE Query_Cache SHALL store responses for queries asked by at least 3 different users
3. THE Query_Cache SHALL expire entries after 7 days
4. WHEN generating cache keys, THEN THE Backend_API SHALL normalize queries to improve hit rates
5. THE Backend_API SHALL track cache hit rate and report metrics above 30 percent

### Requirement 4: Sign in with Apple Integration

**User Story:** As an iOS user, I want to sign in with my Apple ID, so that I can authenticate quickly without creating another password.

#### Acceptance Criteria

1. WHEN a user selects Sign_In_With_Apple, THEN THE ParkScout_App SHALL initiate Apple authentication flow
2. WHEN Apple authentication succeeds, THEN THE ParkScout_App SHALL receive a verified user token
3. THE Backend_API SHALL accept Apple ID tokens and create or link user accounts
4. WHEN a user signs in with Apple for the first time, THEN THE Backend_API SHALL create a new account with Apple-provided information
5. THE ParkScout_App SHALL handle Apple authentication errors gracefully with user-friendly messages

### Requirement 5: Biometric Authentication

**User Story:** As a user, I want to use Face ID or Touch ID to access my account, so that I can authenticate securely without typing passwords.

#### Acceptance Criteria

1. WHEN a user enables Biometric_Auth, THEN THE ParkScout_App SHALL store authentication tokens in iOS Keychain with biometric protection
2. WHEN the app launches and biometric is enabled, THEN THE ParkScout_App SHALL prompt for Face ID or Touch ID
3. WHEN biometric authentication succeeds, THEN THE ParkScout_App SHALL retrieve stored tokens and authenticate the session
4. IF biometric authentication fails 3 times, THEN THE ParkScout_App SHALL fall back to password authentication
5. THE ParkScout_App SHALL allow users to disable biometric authentication in settings

### Requirement 6: StoreKit 2 Payment Integration

**User Story:** As a user, I want to purchase premium subscription through Apple's payment system, so that I can access AI chat and advanced features securely.

#### Acceptance Criteria

1. WHEN a user selects a subscription tier, THEN THE ParkScout_App SHALL initiate StoreKit purchase flow
2. WHEN purchase completes successfully, THEN THE ParkScout_App SHALL verify the receipt with Apple servers
3. THE Backend_API SHALL validate StoreKit receipts and update user premium status
4. WHEN a subscription expires, THEN THE Backend_API SHALL downgrade the user to Free_User tier
5. THE ParkScout_App SHALL handle subscription restoration for users reinstalling the app
6. THE ParkScout_App SHALL display subscription status and renewal date in user settings

### Requirement 7: Secure Token Management

**User Story:** As a security engineer, I want to implement secure token storage and automatic refresh, so that user sessions remain secure and seamless.

#### Acceptance Criteria

1. THE Token_Manager SHALL store access tokens and refresh tokens in iOS Keychain with appropriate protection levels
2. WHEN an access token expires, THEN THE Token_Manager SHALL automatically request a new token using the refresh token
3. WHEN a refresh token expires, THEN THE ParkScout_App SHALL prompt the user to re-authenticate
4. THE Token_Manager SHALL encrypt tokens at rest using iOS Data Protection APIs
5. WHEN the app is backgrounded, THEN THE Token_Manager SHALL clear sensitive tokens from memory

### Requirement 8: PII Protection in Reviews

**User Story:** As a privacy officer, I want to detect and protect PII in user reviews, so that personal information is not publicly exposed.

#### Acceptance Criteria

1. WHEN a user submits a review, THEN THE Backend_API SHALL scan the text for email addresses, phone numbers, and street addresses
2. WHEN PII is detected, THEN THE Backend_API SHALL redact or reject the review with an explanation
3. THE Backend_API SHALL log PII detection events for security monitoring
4. THE ParkScout_App SHALL warn users before submission if potential PII is detected
5. THE Backend_API SHALL apply PII detection to both new reviews and review edits

### Requirement 9: AWS Cognito Authentication Migration

**User Story:** As a system architect, I want to migrate authentication to AWS Cognito, so that I can leverage managed identity services with better scalability and security.

#### Acceptance Criteria

1. THE Backend_API SHALL integrate with Cognito for user registration, login, and token validation
2. WHEN a user registers, THEN Cognito SHALL create a user pool entry and return authentication tokens
3. THE Backend_API SHALL validate all incoming requests using Cognito JWT tokens
4. WHEN migrating existing users, THEN THE Backend_API SHALL preserve user IDs and authentication state
5. Cognito SHALL enforce password policies with minimum 8 characters, uppercase, lowercase, and numbers

### Requirement 10: Vector Database Migration to AWS

**User Story:** As a system architect, I want to migrate ChromaDB to AWS OpenSearch with vector engine, so that I can achieve better scalability and managed infrastructure for semantic search.

#### Acceptance Criteria

1. THE Backend_API SHALL store park embeddings in OpenSearch vector indices
2. WHEN performing semantic search, THEN THE Backend_API SHALL query OpenSearch using k-NN vector search
3. THE Backend_API SHALL migrate all existing ChromaDB embeddings to OpenSearch without data loss
4. WHEN new parks are added, THEN THE Backend_API SHALL generate embeddings and store them in OpenSearch
5. THE Backend_API SHALL achieve query response times under 500ms for vector searches

### Requirement 11: Lambda Function Backend Migration

**User Story:** As a system architect, I want to migrate the FastAPI backend to AWS Lambda functions, so that I can reduce costs through serverless scaling and pay-per-use pricing.

#### Acceptance Criteria

1. THE Backend_API SHALL deploy as Lambda_Functions behind API_Gateway
2. WHEN request volume is low, THEN Lambda_Functions SHALL scale to zero to minimize costs
3. WHEN request volume increases, THEN Lambda_Functions SHALL auto-scale to handle load
4. THE Lambda_Functions SHALL maintain response times under 2 seconds including cold starts
5. THE Backend_API SHALL implement connection pooling for DynamoDB and OpenSearch to optimize Lambda performance

### Requirement 12: S3 and CloudFront for Images

**User Story:** As a system architect, I want to store park images in S3 and serve them through CloudFront, so that I can reduce server load and improve image delivery performance.

#### Acceptance Criteria

1. THE Backend_API SHALL store all park images in S3 buckets with appropriate access controls
2. THE ParkScout_App SHALL retrieve images through CloudFront URLs
3. WHEN a user uploads a photo, THEN THE Backend_API SHALL generate a presigned S3 URL for direct upload
4. CloudFront SHALL cache images with a 30-day TTL
5. THE Backend_API SHALL serve images in WebP format with fallback to JPEG for compatibility

### Requirement 13: DynamoDB for User Data and Reviews

**User Story:** As a system architect, I want to migrate user data and reviews to DynamoDB, so that I can achieve better scalability and performance than SQLite.

#### Acceptance Criteria

1. THE Backend_API SHALL store user profiles, reviews, and badges in DynamoDB tables
2. WHEN querying user data, THEN THE Backend_API SHALL use DynamoDB partition keys for efficient lookups
3. THE Backend_API SHALL implement DynamoDB global secondary indices for common query patterns
4. WHEN migrating from SQLite, THEN THE Backend_API SHALL preserve all existing user data and relationships
5. THE Backend_API SHALL implement optimistic locking for concurrent review updates

### Requirement 14: API Gateway with Rate Limiting

**User Story:** As a system architect, I want to implement API Gateway with rate limiting and API keys, so that I can protect the backend from abuse and control access.

#### Acceptance Criteria

1. THE API_Gateway SHALL route all client requests to appropriate Lambda_Functions
2. THE API_Gateway SHALL enforce rate limits of 100 requests per minute for Free_Users
3. THE API_Gateway SHALL enforce rate limits of 500 requests per minute for Premium_Users
4. WHEN rate limits are exceeded, THEN THE API_Gateway SHALL return HTTP 429 with retry-after headers
5. THE API_Gateway SHALL require API keys for all requests and validate them before routing

### Requirement 15: Merit Badge System with Amenity Verification

**User Story:** As a user, I want to earn merit badges by verifying specific park amenities, so that I contribute valuable "Scout Intel" while feeling rewarded for my contributions.

#### Acceptance Criteria

1. THE Badge_System SHALL award Amenity_Badges for verifying specific park features including clean bathrooms, fenced playgrounds, shade coverage, nearby coffee shops, and stroller-friendly paths
2. WHEN a user is the first to verify an amenity at a park, THEN THE Backend_API SHALL award the corresponding Amenity_Badge immediately
3. WHEN 3 different users verify the same amenity type at the same park, THEN THE Backend_API SHALL award a master-level version of that Amenity_Badge to the park
4. WHEN a user earns a badge, THEN THE ParkScout_App SHALL display a full-screen celebration animation with the badge icon
5. THE ParkScout_App SHALL play a congratulatory sound effect when badges are earned
6. WHEN viewing a park profile, THEN THE ParkScout_App SHALL display earned Amenity_Badges in a visual row similar to a Scout sash
7. WHEN an amenity has not been verified, THEN THE ParkScout_App SHALL show a greyed-out badge with a prompt asking "Is this park fenced in? Tap to scout it!"
8. THE ParkScout_App SHALL allow users to share badge achievements to social media
9. THE Backend_API SHALL define these specific Amenity_Badges: The Golden Throne (bathrooms), The Fortress (fenced playgrounds), The Solar Shield (shade), The Caffeine Compass (nearby coffee), The Smooth Roller (stroller paths)

### Requirement 16: Photo Upload with Content Moderation

**User Story:** As a user, I want to attach photos to my park reviews, so that I can share visual experiences with other scouts.

#### Acceptance Criteria

1. WHEN submitting a review, THEN THE ParkScout_App SHALL allow all users to attach up to 5 photos
2. THE ParkScout_App SHALL compress images to under 2MB before upload
3. THE Backend_API SHALL validate image formats and reject non-image files
4. WHEN a photo is uploaded, THEN THE Backend_API SHALL use AWS Rekognition to detect faces and automatically blur them
5. WHEN a photo is uploaded, THEN THE Backend_API SHALL use AWS Rekognition to detect inappropriate content and flag it for review
6. WHEN a photo contains low-quality or irrelevant content, THEN THE Backend_API SHALL flag it as potentially useless
7. THE Backend_API SHALL reject photos flagged as inappropriate before storing them
8. WHEN viewing park details, THEN THE ParkScout_App SHALL display user-uploaded photos alongside Google Places photos
9. THE ParkScout_App SHALL indicate photo source with badges showing "Scout Photo" or "Google Places"

### Requirement 16a: Google Places Photo Integration

**User Story:** As a user, I want to see both official Google Places photos and community Scout photos, so that I get a comprehensive visual understanding of each park.

#### Acceptance Criteria

1. THE Backend_API SHALL fetch park photos from Google Places API for each park
2. WHEN displaying park photos, THEN THE ParkScout_App SHALL show Google Places photos first, followed by Scout-uploaded photos
3. THE Backend_API SHALL cache Google Places photos in S3 to reduce API costs
4. THE Backend_API SHALL refresh Google Places photos every 30 days
5. WHEN a park has no Google Places photos, THEN THE ParkScout_App SHALL display only Scout photos
6. THE ParkScout_App SHALL display photo attribution with "Photo by Google" or "Photo by [Scout_Rank] [Username]"

### Requirement 17: Offline Mode Support

**User Story:** As a user, I want to access basic park information offline, so that I can use the app in areas with poor connectivity.

#### Acceptance Criteria

1. THE ParkScout_App SHALL cache park details, locations, and basic information locally
2. WHEN offline, THEN THE ParkScout_App SHALL display cached park information with an offline indicator
3. THE ParkScout_App SHALL queue review submissions when offline and sync when connectivity returns
4. WHEN returning online, THEN THE ParkScout_App SHALL sync queued actions within 30 seconds
5. THE ParkScout_App SHALL display map tiles from cache when offline using MapKit offline capabilities

### Requirement 18: Personalized Park Recommendations

**User Story:** As a user, I want to receive personalized park recommendations based on my preferences and history, so that I can discover parks that match my interests.

#### Acceptance Criteria

1. THE Backend_API SHALL track user park visits, reviews, and badge progress
2. WHEN a user views recommendations, THEN THE Backend_API SHALL generate suggestions based on user activity patterns
3. THE Backend_API SHALL consider park features, distance, and user preferences in recommendations
4. THE ParkScout_App SHALL display personalized recommendations on the home screen
5. WHEN a Free_User views recommendations, THEN THE ParkScout_App SHALL show 5 suggestions
6. WHEN a Premium_User views recommendations, THEN THE ParkScout_App SHALL show 10 suggestions with AI-enhanced descriptions

### Requirement 19: Scout Challenges and Achievement Diversity

**User Story:** As a user, I want to participate in Scout Challenges that reward various activities beyond just reviews, so that I have multiple ways to engage and progress.

#### Acceptance Criteria

1. THE Backend_API SHALL define Scout_Challenges with goals including park visits, social media shares, amenity verifications, and review submissions
2. WHEN a user visits a new park, THEN THE Backend_API SHALL award progress toward visit-based challenges
3. WHEN a user shares a park to social media, THEN THE Backend_API SHALL award progress toward sharing challenges
4. WHEN a user completes a challenge, THEN THE Backend_API SHALL award challenge-specific badges and rank progression points
5. THE ParkScout_App SHALL display active challenges with progress tracking on the home screen
6. THE Backend_API SHALL create monthly rotating challenges automatically
7. WHEN a Premium_User completes challenges, THEN THE Backend_API SHALL award bonus recognition in the community feed
8. THE ParkScout_App SHALL send push notifications when new challenges are available
9. THE Backend_API SHALL track challenge completion rates for engagement metrics

### Requirement 20: Scout Rank Progression System

**User Story:** As a user, I want to progress through Scout ranks from Tenderfoot to Park Legend, so that I build credibility and my contributions carry more weight in the community.

#### Acceptance Criteria

1. THE Backend_API SHALL implement Scout_Rank progression with four tiers: Tenderfoot, Trailblazer, Pathfinder, and Park Legend
2. WHEN a user creates an account, THEN THE Backend_API SHALL assign them the Tenderfoot rank
3. WHEN a user checks in and reviews 5 parks, THEN THE Backend_API SHALL promote them to Trailblazer rank
4. WHEN a user contributes 10 or more amenity verifications, THEN THE Backend_API SHALL promote them to Pathfinder rank
5. WHEN a user reaches 50 total contributions including reviews, amenity tags, photos, park visits, and social shares, THEN THE Backend_API SHALL promote them to Park Legend rank
6. WHEN a user ranks up, THEN THE ParkScout_App SHALL display a rank-up celebration animation
7. THE ParkScout_App SHALL display user Scout_Rank and progress on the profile screen
8. WHEN the AI_Chat provides recommendations, THEN THE Backend_API SHALL include Scout_Rank information as social proof in responses
9. THE Backend_API SHALL weight contributions from higher-ranked scouts more heavily in recommendation algorithms

### Requirement 21: Privacy-Respecting Leaderboards

**User Story:** As a user, I want to optionally participate in leaderboards, so that I can compare my progress with other scouts while maintaining privacy.

#### Acceptance Criteria

1. THE ParkScout_App SHALL allow users to opt-in to Leaderboard participation in settings
2. WHEN a user opts in, THEN THE Backend_API SHALL include their anonymized data in leaderboard calculations
3. THE Leaderboard SHALL display only usernames or anonymous identifiers, never full names or PII
4. THE ParkScout_App SHALL show leaderboards for weekly, monthly, and all-time periods
5. WHEN a user opts out, THEN THE Backend_API SHALL immediately remove them from all leaderboards
6. THE Leaderboard SHALL rank users by total parks visited, reviews written, and badges earned

### Requirement 22: Enhanced Onboarding Flow

**User Story:** As a new user, I want a guided onboarding experience, so that I understand the app's features and Scout theme quickly.

#### Acceptance Criteria

1. WHEN a user launches the app for the first time, THEN THE ParkScout_App SHALL display an interactive onboarding tutorial
2. THE ParkScout_App SHALL explain the badge system, challenges, and progression during onboarding
3. THE ParkScout_App SHALL allow users to skip onboarding at any point
4. WHEN onboarding completes, THEN THE ParkScout_App SHALL award a "First Steps" badge
5. THE ParkScout_App SHALL use no more than 5 onboarding screens to avoid overwhelming users

### Requirement 23: Weather Integration for LLM and UI

**User Story:** As a user, I want to see current weather conditions for parks and have the AI consider weather in recommendations, so that I can plan visits appropriately.

#### Acceptance Criteria

1. WHEN viewing park details, THEN THE ParkScout_App SHALL display current weather conditions and temperature
2. THE ParkScout_App SHALL show weather icons indicating conditions like sunny, rainy, or cloudy
3. THE Backend_API SHALL fetch weather data from a weather API with updates every 30 minutes
4. THE ParkScout_App SHALL display weather forecasts for the next 3 days on park detail screens
5. WHEN weather conditions are severe, THEN THE ParkScout_App SHALL display a warning banner
6. WHEN the AI_Chat generates recommendations, THEN THE Backend_API SHALL provide current weather data to the LLM context
7. THE Backend_API SHALL enable the LLM to adjust recommendations based on weather conditions such as suggesting shaded parks on hot days or indoor alternatives during rain
8. WHEN a user asks weather-related questions, THEN THE AI_Chat SHALL provide weather-aware responses using real-time data

### Requirement 24: Social Sharing Features

**User Story:** As a user, I want to share parks and achievements with friends, so that I can encourage others to explore parks.

#### Acceptance Criteria

1. WHEN viewing a park, THEN THE ParkScout_App SHALL provide a share button for social media and messaging
2. THE ParkScout_App SHALL generate shareable links with park preview images and descriptions
3. WHEN a user earns a badge, THEN THE ParkScout_App SHALL offer to share the achievement
4. THE ParkScout_App SHALL support sharing to Messages, Instagram, Facebook, and Twitter
5. THE Backend_API SHALL track share events for analytics without storing PII

### Requirement 25: Backward Compatibility with Existing Data

**User Story:** As a system administrator, I want to maintain backward compatibility during migration, so that existing users experience no data loss or service disruption.

#### Acceptance Criteria

1. WHEN migrating to AWS infrastructure, THEN THE Backend_API SHALL preserve all existing park data without modification
2. THE Backend_API SHALL migrate user accounts, reviews, and badges with complete data integrity
3. WHEN users update the app, THEN THE ParkScout_App SHALL continue to function with both old and new backend endpoints during transition
4. THE Backend_API SHALL maintain API compatibility for at least 2 app versions during migration
5. THE Backend_API SHALL implement feature flags to enable gradual rollout of new infrastructure

### Requirement 26: Cost Reduction Metrics

**User Story:** As a product owner, I want to measure cost reduction from infrastructure changes, so that I can validate the business case for migration.

#### Acceptance Criteria

1. THE Backend_API SHALL log all LLM API calls with cost attribution
2. THE Backend_API SHALL track Lambda execution costs and compare to previous EC2 costs
3. THE Backend_API SHALL measure cache hit rates and calculate cost savings from reduced LLM calls
4. THE Backend_API SHALL generate monthly cost reports comparing pre-migration and post-migration expenses
5. THE Backend_API SHALL achieve at least 60 percent reduction in LLM costs through tiered access and caching

### Requirement 27: User Engagement Metrics

**User Story:** As a product owner, I want to track user engagement metrics, so that I can measure the impact of gamification and premium features.

#### Acceptance Criteria

1. THE Backend_API SHALL track daily active users, weekly active users, and monthly active users
2. THE Backend_API SHALL measure premium conversion rate and subscription retention
3. THE Backend_API SHALL track badge earning rates and challenge completion rates
4. THE Backend_API SHALL measure average session duration and feature usage patterns
5. THE Backend_API SHALL generate engagement reports showing trends over time
6. THE Backend_API SHALL track review submission rates before and after photo upload feature launch

## Phased Rollout Plan

### Phase 1: MVP (Months 1-2)
- Requirement 1: Tiered Access Model
- Requirement 6: StoreKit 2 Payment Integration
- Requirement 2: AI Chat Rate Limiting
- Requirement 9: AWS Cognito Authentication Migration
- Requirement 14: API Gateway with Rate Limiting
- Requirement 25: Backward Compatibility

### Phase 2: Infrastructure Migration (Months 2-3)
- Requirement 10: Vector Database Migration to AWS
- Requirement 11: Lambda Function Backend Migration
- Requirement 12: S3 and CloudFront for Images
- Requirement 13: DynamoDB for User Data and Reviews
- Requirement 3: Query Caching Strategy

### Phase 3: Security & Authentication (Month 3)
- Requirement 4: Sign in with Apple Integration
- Requirement 5: Biometric Authentication
- Requirement 7: Secure Token Management
- Requirement 8: PII Protection in Reviews

### Phase 4: Enhanced UX & Gamification (Months 4-5)
- Requirement 15: Enhanced Badge System with Animations
- Requirement 19: Scout Challenges System
- Requirement 20: User Progression System
- Requirement 22: Enhanced Onboarding Flow
- Requirement 16: Photo Upload for Reviews

### Phase 5: Advanced Features (Month 5-6)
- Requirement 17: Offline Mode Support
- Requirement 18: Personalized Park Recommendations
- Requirement 21: Privacy-Respecting Leaderboards
- Requirement 23: Weather Integration in UI
- Requirement 24: Social Sharing Features

### Phase 6: Metrics & Optimization (Ongoing)
- Requirement 26: Cost Reduction Metrics
- Requirement 27: User Engagement Metrics

## Success Criteria

- **Cost Reduction**: Achieve 60% reduction in monthly LLM API costs
- **Premium Conversion**: Reach 5% free-to-premium conversion rate within 6 months
- **User Engagement**: Increase average session duration by 40%
- **Review Growth**: Increase review submissions by 50% with photo upload feature
- **Infrastructure Performance**: Maintain 99.9% uptime with AWS migration
- **Security**: Zero PII exposure incidents post-implementation
