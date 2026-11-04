from alembic import op
import sqlalchemy as s
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None
def upgrade():
 op.create_table('ocr_reviews',s.Column('tenant_id',s.String(128),primary_key=True),s.Column('review_id',s.String(128),primary_key=True),s.Column('anchor_id',s.String(128),nullable=False),s.Column('revision',s.Integer(),nullable=False),s.Column('decision',s.String(128),nullable=False),s.Column('reviewed_text',s.String(),nullable=False),s.Column('actor_id',s.String(128),nullable=False),s.Column('created_at',s.String(128),nullable=False),s.Column('reason',s.String(),nullable=False),s.ForeignKeyConstraint(['tenant_id','anchor_id'],['evidence_anchors.tenant_id','evidence_anchors.anchor_id'],ondelete='RESTRICT'),s.UniqueConstraint('tenant_id','anchor_id','revision'),s.CheckConstraint('revision > 0'))
def downgrade():op.drop_table('ocr_reviews')
