BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE patients (
    tenant_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    PRIMARY KEY (tenant_id, patient_id)
);

CREATE TABLE query_definitions (
    tenant_id VARCHAR(128) NOT NULL, 
    query_id VARCHAR(128) NOT NULL, 
    version INTEGER NOT NULL, 
    lifecycle VARCHAR(128) NOT NULL, 
    payload JSON NOT NULL, 
    PRIMARY KEY (tenant_id, query_id, version), 
    CHECK (version > 0)
);

CREATE TABLE encounters (
    tenant_id VARCHAR(128) NOT NULL, 
    encounter_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    PRIMARY KEY (tenant_id, encounter_id), 
    UNIQUE (tenant_id, patient_id, encounter_id), 
    FOREIGN KEY(tenant_id, patient_id) REFERENCES patients (tenant_id, patient_id) ON DELETE RESTRICT
);

CREATE TABLE query_runs (
    tenant_id VARCHAR(128) NOT NULL, 
    query_run_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    query_id VARCHAR(128) NOT NULL, 
    query_version INTEGER NOT NULL, 
    actor_id VARCHAR(128) NOT NULL, 
    purpose VARCHAR(128) NOT NULL, 
    snapshot_id VARCHAR(128) NOT NULL, 
    status VARCHAR(128) NOT NULL, 
    PRIMARY KEY (tenant_id, query_run_id), 
    FOREIGN KEY(tenant_id, patient_id) REFERENCES patients (tenant_id, patient_id) ON DELETE RESTRICT, 
    FOREIGN KEY(tenant_id, query_id, query_version) REFERENCES query_definitions (tenant_id, query_id, version) ON DELETE RESTRICT, 
    UNIQUE (tenant_id, patient_id, query_run_id)
);

CREATE TABLE assets (
    tenant_id VARCHAR(128) NOT NULL, 
    asset_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    encounter_id VARCHAR(128), 
    PRIMARY KEY (tenant_id, asset_id), 
    FOREIGN KEY(tenant_id, patient_id) REFERENCES patients (tenant_id, patient_id) ON DELETE RESTRICT, 
    FOREIGN KEY(tenant_id, patient_id, encounter_id) REFERENCES encounters (tenant_id, patient_id, encounter_id) ON DELETE RESTRICT, 
    UNIQUE (tenant_id, patient_id, asset_id)
);

CREATE TABLE clinical_facts (
    tenant_id VARCHAR(128) NOT NULL, 
    fact_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    encounter_id VARCHAR(128), 
    PRIMARY KEY (tenant_id, fact_id), 
    FOREIGN KEY(tenant_id, patient_id) REFERENCES patients (tenant_id, patient_id) ON DELETE RESTRICT, 
    FOREIGN KEY(tenant_id, patient_id, encounter_id) REFERENCES encounters (tenant_id, patient_id, encounter_id) ON DELETE RESTRICT, 
    UNIQUE (tenant_id, patient_id, fact_id)
);

CREATE TABLE evidence_bundles (
    tenant_id VARCHAR(128) NOT NULL, 
    bundle_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    query_run_id VARCHAR(128) NOT NULL, 
    payload JSON NOT NULL, 
    PRIMARY KEY (tenant_id, bundle_id), 
    FOREIGN KEY(tenant_id, patient_id, query_run_id) REFERENCES query_runs (tenant_id, patient_id, query_run_id) ON DELETE RESTRICT
);

CREATE TABLE asset_versions (
    tenant_id VARCHAR(128) NOT NULL, 
    asset_version_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    asset_id VARCHAR(128) NOT NULL, 
    version INTEGER NOT NULL, 
    payload JSON NOT NULL, 
    PRIMARY KEY (tenant_id, asset_version_id), 
    FOREIGN KEY(tenant_id, patient_id, asset_id) REFERENCES assets (tenant_id, patient_id, asset_id) ON DELETE RESTRICT, 
    UNIQUE (tenant_id, asset_id, version), 
    UNIQUE (tenant_id, patient_id, asset_version_id), 
    CHECK (version > 0)
);

CREATE TABLE fact_versions (
    tenant_id VARCHAR(128) NOT NULL, 
    fact_version_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    fact_id VARCHAR(128) NOT NULL, 
    version INTEGER NOT NULL, 
    concept_code VARCHAR(128) NOT NULL, 
    publication_status VARCHAR(128) NOT NULL, 
    payload JSON NOT NULL, 
    PRIMARY KEY (tenant_id, fact_version_id), 
    FOREIGN KEY(tenant_id, patient_id, fact_id) REFERENCES clinical_facts (tenant_id, patient_id, fact_id) ON DELETE RESTRICT, 
    UNIQUE (tenant_id, fact_id, version), 
    UNIQUE (tenant_id, patient_id, fact_version_id), 
    CHECK (version > 0)
);

CREATE INDEX ix_fact_patient_concept ON fact_versions (tenant_id, patient_id, concept_code);

CREATE TABLE evidence_anchors (
    tenant_id VARCHAR(128) NOT NULL, 
    anchor_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    asset_version_id VARCHAR(128) NOT NULL, 
    payload JSON NOT NULL, 
    PRIMARY KEY (tenant_id, anchor_id), 
    FOREIGN KEY(tenant_id, patient_id, asset_version_id) REFERENCES asset_versions (tenant_id, patient_id, asset_version_id) ON DELETE RESTRICT, 
    UNIQUE (tenant_id, patient_id, anchor_id)
);

CREATE TABLE fact_evidence (
    tenant_id VARCHAR(128) NOT NULL, 
    patient_id VARCHAR(128) NOT NULL, 
    fact_version_id VARCHAR(128) NOT NULL, 
    anchor_id VARCHAR(128) NOT NULL, 
    UNIQUE (tenant_id, fact_version_id, anchor_id), 
    FOREIGN KEY(tenant_id, patient_id, fact_version_id) REFERENCES fact_versions (tenant_id, patient_id, fact_version_id) ON DELETE RESTRICT, 
    FOREIGN KEY(tenant_id, patient_id, anchor_id) REFERENCES evidence_anchors (tenant_id, patient_id, anchor_id) ON DELETE RESTRICT
);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

COMMIT;

