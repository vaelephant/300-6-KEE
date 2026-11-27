-- 0076 / OR-01：对齐期本体校验按库开关。
--
-- 缺省关：与今日物化 / 绑定状态行为一致。打开后，phrase alignment 与 materialise
-- 写入 reason_codes / validation_decision，硬约束阻止入账。
-- 进程级 KEE_ALIGNMENT_VALIDATION_V2 仍可作为实验室强制打开（任意库都开）。
ALTER TABLE knowledge_bases
    ADD COLUMN alignment_validation_v2 BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN knowledge_bases.alignment_validation_v2 IS
    'OR-01 / 0076: run alignment validation and persist reason_codes for this KB';
