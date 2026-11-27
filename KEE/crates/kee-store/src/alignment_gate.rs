//! Pre-materialisation alignment validation (0076 / OR-01).
//!
//! Pure decisions live in [`kee_reason::alignment_validation`]. This module
//! loads the KB's class hierarchy and property ends, and decides whether a
//! bound `(statement, property)` pair may type. Off unless
//! `KEE_ALIGNMENT_VALIDATION_V2` is set to a truthy value (not `0` / `false`).

use std::collections::HashMap;

use kee_reason::alignment_validation::{
    self, Candidate, Direction, PropertyShape, ValidationOutcome,
};
use sqlx::{Postgres, Transaction};
use uuid::Uuid;

use kee_core::AppResult;

/// Deploy / lab switch for OR-01. Default off preserves today's materialisation.
pub fn v2_enabled() -> bool {
    match std::env::var("KEE_ALIGNMENT_VALIDATION_V2") {
        Ok(v) => {
            let v = v.trim();
            !(v.is_empty() || v == "0" || v.eq_ignore_ascii_case("false") || v.eq_ignore_ascii_case("off"))
        }
        Err(_) => false,
    }
}

/// Ontology snapshot used for one materialise pass.
#[derive(Debug, Default)]
pub struct OntologySnap {
    pub parents: Vec<(Uuid, Uuid)>,
    pub disjoint: Vec<(Uuid, Uuid)>,
    pub domains: HashMap<Uuid, Vec<Uuid>>,
    pub ranges: HashMap<Uuid, Vec<Uuid>>,
}

/// One due pair's ends, enough to build a [`Candidate`].
#[derive(Debug, Clone)]
pub struct DueEnds {
    pub property: Uuid,
    pub direction: Direction,
    pub subject_type: Option<Uuid>,
    pub object_type: Option<Uuid>,
    pub object_is_value: bool,
    pub kind: String,
    pub datatype: Option<String>,
    pub unit: Option<String>,
    /// When set, attribute literal already failed / passed datatype+unit parsing.
    pub value_shape_ok: Option<bool>,
}

pub async fn load_ontology_snap(
    tx: &mut Transaction<'_, Postgres>,
    kb_id: Uuid,
) -> AppResult<OntologySnap> {
    let parents: Vec<(Uuid, Uuid)> = sqlx::query_as(
        "SELECT p.child_id, p.parent_id
           FROM entity_type_parents p
           JOIN entity_types c ON c.id = p.child_id
          WHERE c.kb_id = $1",
    )
    .bind(kb_id)
    .fetch_all(&mut **tx)
    .await?;

    let disjoint: Vec<(Uuid, Uuid)> = sqlx::query_as(
        "SELECT a_id, b_id FROM entity_type_disjoint WHERE kb_id = $1",
    )
    .bind(kb_id)
    .fetch_all(&mut **tx)
    .await?;

    let domain_rows: Vec<(Uuid, Uuid)> = sqlx::query_as(
        "SELECT d.relation_type_id, d.entity_type_id
           FROM relation_type_domains d
           JOIN relation_types r ON r.id = d.relation_type_id
          WHERE r.kb_id = $1",
    )
    .bind(kb_id)
    .fetch_all(&mut **tx)
    .await?;

    let range_rows: Vec<(Uuid, Uuid)> = sqlx::query_as(
        "SELECT g.relation_type_id, g.entity_type_id
           FROM relation_type_ranges g
           JOIN relation_types r ON r.id = g.relation_type_id
          WHERE r.kb_id = $1",
    )
    .bind(kb_id)
    .fetch_all(&mut **tx)
    .await?;

    let mut domains = HashMap::<Uuid, Vec<Uuid>>::new();
    for (rel, ty) in domain_rows {
        domains.entry(rel).or_default().push(ty);
    }
    let mut ranges = HashMap::<Uuid, Vec<Uuid>>::new();
    for (rel, ty) in range_rows {
        ranges.entry(rel).or_default().push(ty);
    }

    Ok(OntologySnap {
        parents,
        disjoint,
        domains,
        ranges,
    })
}

/// Run OR-01 validation for one due pair. Does not consult LLM confidence.
pub fn validate_due(ends: &DueEnds, snap: &OntologySnap) -> ValidationOutcome {
    let property = PropertyShape {
        domains: snap.domains.get(&ends.property).cloned().unwrap_or_default(),
        ranges: snap.ranges.get(&ends.property).cloned().unwrap_or_default(),
        kind: ends.kind.clone(),
        datatype: ends.datatype.clone(),
        unit: ends.unit.clone(),
    };
    let mut candidate = Candidate {
        subject_type: ends.subject_type,
        object_type: ends.object_type,
        object_is_value: ends.object_is_value,
        direction: ends.direction,
        value_datatype_ok: None,
        value_unit_ok: None,
        ontology_stale: false,
        evidence_missing: false,
        ambiguous: false,
    };
    if ends.kind == "attribute" || ends.object_is_value {
        if let Some(ok) = ends.value_shape_ok {
            candidate.value_datatype_ok = Some(ok);
            if ends.unit.is_some() {
                candidate.value_unit_ok = Some(ok);
            }
        }
    }
    alignment_validation::validate(&candidate, &property, &snap.parents, &snap.disjoint)
}

/// True when this outcome must not create a typed fact (0076).
pub fn blocks_typing(outcome: &ValidationOutcome) -> bool {
    !outcome.decision.may_materialize()
}

/// How an intended `bound` write should be stored after OR-01 validation.
#[derive(Debug, Clone)]
pub struct AlignWrite {
    pub status: &'static str,
    pub keep_binding: bool,
    pub outcome: ValidationOutcome,
}

/// Re-shape an agent/ontology intent to `bound` using the closed reason codes.
///
/// - [`Decision::Accepted`] → still `bound`
/// - [`Decision::NeedsReview`] → `undecided`, drop property (queue a person)
/// - [`Decision::Rejected`] → `none`, drop property (open statement kept)
pub fn align_write_for_bound(outcome: ValidationOutcome) -> AlignWrite {
    match outcome.decision {
        Decision::Accepted => AlignWrite {
            status: "bound",
            keep_binding: true,
            outcome,
        },
        Decision::NeedsReview => AlignWrite {
            status: "undecided",
            keep_binding: false,
            outcome,
        },
        Decision::Rejected => AlignWrite {
            status: "none",
            keep_binding: false,
            outcome,
        },
    }
}

/// Ambiguous / disagreeing votes → needs_review with [`ReasonCode::AmbiguousBinding`].
pub fn ambiguous_outcome() -> ValidationOutcome {
    ValidationOutcome {
        decision: Decision::NeedsReview,
        reasons: vec![ReasonCode::AmbiguousBinding],
    }
}

/// Build a candidate for a signature about to bind `property` in `direction`.
pub fn ends_for_signature(
    property: Uuid,
    direction: Direction,
    subject_type: Option<Uuid>,
    object_type: Option<Uuid>,
    object_is_value: bool,
    kind: &str,
    datatype: Option<String>,
    unit: Option<String>,
) -> DueEnds {
    DueEnds {
        property,
        direction,
        subject_type,
        object_type: if object_is_value { None } else { object_type },
        object_is_value,
        kind: kind.to_string(),
        datatype,
        unit,
        value_shape_ok: None,
    }
}

pub async fn load_ontology_snap_pool(pool: &sqlx::PgPool, kb_id: Uuid) -> AppResult<OntologySnap> {
    let mut tx = pool.begin().await?;
    let snap = load_ontology_snap(&mut tx, kb_id).await?;
    tx.commit().await?;
    Ok(snap)
}

pub use alignment_validation::{Decision, ReasonCode};

#[cfg(test)]
mod tests {
    use super::*;
    use kee_reason::alignment_validation::ReasonCode;

    fn id(n: u8) -> Uuid {
        Uuid::from_bytes([n, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    }

    #[test]
    fn v2_defaults_off() {
        // Do not assert global env; only the parser shape via a local check.
        let off = |v: &str| v.is_empty() || v == "0" || v.eq_ignore_ascii_case("false");
        assert!(off("0"));
        assert!(off("false"));
        assert!(!off("1"));
        assert!(!off("true"));
    }

    #[test]
    fn hard_domain_mismatch_blocks_typing() {
        let person = id(1);
        let org = id(3);
        let property = id(9);
        let snap = OntologySnap {
            parents: vec![],
            disjoint: vec![],
            domains: HashMap::from([(property, vec![org])]),
            ranges: HashMap::from([(property, vec![org])]),
        };
        let ends = DueEnds {
            property,
            direction: Direction::Forward,
            subject_type: Some(person),
            object_type: Some(org),
            object_is_value: false,
            kind: "relation".into(),
            datatype: None,
            unit: None,
            value_shape_ok: None,
        };
        let out = validate_due(&ends, &snap);
        assert_eq!(out.decision, Decision::Rejected);
        assert!(out.reasons.contains(&ReasonCode::DomainMismatch));
        assert!(blocks_typing(&out));
    }

    #[test]
    fn rejected_bound_intent_becomes_none() {
        let out = ValidationOutcome {
            decision: Decision::Rejected,
            reasons: vec![ReasonCode::DomainMismatch],
        };
        let w = align_write_for_bound(out);
        assert_eq!(w.status, "none");
        assert!(!w.keep_binding);
    }

    #[test]
    fn review_bound_intent_becomes_undecided() {
        let out = ValidationOutcome {
            decision: Decision::NeedsReview,
            reasons: vec![ReasonCode::UnknownEndpointType],
        };
        let w = align_write_for_bound(out);
        assert_eq!(w.status, "undecided");
        assert!(!w.keep_binding);
    }

    #[test]
    fn fitting_pair_does_not_block() {
        let person = id(1);
        let org = id(3);
        let property = id(9);
        let snap = OntologySnap {
            parents: vec![],
            disjoint: vec![],
            domains: HashMap::from([(property, vec![person])]),
            ranges: HashMap::from([(property, vec![org])]),
        };
        let ends = DueEnds {
            property,
            direction: Direction::Forward,
            subject_type: Some(person),
            object_type: Some(org),
            object_is_value: false,
            kind: "relation".into(),
            datatype: None,
            unit: None,
            value_shape_ok: None,
        };
        let out = validate_due(&ends, &snap);
        assert_eq!(out.decision, Decision::Accepted);
        assert!(!blocks_typing(&out));
    }
}
