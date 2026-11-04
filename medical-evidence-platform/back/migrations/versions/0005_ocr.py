from alembic import op
import sqlalchemy as s
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('document_ocr_runs',s.Column('tenant_id',s.String(128),primary_key=True),s.Column('run_id',s.String(128),primary_key=True),s.Column('asset_version_id',s.String(128),nullable=False),s.Column('language',s.String(128),nullable=False),s.Column('engine_version',s.String(128),nullable=False),s.Column('status',s.String(128),nullable=False),s.Column('payload',s.JSON(),nullable=False),s.ForeignKeyConstraint(['tenant_id','asset_version_id'],['document_files.tenant_id','document_files.asset_version_id'],ondelete='RESTRICT'))
def downgrade():op.drop_table('document_ocr_runs')
