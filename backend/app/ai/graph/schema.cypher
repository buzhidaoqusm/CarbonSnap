// CarbonSnap optional Neo4j GraphRAG schema.
// Apply with: python backend/scripts/seed_recycling_graph.py
//
// Vector indexes are intentionally left out until embedding dimensions and
// provider are fixed. Full-text indexes support the first deterministic graph
// lookup path without requiring embeddings.

CREATE CONSTRAINT item_name_unique IF NOT EXISTS
FOR (item:Item)
REQUIRE item.name IS UNIQUE;

CREATE CONSTRAINT material_name_unique IF NOT EXISTS
FOR (material:Material)
REQUIRE material.name IS UNIQUE;

CREATE CONSTRAINT disposal_method_name_unique IF NOT EXISTS
FOR (method:DisposalMethod)
REQUIRE method.name IS UNIQUE;

CREATE CONSTRAINT rule_id_unique IF NOT EXISTS
FOR (rule:Rule)
REQUIRE rule.id IS UNIQUE;

CREATE CONSTRAINT risk_name_unique IF NOT EXISTS
FOR (risk:Risk)
REQUIRE risk.name IS UNIQUE;

CREATE CONSTRAINT facility_type_name_unique IF NOT EXISTS
FOR (facility:FacilityType)
REQUIRE facility.name IS UNIQUE;

CREATE CONSTRAINT forum_post_id_unique IF NOT EXISTS
FOR (post:ForumPost)
REQUIRE post.post_id IS UNIQUE;

CREATE CONSTRAINT knowledge_chunk_id_unique IF NOT EXISTS
FOR (chunk:KnowledgeChunk)
REQUIRE chunk.id IS UNIQUE;

CREATE CONSTRAINT open_entity_key_unique IF NOT EXISTS
FOR (entity:Entity)
REQUIRE entity.normalized_name IS UNIQUE;

CREATE CONSTRAINT relation_type_key_unique IF NOT EXISTS
FOR (relation:RelationType)
REQUIRE relation.key IS UNIQUE;

CREATE CONSTRAINT relation_fact_id_unique IF NOT EXISTS
FOR (fact:RelationFact)
REQUIRE fact.id IS UNIQUE;

CREATE CONSTRAINT claim_id_unique IF NOT EXISTS
FOR (claim:Claim)
REQUIRE claim.id IS UNIQUE;

CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
FOR (evidence:Evidence)
REQUIRE evidence.id IS UNIQUE;

CREATE FULLTEXT INDEX item_alias_fulltext IF NOT EXISTS
FOR (item:Item)
ON EACH [item.name, item.aliases, item.description];

CREATE FULLTEXT INDEX recycling_rule_fulltext IF NOT EXISTS
FOR (rule:Rule)
ON EACH [rule.title, rule.description, rule.locality];

CREATE FULLTEXT INDEX knowledge_chunk_fulltext IF NOT EXISTS
FOR (chunk:KnowledgeChunk)
ON EACH [chunk.title, chunk.text, chunk.source];

CREATE FULLTEXT INDEX open_entity_fulltext IF NOT EXISTS
FOR (entity:Entity)
ON EACH [entity.display_name, entity.normalized_name, entity.entity_type];

CREATE FULLTEXT INDEX relation_fact_fulltext IF NOT EXISTS
FOR (fact:RelationFact)
ON EACH [fact.id, fact.subject_key, fact.relation_key, fact.object_key];

CREATE INDEX item_category_index IF NOT EXISTS
FOR (item:Item)
ON (item.category);

CREATE INDEX material_category_index IF NOT EXISTS
FOR (material:Material)
ON (material.category);

CREATE INDEX rule_locality_index IF NOT EXISTS
FOR (rule:Rule)
ON (rule.locality);

CREATE INDEX evidence_post_id_index IF NOT EXISTS
FOR (evidence:Evidence)
ON (evidence.post_id);
