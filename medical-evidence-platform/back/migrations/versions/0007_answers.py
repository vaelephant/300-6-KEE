from alembic import op
import sqlalchemy as s
revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('answer_snapshots',s.Column('tenant_id',s.String(128),primary_key=True),s.Column('answer_id',s.String(128),primary_key=True),s.Column('patient_id',s.String(128),nullable=False),s.Column('actor_id',s.String(128),nullable=False),s.Column('payload',s.JSON(),nullable=False),s.ForeignKeyConstraint(['tenant_id','patient_id'],['patients.tenant_id','patients.patient_id'],ondelete='RESTRICT'))
def downgrade():op.drop_table('answer_snapshots')
