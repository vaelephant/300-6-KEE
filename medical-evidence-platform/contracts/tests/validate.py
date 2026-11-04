import json,pathlib,copy
from jsonschema import Draft202012Validator,FormatChecker
from referencing import Registry,Resource
R=pathlib.Path(__file__).resolve().parents[1]
schemas={p.name:json.loads(p.read_text()) for p in (R/'schemas').glob('*.json')}
registry=Registry().with_resources((n,Resource.from_contents(v)) for n,v in schemas.items())
for v in schemas.values():Draft202012Validator.check_schema(v)
def validator(n):return Draft202012Validator(schemas[n+'.schema.json'],registry=registry,format_checker=FormatChecker())
examples={p.stem:json.loads(p.read_text()) for p in (R/'examples').glob('*.json')}
for n,x in examples.items():validator(n).validate(x)
def reject(n,change):
 x=copy.deepcopy(examples[n]);change(x)
 assert list(validator(n).iter_errors(x)),n
reject('clinical-fact',lambda x:x.update(anchor_ids=[]))
reject('clinical-fact',lambda x:x['value'].update(value=86))
reject('clinical-fact',lambda x:x.update(event_time={'precision':'datetime','value':'2026-10-01'}))
reject('clinical-fact',lambda x:x.update(origin='calculated'))
reject('query-definition',lambda x:x.update(lifecycle='published'))
reject('evidence-anchor',lambda x:x['locator'].update(kind='unknown'))
reject('query-request',lambda x:x.update(tenant_id='forged'))
reject('evidence-bundle',lambda x:x.update(execution_status='no_records'))
# validate actual query parameters using the registered nested schema
Draft202012Validator(examples['query-definition']['parameter_schema']).validate(examples['query-request']['parameters'])
a=examples['asset-version'];e=examples['evidence-anchor'];f=examples['clinical-fact'];z=examples['evidence-bundle']
assert e['asset_version_id']==a['asset_version_id']
assert e['anchor_id'] in f['anchor_ids']
assert all(x['tenant_id']==a['tenant_id'] for x in (e,f,z))
assert f['scope']==a['scope']==z['scope']
assert {x['anchor_id'] for x in z['evidence']}==set(f['anchor_ids'])
print('PASS: 6 schema definitions; 6 positive examples; 8 rejection cases; registered parameters; example reference consistency')
