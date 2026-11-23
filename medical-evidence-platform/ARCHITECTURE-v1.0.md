# KEE Medical V1.0 — Architecture Baseline

> Status: Draft baseline  
> Repository: `vaelephant/300-6-KEE`  
> Development branch: `feature/kee-medical-v1`

## 1. Product direction

The product remains **KEE (Knowledge Evolution Engine)**. Medical capabilities are developed as a domain extension named **KEE Medical**, not as a separate repository or a rename of KEE.

## 2. Architecture principles

1. Preserve the existing Rust KEE engine and its independent release boundary.
2. Extend the existing `medical-evidence-platform` rather than replacing it.
3. Keep medical-domain workflows in the existing Python/FastAPI service where practical.
4. Integrate KEE through an explicit adapter and versioned API contracts; do not couple medical business code to KEE internal tables.
5. Preserve provenance, evidence anchors, review decisions, and temporal history for every published knowledge assertion.
6. Do not introduce a second graph or vector database until measured requirements demonstrate that existing KEE capabilities are insufficient.

## 3. Logical layers

- **Web console:** existing medical frontend, extended for source assets, extraction, terminology, ontology, review, graph exploration, and knowledge services.
- **Medical domain services:** source ingestion, document parsing, medical extraction, terminology mapping, governance workflows, rule management, and API access.
- **KEE adapter:** maps medical entities, relations, assertions, evidence, and ontology concepts to KEE-supported contracts.
- **Knowledge engine:** existing Rust KEE capabilities for ontology, temporal knowledge, entity resolution, reasoning, conflict detection, and hybrid search.
- **Storage:** PostgreSQL for domain metadata and workflow state; KEE-managed persistence for engine data; object storage for original and derived multimodal assets.

## 4. Data model boundaries

The medical domain model must distinguish:

- **Entity:** a normalized medical concept or named entity.
- **Relation:** a typed link between entities.
- **Assertion:** a contextualized claim about entities, including qualifiers and temporal scope.
- **Evidence:** a source-specific support or refutation record with a stable locator and source version.
- **Ontology:** versioned classes, properties, constraints, and mappings.
- **Governance record:** review task, decision, reviewer, rationale, and publication state.

Do not collapse entities, assertions, and evidence into a single table or object.

## 5. Temporal and provenance requirements

Published knowledge must retain both:

- **Valid time:** when the claim applies in the clinical or source domain.
- **Transaction time:** when the platform recorded the claim.

Each assertion must be traceable to source version(s), evidence locator(s), extraction run, and review decision where applicable. Conflicting claims must remain separately inspectable; newer publication dates must not silently overwrite older claims.

## 6. Initial implementation sequence

1. Inspect and document the existing medical platform models, migrations, APIs, and frontend before changing them.
2. Define versioned contracts for Entity, Relation, Assertion, Evidence, and Ontology.
3. Add additive database migrations and tenant-aware access controls.
4. Implement a KEE adapter behind a stable service interface.
5. Add integration tests for provenance, temporal history, permissions, and round-trip mapping.
6. Deliver one end-to-end demonstration using non-identifiable public medical guideline material.

## 7. Safety and governance

This platform manages medical knowledge assets; it is not itself a diagnostic authority. Extracted claims remain pending until their configured review workflow is complete. Any clinical rule must be versioned, scoped, testable, and explicitly approved before being exposed to downstream clinical workflows.

## 8. Non-goals for the first milestone

- Rewriting the Rust KEE engine.
- Replacing the current medical backend or frontend wholesale.
- Introducing Neo4j, Milvus, or OpenSearch by default.
- Automatically publishing unreviewed clinical claims.
- Using identifiable patient data in the initial demonstration.
