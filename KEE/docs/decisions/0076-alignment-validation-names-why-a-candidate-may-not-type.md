# 0076 · Alignment validation names why a candidate may not type

- **Status**: In progress 2026-11-27 · open: per-KB flag (env `KEE_ALIGNMENT_VALIDATION_V2` still process-wide), human hard-override UX, review API surfacing of `reason_codes`
- **Written**: 2026-11-27
- **Related**: [0012](0012-the-ontology-is-a-contract-not-a-suggestion.md); [0044](0044-the-ontology-is-a-view-over-what-documents-say.md) decisions 2–3; [0051](0051-a-human-phrase-decision-carries-its-materialization-work.md); [0053](0053-a-phrase-decision-records-the-inputs-it-considered.md); plan [`KEE-V0.2-ONTOLOGY-RUNTIME`](../plans/KEE-V0.2-ONTOLOGY-RUNTIME.md) OR-01; baseline [`KEE-V0.2-W0-BASELINE-AUDIT`](../plans/KEE-V0.2-W0-BASELINE-AUDIT.md)

## Problem

Under [0044](0044-the-ontology-is-a-view-over-what-documents-say.md), extraction writes the open graph and alignment produces the typed graph. Today that path is real: kind alignment, phrase alignment (`fits` through the class hierarchy), human review, and materialisation that writes typed rows only for `phrase_bindings.status = 'bound'`.

What is missing for an ontology *runtime* is a **named, machine-readable gate** at alignment time:

1. Outcomes are stored as `bound | none | undecided`. Reviewers and agents can work with that, but APIs and tests cannot speak the OR-01 contract `accepted | needs_review | rejected` without ad-hoc mapping.
2. Failure reasons are free-form strings in `votes.reason` (`no_candidates`, `too_many_candidates`, `declared_relation`, …). There is no stable enum for domain/range mismatch, disjoint types, datatype/unit conflict, stale ontology version, missing evidence, or ambiguous binding.
3. Some contract checks still land **after** a typed write (`signature_breaks` → `axiom_violations`). That is a valuable safety net; it is not the same as refusing to type a candidate with a clear code before materialisation.
4. External systems (and TrustGraph-style OntologyRAG) often put ontology into the extract prompt. KEE must not drift there: [0044](0044-the-ontology-is-a-view-over-what-documents-say.md) decision 2 stands. Validation belongs on the alignment/materialisation boundary.

Without this record, OR-01 work risks either renaming storage under every client, or bolting a parallel “TrustGraph graph” beside the ledger.

## Decisions

### 1. Keep the stored binding statuses; publish a validation decision beside them

**Do not**, in the first cut, rename `phrase_bindings.status` from `bound | none | undecided` to `accepted | needs_review | rejected`. Those three values are already wired through materialisation, the alignment queue, and human precedence ([0051](0051-a-human-phrase-decision-carries-its-materialization-work.md), [0053](0053-a-phrase-decision-records-the-inputs-it-considered.md)).

OR-01 introduces a **validation decision** (logical protocol, then code type) with:

- `decision`: `accepted | needs_review | rejected`
- `reason_codes`: stable enum list (below)
- `ontology_version` / basis fingerprint already implied by [0053](0053-a-phrase-decision-records-the-inputs-it-considered.md)
- `trace_id` when OR-02 lands; until then optional / request-scoped

Default mapping used by materialisation and APIs (must stay explicit in tests):

| Stored `phrase_bindings.status` | Validation `decision` | May materialise typed fact? |
| --- | --- | --- |
| `bound` | `accepted` | yes, if no hard `rejected` reason remains |
| `undecided` | `needs_review` | no |
| `none` | `rejected` **or** soft structural silence | no |

`none` today covers “no admissible property” and similar structural silences. Hard constraint failures (`DOMAIN_MISMATCH`, `DISJOINT_TYPE`, …) must also prevent typing; they may surface as `none`/`undecided` in storage **plus** one or more `reason_codes`, or as a dedicated field on the binding/votes JSON. The first implementation prefers **durable `reason_codes` on the decision row** over inventing a fourth status value, unless a migration proves a fourth status is clearer—then a follow-up revision of this record.

### 2. Stable reason codes (first closed set)

Implementations and tests use these strings exactly:

| Code | Meaning | Default decision |
| --- | --- | --- |
| `DOMAIN_MISMATCH` | Subject class (with ancestors) outside the property's domain | `rejected` |
| `RANGE_MISMATCH` | Object class/value outside the property's range | `rejected` |
| `DISJOINT_TYPE` | Endpoint types violate a disjointness constraint for this binding | `rejected` |
| `DATATYPE_INVALID` | Literal/value fails the declared datatype | `rejected` |
| `UNIT_CONFLICT` | Unit incompatible with the property's declared unit | `rejected` |
| `ONTOLOGY_VERSION_STALE` | Decision basis no longer matches live ontology inputs | `needs_review` (re-align; do not silently keep typed projection for agent decisions) |
| `EVIDENCE_MISSING` | Required evidence/quote/chunk link absent for typing | `needs_review` or `rejected` by policy; default `needs_review` |
| `AMBIGUOUS_BINDING` | Multiple plausible properties or disagreeing votes | `needs_review` |

Unknown or incomplete endpoint typing is **not** coded as a hard mismatch: prefer `needs_review` with an explicit note (e.g. extend with `UNKNOWN_ENDPOINT_TYPE` only if tests demand a separate code). LLM confidence alone never admits a binding.

Existing ad-hoc reasons (`no_candidates`, `too_many_candidates`, `declared_relation`, …) remain for provenance of *how* the aligner voted; new validators emit the table above. A later cut may alias old strings onto the closed set; until then both may appear, and OR-01 acceptance tests assert on the closed set.

### 3. Where validation runs

1. **Open extraction unchanged** — no ontology forced into the extract prompt ([0044](0044-the-ontology-is-a-view-over-what-documents-say.md) d2).
2. **Candidate admission** continues to use hierarchy-aware `fits` ([0053](0053-a-phrase-decision-records-the-inputs-it-considered.md)).
3. **Alignment validation** runs when a candidate would become `bound` (agent, ontology-declared, or human), and again as a guard immediately before materialisation. Human `bound` decisions still win precedence over agents, but a **hard** ontology contradiction (`DOMAIN_MISMATCH`, `RANGE_MISMATCH`, `DISJOINT_TYPE`, `DATATYPE_INVALID`, `UNIT_CONFLICT`) must not silently type: surface `needs_review` or refuse materialisation with reason codes, and keep the open statement. Exact UX for overruling a hard code is left open; silent typed write is forbidden.
4. **Post-write `signature_breaks`** stays as a second line of defence; OR-01 does not delete it. Prefer catching the same class of errors earlier with reason codes.

### 4. Open statements are never deleted by rejection

A `rejected` or `needs_review` outcome does not remove the open statement, its evidence, or its quote. Typed projection is simply not created or is retired by existing materialisation rules when support is gone.

### 5. Feature flag and scope

Ship behind `alignment_validation_v2` (name indicative; follow the deployment config convention in force). Enable per KB or workspace. With the flag off, behaviour matches today's binding statuses and materialisation. With the flag on, reason codes are populated and hard codes block typing as above.

Industry packs (e.g. HCC) must not hard-code clinical rules into the validator; only generic ontology constraints belong here.

### 6. What this record does not decide

- Unified evidence `trace_id` across retrieval and answers ([OR-02](../plans/KEE-V0.2-ONTOLOGY-RUNTIME.md)).
- Fine-grained read PDP ([OR-03](../plans/KEE-V0.2-ONTOLOGY-RUNTIME.md)).
- SPARQL, Context Package, or guided graph query (P1).
- Replacing KEE storage with an external ontology-runtime stack.
- Treating TrustGraph OntologyRAG (ontology-in-extract) as a goal — explicitly out of scope ([plan §0.1](../plans/KEE-V0.2-ONTOLOGY-RUNTIME.md)).

## Consequences

- OR-01 implementation has a fixed vocabulary and hang points: phrase alignment / decide paths and pre-materialisation guard; open extract stays untouched.
- Clients keep consuming `bound | none | undecided` until a later, explicit migration; new fields/codes are additive.
- Test oracles for hard constraints: **zero false accepts** when a hard reason code applies.
- W0 baseline remains the pre-change snapshot; this record is the decision snapshot for coding.

## Status history

- 2026-11-27: Proposed after W0 baseline audit on `d9c5ae1`; awaiting review before coding.
- 2026-11-27: In progress — `kee_reason::alignment_validation` + `kee_store::alignment_gate` pre-materialise guard behind `KEE_ALIGNMENT_VALIDATION_V2`.
- 2026-11-27: Migration 0129 adds `phrase_bindings.reason_codes` + `validation_decision`; materialise writes them when the v2 gate runs.
- 2026-11-27: Phrase alignment (agent + declared ontology binds) validates before write; hard reject → `none`, review → `undecided`, with durable codes; disagree votes get `AMBIGUOUS_BINDING`.
