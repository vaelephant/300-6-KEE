//! Alignment validation (0076 / OR-01): pure decisions, no database.
//!
//! Open extraction stays ontology-free. This module answers whether a
//! candidate `(subject, predicate, object)` may become a typed fact, with
//! stable reason codes. Storage statuses (`bound` / `none` / `undecided`)
//! stay as they are; callers map via [`Decision`].

use std::collections::{HashMap, HashSet};
use uuid::Uuid;

use crate::ontology::MAX_ANCESTRY;

/// Closed set from 0076. String form is the API / test oracle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReasonCode {
    DomainMismatch,
    RangeMismatch,
    DisjointType,
    DatatypeInvalid,
    UnitConflict,
    OntologyVersionStale,
    EvidenceMissing,
    AmbiguousBinding,
    UnknownEndpointType,
}

impl ReasonCode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::DomainMismatch => "DOMAIN_MISMATCH",
            Self::RangeMismatch => "RANGE_MISMATCH",
            Self::DisjointType => "DISJOINT_TYPE",
            Self::DatatypeInvalid => "DATATYPE_INVALID",
            Self::UnitConflict => "UNIT_CONFLICT",
            Self::OntologyVersionStale => "ONTOLOGY_VERSION_STALE",
            Self::EvidenceMissing => "EVIDENCE_MISSING",
            Self::AmbiguousBinding => "AMBIGUOUS_BINDING",
            Self::UnknownEndpointType => "UNKNOWN_ENDPOINT_TYPE",
        }
    }

    pub fn is_hard(self) -> bool {
        matches!(
            self,
            Self::DomainMismatch
                | Self::RangeMismatch
                | Self::DisjointType
                | Self::DatatypeInvalid
                | Self::UnitConflict
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Decision {
    Accepted,
    NeedsReview,
    Rejected,
}

impl Decision {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Accepted => "accepted",
            Self::NeedsReview => "needs_review",
            Self::Rejected => "rejected",
        }
    }

    /// Typed materialisation is allowed only for [`Decision::Accepted`].
    pub fn may_materialize(self) -> bool {
        matches!(self, Self::Accepted)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationOutcome {
    pub decision: Decision,
    pub reasons: Vec<ReasonCode>,
}

impl ValidationOutcome {
    pub fn accepted() -> Self {
        Self {
            decision: Decision::Accepted,
            reasons: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Direction {
    Forward,
    Reverse,
}

/// Declared shape of the property under consideration.
#[derive(Debug, Clone)]
pub struct PropertyShape {
    /// Empty = unconstrained (0076 / 0053: no axiom, no verdict).
    pub domains: Vec<Uuid>,
    pub ranges: Vec<Uuid>,
    /// `relation` or `attribute` (others are rejected as not typable here).
    pub kind: String,
    pub datatype: Option<String>,
    pub unit: Option<String>,
}

/// One candidate binding to validate.
#[derive(Debug, Clone)]
pub struct Candidate {
    pub subject_type: Option<Uuid>,
    pub object_type: Option<Uuid>,
    pub object_is_value: bool,
    pub direction: Direction,
    /// For attributes: whether the literal parses as the declared datatype.
    /// `None` = not applicable (relation, or no datatype declared).
    pub value_datatype_ok: Option<bool>,
    /// For attributes with a declared unit: whether the value's unit fits.
    pub value_unit_ok: Option<bool>,
    pub ontology_stale: bool,
    pub evidence_missing: bool,
    pub ambiguous: bool,
}

/// Validate a candidate against a property and the class hierarchy.
///
/// `parents` are `(child, parent)` edges. `disjoint` pairs are already
/// expanded symmetrically by the importer (same as [`crate::ontology::check_ontology`]).
pub fn validate(
    candidate: &Candidate,
    property: &PropertyShape,
    parents: &[(Uuid, Uuid)],
    disjoint: &[(Uuid, Uuid)],
) -> ValidationOutcome {
    let mut reasons = Vec::new();
    let up = adjacency(parents);

    if candidate.ambiguous {
        reasons.push(ReasonCode::AmbiguousBinding);
    }
    if candidate.ontology_stale {
        reasons.push(ReasonCode::OntologyVersionStale);
    }
    if candidate.evidence_missing {
        reasons.push(ReasonCode::EvidenceMissing);
    }

    let (domain_end, range_end) = match candidate.direction {
        Direction::Forward => (candidate.subject_type, candidate.object_type),
        Direction::Reverse => (candidate.object_type, candidate.subject_type),
    };

    // Domain
    if !property.domains.is_empty() {
        match domain_end {
            None => reasons.push(ReasonCode::UnknownEndpointType),
            Some(t) => {
                if !admits(t, &property.domains, &up) {
                    reasons.push(ReasonCode::DomainMismatch);
                }
                if unsatisfiable_type(t, &up, disjoint) {
                    reasons.push(ReasonCode::DisjointType);
                }
            }
        }
    }

    if property.kind == "attribute" || candidate.object_is_value {
        if let Some(false) = candidate.value_datatype_ok {
            reasons.push(ReasonCode::DatatypeInvalid);
        }
        if property.unit.is_some() {
            if let Some(false) = candidate.value_unit_ok {
                reasons.push(ReasonCode::UnitConflict);
            }
        }
    } else if !property.ranges.is_empty() {
        match range_end {
            None => {
                if !reasons.contains(&ReasonCode::UnknownEndpointType) {
                    reasons.push(ReasonCode::UnknownEndpointType);
                }
            }
            Some(t) => {
                if !admits(t, &property.ranges, &up) {
                    reasons.push(ReasonCode::RangeMismatch);
                }
                if unsatisfiable_type(t, &up, disjoint)
                    && !reasons.contains(&ReasonCode::DisjointType)
                {
                    reasons.push(ReasonCode::DisjointType);
                }
            }
        }
    }

    decide(reasons)
}

fn decide(reasons: Vec<ReasonCode>) -> ValidationOutcome {
    if reasons.is_empty() {
        return ValidationOutcome::accepted();
    }
    let decision = if reasons.iter().any(|r| r.is_hard()) {
        Decision::Rejected
    } else {
        Decision::NeedsReview
    };
    ValidationOutcome { decision, reasons }
}

fn adjacency(parents: &[(Uuid, Uuid)]) -> HashMap<Uuid, Vec<Uuid>> {
    let mut up = HashMap::<Uuid, Vec<Uuid>>::new();
    for &(child, parent) in parents {
        up.entry(child).or_default().push(parent);
    }
    up
}

fn ancestors(start: Uuid, up: &HashMap<Uuid, Vec<Uuid>>) -> HashSet<Uuid> {
    let mut out = HashSet::from([start]);
    let mut stack = vec![start];
    let mut depth = 0usize;
    while let Some(cur) = stack.pop() {
        if depth >= MAX_ANCESTRY {
            break;
        }
        depth += 1;
        if let Some(parents) = up.get(&cur) {
            for &p in parents {
                if out.insert(p) {
                    stack.push(p);
                }
            }
        }
    }
    out
}

fn admits(endpoint: Uuid, declared: &[Uuid], up: &HashMap<Uuid, Vec<Uuid>>) -> bool {
    let closure = ancestors(endpoint, up);
    declared.iter().any(|d| closure.contains(d))
}

/// A type that inherits two mutually disjoint ancestors cannot hold instances (0076).
fn unsatisfiable_type(
    endpoint: Uuid,
    up: &HashMap<Uuid, Vec<Uuid>>,
    disjoint: &[(Uuid, Uuid)],
) -> bool {
    if disjoint.is_empty() {
        return false;
    }
    let pairs: HashSet<(Uuid, Uuid)> = disjoint.iter().copied().collect();
    let closure: Vec<Uuid> = ancestors(endpoint, up).into_iter().collect();
    for (i, &a) in closure.iter().enumerate() {
        for &b in &closure[i + 1..] {
            if pairs.contains(&(a, b)) || pairs.contains(&(b, a)) {
                return true;
            }
        }
    }
    false
}

/// Map a stored phrase-binding status onto the validation decision vocabulary.
pub fn decision_from_binding_status(status: &str) -> Option<Decision> {
    match status {
        "bound" => Some(Decision::Accepted),
        "undecided" => Some(Decision::NeedsReview),
        "none" => Some(Decision::Rejected),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn id(n: u8) -> Uuid {
        Uuid::from_bytes([n, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    }

    fn relation(domains: Vec<Uuid>, ranges: Vec<Uuid>) -> PropertyShape {
        PropertyShape {
            domains,
            ranges,
            kind: "relation".into(),
            datatype: None,
            unit: None,
        }
    }

    fn cand(subject: Option<Uuid>, object: Option<Uuid>) -> Candidate {
        Candidate {
            subject_type: subject,
            object_type: object,
            object_is_value: false,
            direction: Direction::Forward,
            value_datatype_ok: None,
            value_unit_ok: None,
            ontology_stale: false,
            evidence_missing: false,
            ambiguous: false,
        }
    }

    #[test]
    fn a_fitting_relation_is_accepted() {
        // person ⊂ agent; employs: agent → organization
        let person = id(1);
        let agent = id(2);
        let org = id(3);
        let parents = [(person, agent)];
        let property = relation(vec![agent], vec![org]);
        let out = validate(&cand(Some(person), Some(org)), &property, &parents, &[]);
        assert_eq!(out.decision, Decision::Accepted);
        assert!(out.reasons.is_empty());
        assert!(out.decision.may_materialize());
    }

    #[test]
    fn domain_mismatch_is_rejected_with_stable_code() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![org], vec![org]);
        let out = validate(&cand(Some(person), Some(org)), &property, &[], &[]);
        assert_eq!(out.decision, Decision::Rejected);
        assert_eq!(out.reasons, vec![ReasonCode::DomainMismatch]);
        assert_eq!(out.reasons[0].as_str(), "DOMAIN_MISMATCH");
        assert!(!out.decision.may_materialize());
    }

    #[test]
    fn range_mismatch_is_rejected() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![person], vec![org]);
        let out = validate(&cand(Some(person), Some(person)), &property, &[], &[]);
        assert_eq!(out.decision, Decision::Rejected);
        assert_eq!(out.reasons, vec![ReasonCode::RangeMismatch]);
    }

    #[test]
    fn unknown_endpoint_needs_review_not_hard_mismatch() {
        let org = id(3);
        let property = relation(vec![org], vec![org]);
        let out = validate(&cand(None, Some(org)), &property, &[], &[]);
        assert_eq!(out.decision, Decision::NeedsReview);
        assert!(out.reasons.contains(&ReasonCode::UnknownEndpointType));
        assert!(!out.reasons.iter().any(|r| r.is_hard()));
    }

    #[test]
    fn unconstrained_domain_does_not_invent_a_mismatch() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![], vec![org]);
        let out = validate(&cand(Some(person), Some(org)), &property, &[], &[]);
        assert_eq!(out.decision, Decision::Accepted);
    }

    #[test]
    fn reverse_swaps_the_ends_for_domain_and_range() {
        let person = id(1);
        let org = id(3);
        // employs: org → person in reverse means person is domain-side after swap check
        let property = relation(vec![org], vec![person]);
        let mut c = cand(Some(person), Some(org));
        c.direction = Direction::Reverse;
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::Accepted);
    }

    #[test]
    fn disjoint_endpoint_type_is_rejected() {
        // subject typed as leaf that inherits two disjoint ancestors
        let leaf = id(1);
        let a = id(2);
        let b = id(3);
        let org = id(4);
        let parents = [(leaf, a), (leaf, b)];
        let disjoint = [(a, b), (b, a)];
        let property = relation(vec![a], vec![org]);
        let out = validate(&cand(Some(leaf), Some(org)), &property, &parents, &disjoint);
        assert_eq!(out.decision, Decision::Rejected);
        assert!(out.reasons.contains(&ReasonCode::DisjointType));
    }

    #[test]
    fn invalid_datatype_is_rejected() {
        let person = id(1);
        let property = PropertyShape {
            domains: vec![person],
            ranges: vec![],
            kind: "attribute".into(),
            datatype: Some("number".into()),
            unit: None,
        };
        let mut c = cand(Some(person), None);
        c.object_is_value = true;
        c.value_datatype_ok = Some(false);
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::Rejected);
        assert_eq!(out.reasons, vec![ReasonCode::DatatypeInvalid]);
    }

    #[test]
    fn unit_conflict_is_rejected() {
        let person = id(1);
        let property = PropertyShape {
            domains: vec![person],
            ranges: vec![],
            kind: "attribute".into(),
            datatype: Some("number".into()),
            unit: Some("kg".into()),
        };
        let mut c = cand(Some(person), None);
        c.object_is_value = true;
        c.value_datatype_ok = Some(true);
        c.value_unit_ok = Some(false);
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::Rejected);
        assert_eq!(out.reasons, vec![ReasonCode::UnitConflict]);
    }

    #[test]
    fn stale_ontology_needs_review() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![person], vec![org]);
        let mut c = cand(Some(person), Some(org));
        c.ontology_stale = true;
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::NeedsReview);
        assert_eq!(out.reasons, vec![ReasonCode::OntologyVersionStale]);
    }

    #[test]
    fn missing_evidence_needs_review_by_default() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![person], vec![org]);
        let mut c = cand(Some(person), Some(org));
        c.evidence_missing = true;
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::NeedsReview);
        assert_eq!(out.reasons, vec![ReasonCode::EvidenceMissing]);
    }

    #[test]
    fn ambiguous_binding_needs_review() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![person], vec![org]);
        let mut c = cand(Some(person), Some(org));
        c.ambiguous = true;
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::NeedsReview);
        assert_eq!(out.reasons, vec![ReasonCode::AmbiguousBinding]);
    }

    #[test]
    fn hard_reason_wins_over_review_reasons() {
        let person = id(1);
        let org = id(3);
        let property = relation(vec![org], vec![org]);
        let mut c = cand(Some(person), Some(org));
        c.ontology_stale = true;
        let out = validate(&c, &property, &[], &[]);
        assert_eq!(out.decision, Decision::Rejected);
        assert!(out.reasons.contains(&ReasonCode::DomainMismatch));
        assert!(out.reasons.contains(&ReasonCode::OntologyVersionStale));
    }

    #[test]
    fn binding_status_maps_to_decision_vocabulary() {
        assert_eq!(
            decision_from_binding_status("bound"),
            Some(Decision::Accepted)
        );
        assert_eq!(
            decision_from_binding_status("undecided"),
            Some(Decision::NeedsReview)
        );
        assert_eq!(
            decision_from_binding_status("none"),
            Some(Decision::Rejected)
        );
        assert_eq!(decision_from_binding_status("wat"), None);
    }
}
