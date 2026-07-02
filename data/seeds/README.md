# Example Data Seeds

This directory stores repeatable example data that can be imported into the
database.

The goal is to keep demo data structured, readable, and easy to maintain
without hard-coding records in Python.

## Directory Rules

- Each database table gets a folder with the same name as the table.
- Every table folder must contain a `template.json`.
- `template.json` is only a format example. It is never imported.
- Every other `.json` file in the folder is treated as a real seed record.
- File names should be descriptive, such as
  `plastic-bottle-diy-post.json` or `recycled-paper-notebook.json`.

Recommended structure:

```text
data/seeds/
  README.md
  users/
    template.json
    demo-seller.json
    demo-buyer.json
  forum_posts/
    template.json
    plastic-bottle-diy-post.json
  forum_post_chunks/
    template.json
    plastic-bottle-diy-post-chunk-v01-i00.json
  content_topic_assignments/
    template.json
    forum-plastic-bottle-diy-post-upcycling.json
  ai_conversations/
    template.json
    oriental-leaf-jasmine-bottle-chat.json
  ai_messages/
    template.json
    oriental-leaf-bottle-user-analysis.json
  recycling_cases/
    template.json
    oriental-leaf-jasmine-bottle-case.json
  recycling_audit_attempts/
    template.json
    oriental-leaf-jasmine-bottle-audit-pass.json
  waste_analysis_records/
    template.json
    oriental-leaf-jasmine-bottle-record.json
  ai_message_decisions/
    template.json
    oriental-leaf-bottle-analysis-decision.json
  transactions/
    template.json
    oriental-leaf-jasmine-bottle-earn.json
  market_items/
    template.json
    recycled-paper-notebook.json
  projects/
    template.json
    neighborhood-cleanup-starter-kit.json
```

## Seed File Format

Each seed JSON file can contain:

1. Real table fields that should be written to the database
2. Helper fields used only by the seed script

### Helper Fields

- `_seed_key`
  - Required
  - Unique identifier for this record inside the seed system
  - Not written to the database
- `_notes`
  - Optional
  - Human-readable notes
  - Not written to the database
- `*_ref`
  - Optional
  - Used for foreign-key references
  - Automatically resolved into the matching `*_id`

## Foreign-Key References

Do not hard-code database IDs in seed data.

Use this format instead:

```json
"author_ref": "users.demo-seller"
```

Meaning:

- `users` is the referenced table
- `demo-seller` is the `_seed_key` of the referenced record

When the seed script runs, it resolves that reference to the real inserted ID.

## Example Files

### `users/template.json`

```json
{
  "_seed_key": "example-user",
  "_notes": "Template only. Copy this file and rename it.",
  "username": "example_user",
  "email": "example@example.com",
  "password_hash": "replace-with-real-hash",
  "avatar_url": null,
  "bio": "Example bio",
  "total_carbon_amount": 0,
  "current_points": 0,
  "preferences_json": null,
  "created_at": "2026-03-29T09:00:00+08:00"
}
```

### `users/demo-seller.json`

```json
{
  "_seed_key": "demo-seller",
  "_notes": "Password: demo123",
  "username": "demo_seller",
  "email": "seller@example.com",
  "password_hash": "replace-with-real-hash",
  "avatar_url": null,
  "bio": "Example seller account",
  "total_carbon_amount": 12.5,
  "current_points": 300,
  "preferences_json": null,
  "created_at": "2026-03-29T09:10:00+08:00"
}
```

### `forum_posts/template.json`

```json
{
  "_seed_key": "example-post",
  "_notes": "Template only. Copy this file and rename it.",
  "author_ref": "users.demo-community-guide",
  "title": "Example post title",
  "content": "Example post content",
  "image_urls_json": null,
  "status": "published",
  "created_at": "2026-03-29T10:00:00+08:00"
}
```

### `forum_posts/plastic-bottle-diy-post.json`

```json
{
  "_seed_key": "plastic-bottle-diy-post",
  "author_ref": "users.demo-diy-maker",
  "title": "National Day DIY Lantern from a Plastic Bottle",
  "content": "A rich, social-style post body goes here.",
  "image_urls_json": null,
  "status": "published",
  "created_at": "2026-03-29T10:05:00+08:00"
}
```

### `projects/template.json`

```json
{
  "_seed_key": "example-project",
  "_notes": "Template only. Copy this file and rename it.",
  "creator_user_ref": "users.demo-community-guide",
  "title": "Example community project",
  "description": "Example project description",
  "points_target": 500,
  "points_raised": 120,
  "status": "fundraising",
  "deadline_at": "2026-04-20T20:00:00+08:00",
  "created_at": "2026-03-29T12:00:00+08:00"
}
```

### `projects/neighborhood-cleanup-starter-kit.json`

```json
{
  "_seed_key": "neighborhood-cleanup-starter-kit",
  "creator_user_ref": "users.demo-community-guide",
  "title": "Neighborhood cleanup starter kit for the riverside path",
  "description": "Funding gloves, sorting signs, and collection bags for a one-month weekend cleanup series.",
  "points_target": 450,
  "points_raised": 180,
  "status": "fundraising",
  "deadline_at": "2026-04-20T20:00:00+08:00",
  "created_at": "2026-03-29T12:10:00+08:00"
}
```

## Seed Script Behavior

The example data seed script is:

`backend/scripts/seed_example_data.py`

It does the following:

1. Clears a fixed set of application tables
2. Reads `data/seeds/`
3. Skips every `template.json`
4. Imports all other `.json` files
5. Records `_seed_key -> inserted database id`
6. Resolves all `*_ref` fields into real `*_id` values
7. Imports any seeded `content_topic_assignments` rows directly

`content_topic_assignments` can also be seeded directly. When those seed files are present,
the example-data seed script trusts them and does not re-run topic classification with the LLM.

AI-related example seeds may reference uploaded files through `/api/uploads/...`.
Keep the source image files under `data/seeds/assets/`.
The example-data seed script restores upload assets back into `data/uploads/` and forum RAG assets back into `data/faiss/` before inserting rows so they survive `backend/scripts/reset_all_data.py`.

Forum RAG chunk rows are stored in:

`data/seeds/forum_post_chunks/`

The paired vector-index assets are stored in:

`data/seeds/assets/faiss/`

## AI-Only Seed Script

If you only want to reset and import the AI demo content, use:

`backend/scripts/seed_ai_example_data.py`

It does the following:

1. Clears AI-related tables only
2. Clears ledger rows whose `source_type` is `waste_analysis`
3. Keeps forum, market, project, and other non-AI tables untouched
4. Syncs only the user seed records referenced by the AI seeds
5. Restores AI seed upload assets
6. Imports only AI-related seed folders and recalculates user balances

## Exporting A Real AI Conversation Back Into Seeds

To export a real persisted AI conversation as seed files, use:

`backend/scripts/export_ai_conversation_to_seed.py`

Example:

```text
backend\.venv\Scripts\python.exe backend\scripts\export_ai_conversation_to_seed.py ^
  --conversation-id 2 ^
  --conversation-seed-key plastic-bottle-real-chat ^
  --user-seed-key demo-ai-recycler ^
  --replace-existing
```

Recommended workflow:

1. Run the real AI conversation you want to keep.
2. Export it with `export_ai_conversation_to_seed.py`.
3. Run `backend/scripts/reset_all_data.py`.
4. Run `backend/scripts/seed_example_data.py`.

## Exporting Forum RAG Chunks And FAISS Assets

If you want forum retrieval to seed instantly without re-running embeddings, export the current
`forum_post_chunks` rows and `data/faiss/*` files into seeds with:

`backend/scripts/export_forum_rag_to_seed.py`

Example:

```text
backend\.venv\Scripts\python.exe backend\scripts\export_forum_rag_to_seed.py --replace-existing
```

After that, your normal reset flow can stay exactly the same:

1. Run `backend/scripts/reset_all_data.py`.
2. Run `backend/scripts/seed_example_data.py`.

The seed script will now restore the exported forum chunks and FAISS assets directly, and will not
rebuild the forum index during seeding.

## Exporting Content Topic Assignments

If you also want to avoid re-running topic classification for forum posts, market items, and
projects during seeding, export the current `content_topic_assignments` rows with:

`backend/scripts/export_content_topic_assignments_to_seed.py`

Example:

```text
backend\.venv\Scripts\python.exe backend\scripts\export_content_topic_assignments_to_seed.py --replace-existing
```

After exporting these files, `backend/scripts/seed_example_data.py` will import them directly and
will no longer call the LLM-based topic assignment refresh during seeding.

## Full Reset Script

The full database reset script is:

`backend/scripts/reset_all_data.py`

It does the following:

1. Clears all application table data except `alembic_version`
2. Deletes everything under `data/uploads`
3. Deletes everything under `data/faiss` except `.gitkeep`
4. Recreates `.gitkeep` files if needed

## Current Conventions

The most important rules are:

1. Table name = folder name
2. Every folder must contain `template.json`
3. Every real seed record must have `_seed_key`
4. Foreign keys should use `*_ref`, not hard-coded `*_id`
