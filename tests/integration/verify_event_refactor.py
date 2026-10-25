"""Lecture 05 follow-up: remove duplicated event-field mapping, keep behavior."""
from pathlib import Path
import importlib.util
import json
import hashlib
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "work" / "ad022-evidence"
ROOT.mkdir(parents=True, exist_ok=True)
SOURCE = REPO_ROOT / "src" / "backend" / "event_ingestion_prototype.py"
# Normalize checkout line endings before checking the pinned Git blob content.
_bytes = SOURCE.read_text(encoding="utf-8").encode("utf-8")
_blob = hashlib.sha1(b"blob " + str(len(_bytes)).encode() + b"\0" + _bytes).hexdigest()
if _blob != "e5697e91b933bad21694ca0b2dfa29edb1b4e185":
    raise RuntimeError("Source differs from pinned C1 (7ccec19); do not compare results silently")
source=SOURCE.read_text(encoding='utf-8')
helper='''def _event_content(event: ValidatedEvent) -> tuple[str, str, str, str, float, str]:
    """Canonical field order shared by INSERT and duplicate-content comparison."""
    return (event.device_id, event.building_id, event.measured_at,
            event.metric, event.value, event.unit)


'''
insert_before='''                (
                    event.event_id,
                    event.device_id,
                    event.building_id,
                    event.measured_at,
                    event.metric,
                    event.value,
                    event.unit,
                    received_at,
                ),'''
compare_before='''                incoming = (
                    event.device_id,
                    event.building_id,
                    event.measured_at,
                    event.metric,
                    event.value,
                    event.unit,
                )'''
assert source.count(insert_before)==1 and source.count(compare_before)==1
candidate=source.replace('class SQLiteEventRepository:',helper+'class SQLiteEventRepository:')
candidate=candidate.replace(insert_before,'                (event.event_id, *_event_content(event), received_at),')
candidate=candidate.replace(compare_before,'                incoming = _event_content(event)')
target=ROOT/'prototype_refactor_v2_candidate.py'
target.write_text(candidate,encoding='utf-8')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

tmp=Path(tempfile.mkdtemp(prefix='refactor-v2-',dir=ROOT))
signatures=[]
for name,path in [('before',SOURCE),('after',target)]:
    m=load('refactor_'+name,path)
    repo=m.SQLiteEventRepository(tmp/(name+'.sqlite3'))
    svc=m.EventIngestionService(repo)
    event=m.example_event()
    now=datetime(2026,10,25,12,tzinfo=timezone.utc)
    outcomes=[svc.ingest(event,received_at=now).status,svc.ingest(event,received_at=now).status]
    # Every field in the shared representation participates in conflict checks.
    changes={'device_id':'meter-02','building_id':'building-b','measured_at':'2026-10-25T04:00:00Z','metric':'power','value':99.0,'unit':'kW'}
    for field,value in changes.items():
        try:svc.ingest(dict(event,**{field:value}),received_at=now)
        except m.IdempotencyConflict:outcomes.append(field+':IdempotencyConflict')
        else:raise AssertionError('Missing conflict: '+field)
    # Existing numeric normalization is unchanged by extraction.
    outcomes.append(svc.ingest(dict(event,value='12.5'),received_at=now).status)
    try:svc.ingest(dict(event,event_id='bad',value=True),received_at=now)
    except m.EventValidationError:outcomes.append('EventValidationError')
    else:raise AssertionError('Invalid payload accepted')
    broken=m.EventIngestionService(m.SQLiteEventRepository(tmp/'missing'/'db.sqlite3'))
    try:broken.ingest(event,received_at=now)
    except m.EventStoreUnavailable:outcomes.append('EventStoreUnavailable')
    else:raise AssertionError('Storage failure hidden')
    c=sqlite3.connect(repo.database_path)
    rows=c.execute('SELECT * FROM readings ORDER BY event_id').fetchall();c.close()
    assert len(rows)==1
    assert rows[0]==('sample-evt-001','meter-01','building-a','2026-10-25T03:00:00.000000Z','energy',12.5,'kWh','2026-10-25T12:00:00.000000Z')
    signatures.append({'version':name,'outcomes':outcomes,'rows':rows})

assert signatures[0]['outcomes']==signatures[1]['outcomes']
assert signatures[0]['rows']==signatures[1]['rows']
result={'id':'T09-shared-mapping-extraction','status':'PASS','source_commit':'7ccec19b4f10a2e19c21e178706005f268762678','scope':'local candidate only; INSERT and conflict comparison share one canonical mapping; not pushed','signatures':signatures,'limits':'finite characterization cases, not a proof of equivalence for all inputs'}
(ROOT/'refactor_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
