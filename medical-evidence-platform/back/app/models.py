"""V0.1 persistence models. Payloads retain the full validated contract."""
from sqlalchemy import (Column,String,Integer,JSON,MetaData,Table,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index)
from sqlalchemy.orm import registry
metadata=MetaData()
mapper_registry=registry(metadata=metadata)

def table(name,idname,extras=(),constraints=()):
    return Table(name,metadata,Column('tenant_id',String(128),primary_key=True),Column(idname,String(128),primary_key=True),*extras,*constraints)
def col(n,t=String(128),nullable=False): return Column(n,t,nullable=nullable)
def fk(local,target): return ForeignKeyConstraint(local,target,ondelete='RESTRICT')
patients=table('patients','patient_id')
encounters=table('encounters','encounter_id',[col('patient_id')],[UniqueConstraint('tenant_id','patient_id','encounter_id'),fk(['tenant_id','patient_id'],['patients.tenant_id','patients.patient_id'])])
def scope_constraints(name):return [fk(['tenant_id','patient_id'],['patients.tenant_id','patients.patient_id']),fk(['tenant_id','patient_id','encounter_id'],['encounters.tenant_id','encounters.patient_id','encounters.encounter_id'])]
assets=table('assets','asset_id',[col('patient_id'),col('encounter_id',nullable=True)],scope_constraints('assets')+[UniqueConstraint('tenant_id','patient_id','asset_id')])
asset_versions=table('asset_versions','asset_version_id',[col('patient_id'),col('asset_id'),col('version',Integer),col('payload',JSON)], [fk(['tenant_id','patient_id','asset_id'],['assets.tenant_id','assets.patient_id','assets.asset_id']),UniqueConstraint('tenant_id','asset_id','version'),UniqueConstraint('tenant_id','patient_id','asset_version_id'),CheckConstraint('version > 0')])
anchors=table('evidence_anchors','anchor_id',[col('patient_id'),col('asset_version_id'),col('payload',JSON)],[fk(['tenant_id','patient_id','asset_version_id'],['asset_versions.tenant_id','asset_versions.patient_id','asset_versions.asset_version_id']),UniqueConstraint('tenant_id','patient_id','anchor_id')])
facts=table('clinical_facts','fact_id',[col('patient_id'),col('encounter_id',nullable=True)],scope_constraints('facts')+[UniqueConstraint('tenant_id','patient_id','fact_id')])
fact_versions=table('fact_versions','fact_version_id',[col('patient_id'),col('fact_id'),col('version',Integer),col('concept_code'),col('publication_status'),col('payload',JSON)],[fk(['tenant_id','patient_id','fact_id'],['clinical_facts.tenant_id','clinical_facts.patient_id','clinical_facts.fact_id']),UniqueConstraint('tenant_id','fact_id','version'),UniqueConstraint('tenant_id','patient_id','fact_version_id'),CheckConstraint('version > 0')])
fact_evidence=Table('fact_evidence',metadata,col('tenant_id'),col('patient_id'),col('fact_version_id'),col('anchor_id'),UniqueConstraint('tenant_id','fact_version_id','anchor_id'),fk(['tenant_id','patient_id','fact_version_id'],['fact_versions.tenant_id','fact_versions.patient_id','fact_versions.fact_version_id']),fk(['tenant_id','patient_id','anchor_id'],['evidence_anchors.tenant_id','evidence_anchors.patient_id','evidence_anchors.anchor_id']))
queries=Table('query_definitions',metadata,Column('tenant_id',String(128),primary_key=True),Column('query_id',String(128),primary_key=True),Column('version',Integer,primary_key=True),col('lifecycle'),col('payload',JSON),CheckConstraint('version > 0'))
runs=table('query_runs','query_run_id',[col('patient_id'),col('query_id'),col('query_version',Integer),col('actor_id'),col('purpose'),col('snapshot_id'),col('status')],[fk(['tenant_id','patient_id'],['patients.tenant_id','patients.patient_id']),fk(['tenant_id','query_id','query_version'],['query_definitions.tenant_id','query_definitions.query_id','query_definitions.version']),UniqueConstraint('tenant_id','patient_id','query_run_id')])
bundles=table('evidence_bundles','bundle_id',[col('patient_id'),col('query_run_id'),col('payload',JSON)],[fk(['tenant_id','patient_id','query_run_id'],['query_runs.tenant_id','query_runs.patient_id','query_runs.query_run_id'])])
Index('ix_fact_patient_concept',fact_versions.c.tenant_id,fact_versions.c.patient_id,fact_versions.c.concept_code)
class Patient: pass
class Encounter: pass
class Asset: pass
class AssetVersion: pass
class EvidenceAnchor: pass
class ClinicalFact: pass
class FactVersion: pass
class QueryDefinition: pass
class QueryRun: pass
class EvidenceBundle: pass
for cls,t in [(Patient,patients),(Encounter,encounters),(Asset,assets),(AssetVersion,asset_versions),(EvidenceAnchor,anchors),(ClinicalFact,facts),(FactVersion,fact_versions),(QueryDefinition,queries),(QueryRun,runs),(EvidenceBundle,bundles)]:mapper_registry.map_imperatively(cls,t)
source_records=table('source_records','asset_version_id',[col('payload',JSON)],[fk(['tenant_id','asset_version_id'],['asset_versions.tenant_id','asset_versions.asset_version_id'])])
from sqlalchemy import LargeBinary
document_files=table('document_files','asset_version_id',[col('patient_id'),col('filename'),col('data',LargeBinary),col('page_count',Integer),col('status')],[fk(['tenant_id','patient_id','asset_version_id'],['asset_versions.tenant_id','asset_versions.patient_id','asset_versions.asset_version_id'])])
document_blocks=table('document_blocks','anchor_id',[col('patient_id'),col('asset_version_id'),col('page',Integer),col('text',String)],[fk(['tenant_id','patient_id','anchor_id'],['evidence_anchors.tenant_id','evidence_anchors.patient_id','evidence_anchors.anchor_id'])])
document_import_keys=table('document_import_keys','import_key',[col('asset_version_id')],[fk(['tenant_id','asset_version_id'],['document_files.tenant_id','document_files.asset_version_id'])])
document_ocr_runs=table('document_ocr_runs','run_id',[col('asset_version_id'),col('language'),col('engine_version'),col('status'),col('payload',JSON)],[fk(['tenant_id','asset_version_id'],['document_files.tenant_id','document_files.asset_version_id'])])
ocr_reviews=table('ocr_reviews','review_id',[col('anchor_id'),col('revision',Integer),col('decision'),col('reviewed_text',String),col('actor_id'),col('created_at'),col('reason',String)],[fk(['tenant_id','anchor_id'],['evidence_anchors.tenant_id','evidence_anchors.anchor_id']),UniqueConstraint('tenant_id','anchor_id','revision'),CheckConstraint('revision > 0')])

answer_snapshots=table('answer_snapshots','answer_id',[col('patient_id'),col('actor_id'),col('payload',JSON)],[fk(['tenant_id','patient_id'],['patients.tenant_id','patients.patient_id'])])
