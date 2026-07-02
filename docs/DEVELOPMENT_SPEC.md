# CarbonSnap Development Specification (Spec Coding)

## 1. Document Goal
This document defines how CarbonSnap should be designed, implemented, tested, and reviewed using a Specification-First workflow.
Local run commands are maintained in `docs/architecture/RUNNING_PROJECT.md`.

- Frontend: Vue.js + Vite
- Backend: Flask
- AI orchestration: centralized LLM-driven decision engine over a provider-aware multimodal service layer; optional LangGraph Graph Agent path behind `AI_GRAPH_AGENT_ENABLED`
- Retrieval layers: guarded forum RAG with FAISS-backed recall and optional Neo4j GraphRAG behind `AI_NEO4J_GRAPHRAG_ENABLED`

## 2. Product Vision and Scope
CarbonSnap helps users identify recyclable waste with AI, estimate carbon reduction, earn points, and participate in a sustainability ecosystem through community, projects, and marketplace workflows.

Scope includes:
1. AI Recycling Assistant (image understanding, carbon estimation, recommendations, RAG, memory)
2. Forum
3. Projects (points crowdfunding)
4. Personal Carbon Ledger
5. C2C Marketplace (points-based escrow order flow)
6. User Profile
7. Personalized Recommendation System (posts, projects, marketplace items, AI reply personalization)
8. Notification Center (likes, comments, comment replies, order updates, project completion)

## 3. Roles and Permissions

- User
- Upload images, use AI assistant, create forum posts, join projects, list items, place orders, view ledger and profile.
- Organization accounts are special user accounts (enterprise or NGO). The profile badge is a unified system-defined icon shown at the bottom-right of avatar.
- Organization accounts can create and manage sustainability projects with points targets.

- Admin (optional)
- Moderate forum and marketplace content, handle abnormal orders.

Use basic RBAC: `user`, `admin`.
Organization is not a separate RBAC role. It is a user account type represented by account attributes, and the badge itself is a fixed frontend asset (not uploaded and not stored as a database field).

## 4. Spec Coding Development Rules

### 4.1 Required workflow
1. Write specification first: user stories, acceptance criteria, edge cases.
2. Define API contracts: request, response, status codes, error codes.
3. Write test cases: happy path plus critical failures.
4. Implement code after spec and tests are ready.
5. Merge only after review and automated test pass.

### 4.2 Definition of Ready (DoR)
- Goal and scope are clear.
- API contract is agreed.
- Data schema is defined.
- Acceptance criteria are testable.

### 4.3 Definition of Done (DoD)
- Acceptance criteria passed.
- Unit and integration tests passed.
- Logging and error handling in critical paths.
- Docs updated (API/data model/changelog).

## 5. System Architecture

### 5.1 High-level architecture
- Web frontend (Vue + Vite)
- Flask API layer (auth, validation, routing)
- AI service layer (current: provider-aware multimodal service layer plus centralized decision engine; optional LangGraph orchestration for the Graph Agent path)
- Recommendation service layer (behavior ingestion, preference scoring, ranking)
- Notification service layer (event triggers, fanout, read/unread state, source routing)
- Map service via tool-calling (current implementation: public OpenStreetMap via Nominatim + Overpass)
- Relational database (MySQL) for users, posts, orders, and points
- FAISS index for forum RAG retrieval
- Optional Neo4j graph for AI-facing recycling knowledge, graph paths, rules, risks, facilities, and knowledge chunks

### 5.2 Recommended backend layering
- `api/`: route definitions, request validation, response envelope
- `services/`: business logic
- `repositories/`: database access
- `ai/`: model calls, tool calls, retrieval, memory
- `recommender/`: user behavior features, candidate generation, ranking
- `notifications/`: event-to-notification mapping, source routing, read-state management
- `models/`: ORM models
- `tasks/`: async jobs (indexing, notifications)

## 6. Core Module Specifications

## 6.1 AI Recycling Assistant

### User story
As a user, after uploading a waste image, I want to receive:
- waste type prediction
- estimated carbon reduction and converted points
- nearby recycling guidance
- relevant forum references

### Functional requirements
1. Accept text-plus-optional-image AI messages. Text is required; image is supporting context only.
2. Route every AI message through a centralized backend LLM decision engine before choosing chat or recycling execution flow.
3. Supported top-level intents are:
- `general_chat`
- `recycling_analysis`
- `recycling_follow_up`
4. Supported recycling follow-up subtypes are:
- `guidance_follow_up`
- `nearby_search`
- `task_verification`
5. Image presence is a routing signal, not a routing decision. A message with an image may still be ordinary chat when user intent is descriptive or conversational.
6. The decision engine must consider:
- current user message text
- optional image input
- recent conversation context
- active recycling-case summaries in the current conversation
- current long-term memory summary
7. One conversation may contain multiple concurrent `recycling_cases`.
8. If a recycling follow-up is ambiguous across multiple cases, the system must ask a structured clarification question instead of guessing.
9. Call the provider-aware multimodal model layer for waste classification, structured decision calls, and final answer synthesis.
10. Estimate carbon reduction based on waste type and estimated weight.
11. Convert carbon reduction to points.
12. Use map API tool-calling to find nearby recycling points when location-aware search is needed.
13. Use FAISS retriever over forum data and return cited references when retrieval is enabled.
14. Support short-term conversation memory and long-term user preference memory.
15. Long-term memory must be model-assisted, explicit-only, and user-manageable.
16. Supported long-term memory categories are:
- response style preference
- recycling action preferences
- topic interests
- item-specific recycling method preferences
17. Long-term memory extraction must use structured LLM extraction instead of hard-coded phrase tables.
18. Support one-click conversion of good AI reply to forum draft.
19. Location permission must be requested on demand, only when AI actually needs nearby recycling search.
20. The system may use internally configured recycling stations as mock or supplemental map data, and those stations can also appear in AI recycling recommendations.
21. The system must persist full AI chat history, including user messages, assistant replies, tool messages, and completion-audit state.
22. AI responses should support staged streaming:
- stage 1: waste identification, carbon reduction estimate, points, and non-location recycling guidance
- stage 2: nearby recycling search after checking session location state
23. Image-based waste analysis is both a chat event and a business event:
- the conversation history is stored in chat tables
- the recognized recycling task is first stored as a pending `recycling_case`
- the formal confirmed recycling result is stored in `waste_analysis_records` only after audit approval for ledger traceability
24. If no valid location is available, the system must pause nearby search and request user input:
- allow browser location
- manually enter area
- skip nearby search
25. If the user rejects location access, the system must continue with non-location guidance or manual-area search instead of failing the whole answer.
26. Uploaded AI images must be stored locally under `data/uploads` and exposed through backend file URLs instead of relying on long-lived base64 payloads.
27. After a recycling suggestion is produced, the same conversation must support a completion-audit step where the user uploads a proof photo.
28. Audit approval is required before carbon reduction and points are finalized.
29. Audit failure or unclear evidence must keep the recycling case retryable within the same conversation.
30. The AI page should provide a dedicated chat workspace with:
- a conversation sidebar on the left
- streamed markdown replies on the right
- nearby recycling map cards rendered after the related assistant output
- a completion-audit card rendered after the nearby results / recycling guidance block
31. The AI page should provide a memory management entry point for logged-in users so they can view and delete remembered preference items.
32. The frontend must not make authoritative chat-versus-recycling routing decisions; backend routing is canonical.
33. Every user AI message should persist a structured decision record for debugging, replay, and future orchestration migration, including clarification outcomes.

### Calculation rules
- `co2_saved_kg = weight_kg * emission_factor_by_waste_type`
- `carbon_points = round(co2_saved_kg * 10, 2)`

`emission_factor_by_waste_type` should be configuration-driven.

### Suggested AI response fields
- `intent`
- `follow_up_type`
- `target_case_id`
- `needs_clarification`
- `clarification_question`
- `clarification_options[]`
- `memory_updated[]`
- `waste_type`
- `confidence`
- `estimated_weight_kg`
- `co2_saved_kg`
- `carbon_points`
- `recycle_suggestions[]`
- `nearby_locations[]`
- `forum_references[]` (`post_id`, `title`, `url`)
- `requires_location_decision`
- `stream_stage` (`analysis`, `awaiting_location`, `nearby_search`, `completed`)
- `location_options[]`

### Acceptance criteria
- P95 response time under 8 seconds for valid image-assisted recycling analysis requests.
- Text-only general chat must not be misrouted into recycling analysis solely because it contains recycling vocabulary or references prior recycling context.
- Image-assisted messages must not enter recycling analysis unless the decision engine classifies them as `recycling_analysis` or `recycling_follow_up`.
- Response includes points and at least one recycling suggestion when a recycling-analysis flow is executed.
- When forum results exist, include clickable references.
- If map API fails, return non-map fallback guidance.
- AI replies should reflect user preference profile when preference confidence is available.
- If location is required but not yet available, stage 1 output must still be delivered before user location decision.
- The system must avoid repeatedly prompting for location within the same valid session window.
- Users can reopen a prior AI conversation and read the full message history in order.
- One conversation can contain multiple recycling cases without forcing a new sidebar conversation.
- Ambiguous recycling follow-up must produce a clarification question instead of silently attaching to the wrong case.
- Users do not receive final points or final carbon reduction until a completion audit passes.
- Users can retry completion audit with another image when the audit result is `failed` or `unclear`.
- Conversation history replay must include enough metadata to restore pending nearby-search and completion-audit UI state for eligible recycling conversations.
- If a user explicitly asks for concise style, longer answers, manual area input, location avoidance, a topic interest, or an item-specific recycling method, the system must persist that preference as long-term AI memory.
- Logged-in users must be able to view and delete active AI memory items from the AI workspace.
- Every user AI message must have a persisted structured decision record that captures intent routing without storing raw chain-of-thought.

## 6.2 Forum

### Functional requirements
1. Create, edit, delete posts (author-owned actions).
2. Post includes title, content, images, tags.
3. Users can like and unlike posts.
4. Users can create comments under posts.
5. Comments support reply-to-comment (threaded discussion).
6. Users can like and unlike comments.
7. Post content is indexed for AI retrieval.

### Indexing requirements
- New post triggers chunking + embedding + index job.
- Post content is split into semantic chunks before vectorization.
- Edited post triggers re-chunk + re-index for affected chunks.
- Deleted post removes related chunks and vectors from index.
- Chunking configuration (size, overlap, splitter type) must be centralized and versioned.

### Acceptance criteria
- A new post is retrievable by AI within 30 seconds (async allowed).
- Reference links open the target post detail page.
- Post like count updates immediately after user action.
- Comment replies are linked correctly by parent comment id.
- Comment like count updates immediately after user action.

## 6.3 Projects (Points Crowdfunding)

### Functional requirements
1. Users marked as organization accounts can create projects with title, description, points target, and deadline.
2. Users contribute points.
3. Project status changes to `funded` when target is reached.
4. Show contribution history and progress.
5. After a project is funded and moves forward, the project creator can publish project updates as a timeline feed.
6. Project updates are read-only for users and do not support likes or comments.

### Business rules
- Points are deducted from user available balance immediately at contribution time.
- If project fails at deadline, points are refunded automatically by the system based on project refund policy.
- Only the project creator can create and edit project updates.

### Acceptance criteria
- Project progress updates right after contribution.
- No further contribution is allowed after funded.
- Users can view project updates in chronological order on the project detail page.

## 6.4 Personal Carbon Ledger

### Functional requirements
1. Record daily carbon reduction details by source (AI analysis, project activity, etc.).
2. Support day/week/month aggregation.
3. Show tabular data with date range filters.

### Acceptance criteria
- Default query range is last 30 days.
- Ledger entries are auditable against points transactions.

## 6.5 C2C Marketplace

### Functional requirements
1. Seller lists item: title, description, images, price (points), stock.
2. Buyer places order and points move into escrow.
3. Seller marks item as shipped.
4. Buyer confirms receipt, then points settle to seller.

### Order state machine
- `created` -> `paid_escrow` -> `shipped` -> `completed`
- Exception states: `cancelled`, `disputed`

### Acceptance criteria
- Escrow and settlement transactions are fully traceable.
- Seller cannot access escrow points before buyer confirmation.

## 6.6 User Profile

### Functional requirements
1. Show avatar, nickname, bio.
2. Show post history.
3. Show joined projects.
4. Show cumulative carbon reduction and points.

### Acceptance criteria
- Profile edits are visible immediately after update.
- Links to post and project details work correctly.

## 6.7 Personalized Recommendation System

### Goal
Provide personalized feeds and ranking for:
- forum posts
- projects
- C2C marketplace items
- AI reply style and suggestion priorities

### User behavior signals
The system must collect and use at least these signals:
1. Recent forum browsing (view, dwell time)
2. Forum likes
3. Project browsing and contribution behavior
4. Marketplace browsing behavior
5. AI conversation history (topics, accepted suggestions, explicit preferences)

### Recommendation logic (initial strategy)
1. Build candidates by source:
- forum: latest + relevant tags
- projects: active and not funded projects
- marketplace: available items
2. Rank with weighted score:
- `score = recency_weight + interest_match_weight + engagement_weight`
- forum `preference_match` must be clamped to `[0, 1]` before it contributes to the final score
3. Return top-N per domain (`forum`, `project`, `market`).
4. Forum ranking uses global rank-then-slice pagination:
- rank the full candidate window first
- apply deterministic merge and diversity rules
- slice the final global order by `offset` and `limit`
5. Forum exploration must require weak affinity or low recent exposure rather than mere unseen status.
6. Forum tie-breaks must be deterministic:
- newer `created_at` first
- higher `id` first
- stable source order as the final fallback

### Topic taxonomy and content mapping
1. All recommendation domains must share one unified topic taxonomy.
2. Topics are maintained in application configuration first, with a planned future migration to database-backed configuration.
3. Content authors are not required to provide keywords or topics manually.
4. Every `post`, `project`, and `market item` must be mapped to zero or more system-defined topics through this pipeline:
- normalize content inputs (title, description/content, optional image understanding result, category fields)
- run rule-based candidate recall against the fixed taxonomy
- run AI topic selection constrained to the recalled taxonomy candidates and the fixed taxonomy list
- keep only topics that pass confidence threshold
- if no topic passes threshold, assign `uncategorized`
5. The system must never freely invent new topic ids during runtime.
6. `content_topic_assignments` is a many-to-many mapping table:
- one content item may map to multiple topics
- one topic may be shared by many content items
7. `uncategorized` is a valid fallback topic and participates in ranking, exposure counting, and diversity guard logic like any other dominant topic.

### AI personalization logic
1. AI reads user preference profile before answer synthesis.
2. Preference affects recommendation priority, explanation style, and suggestion ordering.
3. AI must not fabricate preferences and should fallback to generic guidance when confidence is low.

### Preference storage model
1. `user_profiles.preferences_json` stores the compact, AI-facing summary of stable user preferences.
2. `user_preference_profiles` stores detailed machine-oriented weights for recommendation and profile computation.
3. `preferences_json` must not store raw behavior logs or noisy low-confidence inferences.
4. `preferences_json` contains two sections only:
- `content_interest_preferences`: stable topic interests for AI consumption
- `action_preferences`: stable recycling-action preferences for AI consumption
5. `action_preferences` rules:
- explicit-only fields: `max_recycling_distance_km`, `preferred_recycling_methods`, `avoid_recycling_methods`
- behavior-inferred fields allowed: `prefer_nearby_options`, `allow_manual_area_input`, `response_style`

### Preference scoring and aggregation
1. User interest is computed against mapped system topics, not raw free-text keywords.
2. Initial behavior weights are:
- `view = 1`
- `long_view = 2`
- `like = 3`
- `comment_or_reply = 4`
- `project_contribute = 5`
- `market_order = 5`
- `ai_accept = 4`
3. Recommended time decay:
- 0 to 7 days: `1.0`
- 8 to 30 days: `0.6`
- older than 30 days: `0.3`
4. Topic score formula:
- `topic_score = sum(action_weight * time_decay * topic_confidence)`
5. If one content item maps to multiple topics, user behavior on that content must be distributed across those topics according to each topic's `confidence_score`.
6. Example:
- if a post has `plastic-recycling = 0.9` and `upcycling = 0.6`, a `like = 3` event should contribute more score to `plastic-recycling` than to `upcycling`
7. Only stable, high-confidence topic interests should be promoted from `user_preference_profiles` into `preferences_json`.
8. If insufficient data exists, the user remains in cold-start mode and falls back to popularity + recency ranking.
9. Forum novelty semantics must account for `long_view` separately from a basic view:
- unseen post: novelty `1.0`
- basic view only: novelty `0.80`
- `long_view` without deeper engagement: novelty `0.65`
- liked/commented/replied post: novelty `0.55`
10. Recent exposure counting for forum exploration uses a concrete rolling window:
- count delivered forum feed items from the last 20 forum list responses or the last 7 days, whichever yields fewer impressions
- a topic is "low recent exposure" when it appears in 2 or fewer of those impressions

### Recommendation persistence flow
1. `topic_taxonomy` is the source of truth for the fixed topic list and is written only when the system initializes or topic configuration changes.
2. `content_topic_assignments` is written when a `post`, `project`, or `market item` is created or edited and topic mapping runs.
3. `user_behavior_events` is the raw event input table and is written whenever a relevant user action happens:
- forum view, like, comment, reply
- project view and contribution
- market view and order
- AI-domain actions such as accepted suggestions or explicit preference expressions
4. `user_preference_profiles` is the computed profile snapshot and is written by asynchronous aggregation jobs after meaningful behavior updates or scheduled recomputation.
5. `recommendation_logs` is written when the system actually returns recommendation results to a user.
6. AI-related behavior should be stored in `user_behavior_events` with `domain = ai`; a separate AI event table is not required in the current design.

### Acceptance criteria
- Personalized feeds are different across users with different behavior histories.
- Recommendation API returns results for all enabled domains in a single response.
- When no behavior data exists (cold start), system falls back to popularity + recency ranking.
- AI responses show preference-aware adjustments when confidence threshold is met.
- Forum ranking pages continue a single global order across pagination slices instead of re-ranking each page independently.

## 6.8 Notification Center

### Goal
Notify users when important interactions and workflow changes happen, and allow one-click navigation to related pages.

### Trigger events
The system must create notifications for at least:
1. Someone likes the user's forum post.
2. Someone comments on the user's forum post.
3. Someone comments on (replies to) the user's forum comment.
4. Someone likes the user's forum comment.
5. Order status changes for related buyer/seller orders.
6. A project joined by the user is completed.

### Notification payload requirements
Each notification must include:
1. Recipient identity (`recipient_user_id`).
2. Event metadata (`event_type`, `actor_user_id` when available).
3. Source metadata (`source_type`, `source_id`, `source_url`) for page navigation.
4. Display content (`title`, `body`).
5. Read state (`is_read`, `read_at`).

### Functional requirements
1. Provide in-app notification list with unread count.
2. Support mark-as-read and mark-all-as-read.
3. Clicking a notification opens the related page using `source_url`.
4. If source content is removed or inaccessible, show a safe fallback page with a friendly message.

### Acceptance criteria
- Notification is created within 5 seconds after supported trigger events.
- Unread count updates after read actions.
- Clicking notification routes to the correct source page.
- Users can only access their own notifications.

## 7. Data Model (Current Database Shape)

## 7.1 Users
- `users(id, username, email, password_hash, avatar_url, bio, total_carbon_amount, current_points, preferences_json, created_at)`

### `preferences_json` schema
`preferences_json` is the stable AI-facing preference summary stored on the `users` table. Recommended structure:

```json
{
  "version": 1,
  "updated_at": "2026-03-18T10:30:00Z",
  "content_interest_preferences": {
    "topics": [
      { "topic_id": "tree-planting", "score": 0.91 },
      { "topic_id": "upcycling", "score": 0.76 }
    ],
    "confidence_score": 0.84
  },
  "action_preferences": {
    "prefer_nearby_options": true,
    "allow_manual_area_input": true,
    "preferred_recycling_methods": [],
    "avoid_recycling_methods": [],
    "max_recycling_distance_km": null,
    "response_style": "concise"
  }
}
```

Rules:
- `preferences_json` is for AI consumption only.
- It stores stable summarized preferences, not raw events.
- Topic ids must come from the unified fixed taxonomy.
- `max_recycling_distance_km`, `preferred_recycling_methods`, and `avoid_recycling_methods` must only be written from explicit user input.

## 7.2 AI and ledger
- `ai_conversations(id, user_id, title, status, current_pending_action, session_context_json, last_message_at, created_at, updated_at)`
- `ai_messages(id, conversation_id, role, message_type, content_text, content_json, related_analysis_id, sequence_no, created_at)`
- `recycling_cases(id, user_id, conversation_id, origin_message_id, waste_type_predicted, confidence, estimated_weight_kg, expected_co2_saved_kg, expected_carbon_points, status, latest_audit_attempt_no, approved_analysis_id, created_at, updated_at)`
- `recycling_audit_attempts(id, recycling_case_id, user_id, conversation_id, audit_image_url, attempt_no, audit_result, auditor_confidence, audit_reason, audit_response_json, created_at)`
- `waste_analysis_records(id, user_id, conversation_id, recycling_case_id, approved_audit_attempt_id, image_url, waste_type, confidence, estimated_weight_kg, co2_saved_kg, carbon_points, raw_ai_response_json, created_at)`
- `user_memory_items(id, user_id, memory_type, memory_key, value_json, source_type, source_message_id, conversation_id, status, created_at, updated_at)`
- `ai_message_decisions(id, conversation_id, user_message_id, intent, follow_up_type, target_case_id, confidence, needs_clarification, decision_json, engine_version, created_at)`
- `transactions(id, user_id, type, points_delta, co2_delta_kg, source_type, source_id, created_at)`
- `recycling_stations(id, name, address, latitude, longitude)`

Current implementation notes:
- `ai_conversations.status` uses conversation-level workflow state such as `active`, `awaiting_location`, `completed`, and `archived`.
- `ai_conversations.current_pending_action` records the current resume requirement such as `none`, `location_permission`, or `manual_area_input`.
- `ai_messages.role` supports at least `user`, `assistant`, `tool`, and `system`.
- `ai_messages.message_type` supports at least `text`, `image`, `analysis_result`, `recycling_case`, `audit_result`, `tool_call`, `tool_result`, and `user_action`.
- `ai_messages.related_analysis_id` links a chat message to the corresponding `waste_analysis_records` row when an image analysis produces a business result.
- `transactions` is the current combined ledger and points flow table in the implemented database.
- `recycling_cases.status` uses `pending_audit`, `audit_failed`, `audit_passed`, and `cancelled`.
- `recycling_audit_attempts.audit_result` uses `passed`, `failed`, and `unclear`.
- User-uploaded AI images are stored under `data/uploads` and exposed through `/api/uploads/<path>`.
- `user_memory_items` is the source-of-truth table for manageable long-term AI memory.
- `users.preferences_json` is rebuilt from active `user_memory_items` and injected into prompt flows as a compact memory summary.
- `ai_message_decisions` is the source of truth for structured AI routing outcomes and future orchestration migration comparisons.
- Clarification responses are persisted through the same conversation history and decision records as other AI messages so replay/debug tooling can reconstruct the routing outcome.

## 7.3 Forum
- `forum_posts(id, author_id, title, content, image_urls_json, status, created_at)`
- `forum_comments(id, post_id, user_id, parent_comment_id, content, status, created_at)`
- `likes(id, user_id, target_type, target_id, created_at)` with unique constraint on `(user_id, target_type, target_id)`
- `forum_post_chunks(id, post_id, chunk_text, embedding_id)`

## 7.4 Projects
- `projects(id, creator_user_id, title, description, points_target, points_raised, status, deadline_at, created_at)`
- `project_contributions(id, project_id, user_id, points, created_at)`

## 7.5 Marketplace
- `market_items(id, seller_id, title, description, image_urls_json, price_points, status, created_at)`
- `orders(id, item_id, buyer_id, seller_id, price_points, status, created_at)`

## 7.6 Personalization and recommendation
- `user_behavior_events(id, user_id, domain, action_type, target_id, created_at)`

Current implementation note:
- the current database only persists raw behavior events.
- detailed recommendation aggregation tables remain part of the target architecture but are not yet implemented in the current schema.

## 7.7 Notifications
- `notifications(id, recipient_user_id, event_type, source_type, source_id, title, is_read, created_at)`

Current design note:
- notification storage uses the `notifications` table only.
- a separate notification event table is not required in the current scope.

## 8. API Design Standards

### 8.1 Common standards
- Base URL: `/api`
- Auth header: `Authorization: Bearer <JWT>`
- Unified response envelope:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Suggested error codes:
- `40001` invalid parameters
- `40100` unauthorized
- `40300` forbidden
- `40400` not found
- `50000` internal server error

### 8.2 Key endpoints (suggested)
- `POST /ai/analyze-image`
- `POST /ai/chat`
- `POST /ai/chat/stream`
- `POST /ai/chat/resume` (continue suspended AI flow after user location decision)
- `GET /ai/conversations`
- `GET /ai/conversations/{id}/messages`
- `GET /ai/memory`
- `POST /ai/memory`
- `PATCH /ai/memory/{id}`
- `DELETE /ai/memory/{id}`
- `POST /ai/location-context` (submit browser location or manual area for current session)
- `POST /ai/audit-recycling`
- `GET /uploads/{path}` (serve locally stored AI-uploaded images)
- `POST /ai/reply-to-post-draft`
- `GET /recommendations` (multi-domain personalized recommendations)
- `POST /recommendations/feedback` (click/like/hide feedback loop)
- `GET /notifications` (supports unread filter and pagination)
- `POST /notifications/{id}/read`
- `POST /notifications/read-all`
- `GET /forum/posts`
- `POST /forum/posts`
- `POST /forum/posts/{id}/likes`
- `DELETE /forum/posts/{id}/likes`
- `POST /forum/posts/{id}/comments`
- `POST /forum/comments/{id}/replies`
- `POST /forum/comments/{id}/likes`
- `DELETE /forum/comments/{id}/likes`
- `GET /projects`
- `POST /projects/{id}/contribute`
- `GET /projects/{id}/updates`
- `POST /projects/{id}/updates`
- `GET /ledger`
- `GET /market/items`
- `POST /market/orders`
- `POST /market/orders/{id}/ship`
- `POST /market/orders/{id}/confirm`
- `GET /users/{id}/profile`

## 9. Coding Standards

### 9.1 General
- Use semantic naming.
- Separate DTO and Entity models.
- Add timeout/retry/circuit-breaker or fallback for external calls.
- Write structured logs with `trace_id` for critical flows.

### 9.2 Flask
- Split by Blueprint per domain.
- Validate request params at route layer.
- Keep service layer HTTP-agnostic.
- Keep repository focused on data access.

### 9.3 Vue + Vite
- Organize by domain: `ai`, `forum`, `project`, `ledger`, `market`, `profile`.
- Use Pinia for shared state.
- Centralize API client and error interception.
- Keep components single-responsibility.

## 10. AI and RAG Design Details

### 10.0 Graph Agent AI engineering layer

CarbonSnap includes an optional Graph Agent path for AI engineering demos and regression testing. It must remain compatible with the normal AI assistant and must not make Neo4j required for ordinary app startup.

Feature flags:
- `AI_TRACE_ENABLED`: enables structured Agent Trace metadata.
- `AI_GRAPH_AGENT_ENABLED`: routes chat execution through the LangGraph wrapper when enabled.
- `AI_NEO4J_GRAPHRAG_ENABLED`: enables Neo4j GraphRAG retrieval when Neo4j credentials are configured.
- `AI_PROMPTOPS_SHADOW_ENABLED`: reserves a safe path for prompt comparison metadata without changing user-visible output.
- `AI_TRACE_INCLUDE_RETRIEVAL_EXCERPTS`: controls whether retrieved excerpts are included in trace metadata.

Graph Agent responsibilities:
- Route AI runs through observable graph nodes instead of opaque control flow.
- Attach trace metadata for router decisions, graph nodes, retrieval, tools, prompt versions, fallback reasons, and timing.
- Use existing CarbonSnap services as deterministic graph nodes and tools.
- Keep high-risk business writes out of automatic LLM execution.

Neo4j GraphRAG responsibilities:
- Store AI-facing recycling knowledge such as `Item`, `Material`, `DisposalMethod`, `Rule`, `Risk`, `FacilityType`, `ForumPost`, and `KnowledgeChunk`.
- Return structured graph context with `entities`, `paths`, `rules`, `risks`, `facility_types`, `knowledge_chunks`, `confidence`, and optional `fallback_reason`.
- Support repeatable seeding through `backend/scripts/seed_recycling_graph.py`.

Fallback requirement:
- If Neo4j is unavailable or `AI_NEO4J_GRAPHRAG_ENABLED=false`, normal chat, recycling analysis, memory, forum RAG, and Agent Trace should continue working.
- Trace metadata should record graph disabled or unavailable state instead of failing the whole request.

Deterministic AI tools:
- Initial tool registry entries are `search_forum`, `query_recycling_graph`, `estimate_carbon_saving`, `find_nearby_recycling_places`, `recommend_project`, and `read_user_memory`.
- High-risk actions such as recycling completion finalization, points changes, audit pass/fail, order creation, and receipt confirmation require deterministic business validation and explicit user action.

Eval Suite:
- `backend/app/services/ai/eval_suite.py` loads JSON eval cases and summarizes intent accuracy, citation coverage, guardrail hit rate, fallback behavior, and graph path coverage.
- Unit tests use a mock runner so local verification does not require paid LLM calls.
- The same case format can be reused with a live LangGraph runner for controlled smoke tests.

### 10.1 Current AI decision-engine pipeline
1. Input processing (required text + optional image)
2. Decision-context assembly from recent conversation messages, active recycling-case summaries, and current memory summary
3. LLM intent routing (`general_chat`, `recycling_analysis`, `recycling_follow_up`)
4. Conditional case resolution for recycling follow-up across multiple active cases
5. Conditional long-term memory extraction for explicit user preferences
6. Structured decision persistence in `ai_message_decisions`, including clarification branches
7. Execution dispatch into generic chat, recycling analysis, or recycling follow-up service
8. Stage 1 streaming response for non-location-dependent output when recycling flow is active
9. Session location state check (permission state + location cache validity)
10. User decision gate when nearby search is required but location is not yet available
11. Tool calling (map API)
12. Chunk-level forum retriever (FAISS Top-K plus keyword recall and guardrail filtering)
13. Optional Neo4j GraphRAG retrieval for recycling entities, graph paths, rules, risks, facilities, and knowledge chunks
14. Deterministic AI tool planning through the tool registry
15. Response synthesis with citations and source-priority rules
16. Agent Trace attachment and persistence for assistant messages
17. Completion-audit workflow for proof-photo verification
18. Post-reply long-term memory persistence

### 10.2 Memory strategy
- Short-term memory is conversation-scoped working memory.
- Short-term memory sources in the current target design are:
- recent `ai_messages` window from the current conversation only
- `ai_conversations.session_context_json`
- active `recycling_case` summaries for the current conversation
- current location decision state
- current nearby search state
- current completion-audit state
- The runtime reply path should build these inputs through a shared working-memory/context builder rather than hand-assembling prompt fragments in multiple services.
- Long-term memory is explicit user preference memory in database.
- Long-term memory source-of-truth:
- `user_memory_items`
- Long-term memory AI-facing summary:
- `users.preferences_json`
- Persistence rule: store stable preferences only, avoid sensitive data.
- Supported long-term memory categories are:
- `response_style`
- `recycling_preference`
- `topic_interest`
- `item_method_preference`
- Long-term extraction rule:
- only explicit user statements create long-term memory
- extraction is model-assisted and schema-constrained
- browsing or marketplace/forum behavior must not create long-term memory in the AI assistant flow
- Fallback extraction exists only as debug or rollback support and must not be the default runtime path.
- Chat persistence uses three layers:
- `ai_conversations` for conversation lifecycle and pause/resume state
- `ai_messages` for ordered message history, including tool and clarification messages
- `ai_message_decisions` for structured routing outcomes per user AI message
- Recycling business persistence uses three layers:
- `recycling_cases` for pending / retryable recycling tasks
- `recycling_audit_attempts` for proof-photo audit history
- `waste_analysis_records` only after audit approval, as the formal ledger-traceable outcome
- Long-term preference storage has two layers:
- `user_memory_items` for manageable source records
- `users.preferences_json` for compact AI-facing stable summary
- LangGraph orchestration should preserve the same decision contract while wrapping existing services as graph nodes. A future LangChain helper may be used for local prompt/template utilities only when it does not replace the service-layer architecture.
- The default runtime mode is `llm_first`; `shadow` and `compat` are reserved for debugging and rollback.

### 10.3 Location permission and staged response strategy
- Location permission must be requested only when map-based nearby search is needed.
- Session location state should track at least:
- `permission_state`: `unknown`, `granted`, `denied`
- `location_source`: `browser`, `manual`, or `none`
- `expires_at` for location validity
- Recommended cache policy:
- browser location cache: 30 to 120 minutes
- manual area input: current login session or up to 24 hours
- If valid location exists, AI may continue directly to nearby search without re-prompting.
- If permission was denied during the current valid session window, do not repeatedly prompt the user.
- If no valid location is available, AI should stream stage 1 output first, then emit a structured pause state and wait for user action.
- User actions after pause:
- allow browser location
- enter manual area
- skip nearby search
- Resume generation after user action through a continuation endpoint or equivalent workflow state.

### 10.4 Preference signals for AI and recommender
- Input signals: forum browsing, post likes, comment likes, comment/reply interactions, project browsing/contribution, marketplace browsing, AI conversation behavior.
- Feature freshness: prioritize recent behavior using time decay.
- Confidence gating: apply preference-aware output only when confidence score is above threshold.
- Cold start: use popularity + recency until enough behavior data is collected.
- Unified topic taxonomy must be used across `post`, `project`, and `market item`.
- Content mapping must use fixed taxonomy selection, not free-text user keywords.
- Mapping failure falls back to `uncategorized`.

### 10.5 RAG chunking strategy
- Split unit: heading-aware paragraph chunks (fallback to sentence-based splitting for long paragraphs).
- Target size: 300 to 500 tokens per chunk.
- Overlap: 50 to 80 tokens between adjacent chunks to reduce context loss.
- Metadata per chunk: `post_id`, `chunk_id`, `chunk_index`, `tags`, `section_title`, `updated_at`.
- Retrieval assembly: merge top chunks from same post when contiguous to improve readability.
- Re-index trigger: post create/edit/delete events must sync chunk and vector state.

### 10.6 Citation policy
- Any forum-based claim in AI output must include source links.
- Minimum citation fields: `title` and `url`.
- Recommended citation metadata for debugging/audit: `post_id` and `chunk_id`.
- Retrieved forum text is untrusted input and must be screened for prompt-injection patterns before it is used as answer evidence.
- Agent Trace should record used citations and blocked retrieval evidence without storing chain-of-thought.

## 11. Security and Risk Control

- Image type and size whitelist on upload.
- JWT auth and API rate limiting.
- Content moderation is disabled for now (planned for a future iteration).
- Idempotency key for points transactions.
- Permission check and audit logs on critical order actions.
- Notification access must be strictly scoped to the recipient user.
- Location data should be treated as temporary session-scoped context unless the user explicitly provides longer-lived manual area preferences.

## 12. Testing Strategy

### 12.1 Unit tests
- Points calculation, state transitions, permission guards.
- Chunk splitter correctness (size bounds, overlap bounds, deterministic output).
- Topic mapping correctness against fixed taxonomy.
- Explicit-only action preference fields are not overwritten by inferred behavior.

### 12.2 Integration tests
- AI analyze flow with model mocking.
- AI conversation history persistence and ordered replay.
- AI staged response flow with location-required pause and resume.
- AI fallback flow when location permission is denied.
- AI completion-audit retry flow with delayed ledger finalization.
- Full order flow from create to confirm.
- Project contribution and funded transition.
- Project creator can publish updates and non-creators cannot.
- Recommendation generation from mixed behavior signals.
- Content topic assignment pipeline produces valid fixed-taxonomy topics or `uncategorized`.
- AI reply personalization with high-confidence and low-confidence preference profiles.
- Forum post create/edit/delete triggers chunk re-index and retriever visibility updates.
- Post-like/post-comment/comment-on-comment/comment-like/order-state/project-complete events create correct notifications with valid source routing fields.

### 12.3 E2E tests
- Image upload -> AI suggestion -> pending recycling case -> audit pass -> ledger entry.
- Image upload -> stage 1 AI output -> user grants or denies location -> nearby strategy continues correctly.
- Reopen recycling conversation -> nearby map and completion-audit card restore correctly from persisted history.
- Project funded -> creator publishes update -> participants can read project timeline.
- Buyer order -> seller ship -> buyer confirm -> seller settlement.
- Browse/like/interact -> recommendation feed refresh -> AI reply reflects updated preferences.
- User receives notification -> opens source page via notification click -> marks as read.
- User likes post/comments/replies/likes comment -> counters update and notifications are delivered correctly.

### 12.4 Performance targets
- AI analyze API: P95 < 8s.
- Standard list APIs: P95 < 500ms.

## 13. Milestone Plan

### Milestone 1
- Auth baseline, basic forum, AI single analysis, ledger recording.

### Milestone 2
- Project crowdfunding flow, C2C order lifecycle, profile page, notification center baseline.

### Milestone 3
- RAG citations, map tool-calling, preference memory, one-click post draft.

## 14. Confirmed Decisions and Pending Item

### Confirmed decisions
1. Points conversion is fixed at `1 kg CO2 = 10 points`.
2. Relational database is MySQL.
3. Failed project refunds are fully automated.
4. Moderation is disabled for now.

### Pending decisions
1. LangChain + FAISS forum retrieval is still a target architecture item and remains to be activated in the runtime flow.

---

Maintenance rule: every requirement change must update affected sections and the changelog.


