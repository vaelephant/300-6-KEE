from app.models.knowledge import KnowledgeObject, Evidence
from app.services.trust import trust_service

def test_trust_score_is_bounded_and_explained():
    obj = KnowledgeObject(content="A verified clinical claim", source="Official Guideline", confidence=.9, evidence=[Evidence(source="Guideline", excerpt="Evidence excerpt")])
    out = trust_service.evaluate(obj)
    assert 0 <= out["trust_score"] <= 1
    assert set(out["factors"]) == {"source_authority","evidence_strength","freshness","consistency","usage_feedback","human_verification"}
    assert out["trust_level"] in {"high","medium","guarded","low"}

def test_review_required_reduces_consistency():
    active = KnowledgeObject(content="x", source="Official Guideline", status="active", confidence=.8)
    review = KnowledgeObject(content="x", source="Official Guideline", status="review_required", confidence=.8)
    assert trust_service.evaluate(review)["factors"]["consistency"] < trust_service.evaluate(active)["factors"]["consistency"]
