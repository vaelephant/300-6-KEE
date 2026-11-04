from alembic import op
import sqlalchemy as s
import hashlib,json
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None
def upgrade():
 t=op.create_table('document_import_keys',s.Column('tenant_id',s.String(128),primary_key=True),s.Column('import_key',s.String(128),primary_key=True),s.Column('asset_version_id',s.String(128),nullable=False),s.ForeignKeyConstraint(['tenant_id','asset_version_id'],['document_files.tenant_id','document_files.asset_version_id'],ondelete='RESTRICT'))
 # Backfill existing files; historical duplicates remain, one canonical retry target.
 c=op.get_bind();meta=s.MetaData();f=s.Table('document_files',meta,autoload_with=c);a=s.Table('asset_versions',meta,autoload_with=c);seen=set()
 for row in c.execute(s.select(f.c.tenant_id,f.c.asset_version_id,f.c.data,a.c.payload).join(a,s.and_(f.c.tenant_id==a.c.tenant_id,f.c.asset_version_id==a.c.asset_version_id)).order_by(f.c.asset_version_id)).mappings():
  scope=row['payload']['scope'];digest=hashlib.sha256(row['data']).hexdigest();key=hashlib.sha256(json.dumps([scope['patient_id'],scope['encounter_id'],digest],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  pair=(row['tenant_id'],key)
  if pair not in seen:c.execute(t.insert().values(tenant_id=pair[0],import_key=key,asset_version_id=row['asset_version_id']));seen.add(pair)
def downgrade():op.drop_table('document_import_keys')
