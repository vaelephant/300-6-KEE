from alembic import op
import sqlalchemy as s
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('document_files',s.Column('tenant_id',s.String(128),primary_key=True),s.Column('asset_version_id',s.String(128),primary_key=True),s.Column('patient_id',s.String(128),nullable=False),s.Column('filename',s.String(128),nullable=False),s.Column('data',s.LargeBinary(),nullable=False),s.Column('page_count',s.Integer(),nullable=False),s.Column('status',s.String(128),nullable=False),s.ForeignKeyConstraint(['tenant_id','patient_id','asset_version_id'],['asset_versions.tenant_id','asset_versions.patient_id','asset_versions.asset_version_id'],ondelete='RESTRICT'))
 op.create_table('document_blocks',s.Column('tenant_id',s.String(128),primary_key=True),s.Column('anchor_id',s.String(128),primary_key=True),s.Column('patient_id',s.String(128),nullable=False),s.Column('asset_version_id',s.String(128),nullable=False),s.Column('page',s.Integer(),nullable=False),s.Column('text',s.String(),nullable=False),s.ForeignKeyConstraint(['tenant_id','patient_id','anchor_id'],['evidence_anchors.tenant_id','evidence_anchors.patient_id','evidence_anchors.anchor_id'],ondelete='RESTRICT'))
def downgrade():
 op.drop_table('document_blocks');op.drop_table('document_files')
