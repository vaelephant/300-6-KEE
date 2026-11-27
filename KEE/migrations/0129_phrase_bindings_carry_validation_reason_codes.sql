-- 0076 / OR-01：对齐校验的稳定 reason_codes 落在绑定行上。
-- 不改 status 词汇（仍 bound|none|undecided）；validation_decision 是旁路枚举，
-- 物化前守卫与后续对齐器共用。空数组 / NULL = 尚未跑过 v2 校验。

ALTER TABLE phrase_bindings
    ADD COLUMN IF NOT EXISTS reason_codes TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS validation_decision TEXT
        CHECK (
            validation_decision IS NULL
            OR validation_decision IN ('accepted', 'needs_review', 'rejected')
        );

COMMENT ON COLUMN phrase_bindings.reason_codes IS
    'OR-01 closed reason codes (DOMAIN_MISMATCH, …); empty until alignment_validation_v2 writes';
COMMENT ON COLUMN phrase_bindings.validation_decision IS
    'OR-01 decision accepted|needs_review|rejected; NULL if v2 has not recorded an outcome';
