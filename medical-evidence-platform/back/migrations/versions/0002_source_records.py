from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('source_records',sa.Column('tenant_id',sa.String(128),primary_key=True),sa.Column('asset_version_id',sa.String(128),primary_key=True),sa.Column('payload',sa.JSON(),nullable=False),sa.ForeignKeyConstraint(['tenant_id','asset_version_id'],['asset_versions.tenant_id','asset_versions.asset_version_id'],ondelete='RESTRICT'))
def downgrade():op.drop_table('source_records')
