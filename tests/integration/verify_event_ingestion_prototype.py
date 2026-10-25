import concurrent.futures as cf
import contextlib
import importlib.util
import json
import hashlib
import math
import platform
import sqlite3
import statistics
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "work" / "ad022-evidence"
ROOT.mkdir(parents=True, exist_ok=True)
SOURCE = REPO_ROOT / "src" / "backend" / "event_ingestion_prototype.py"
# Normalize checkout line endings before checking the pinned Git blob content.
_bytes = SOURCE.read_text(encoding="utf-8").encode("utf-8")
_blob = hashlib.sha1(b"blob " + str(len(_bytes)).encode() + b"\0" + _bytes).hexdigest()
if _blob != "e5697e91b933bad21694ca0b2dfa29edb1b4e185":
    raise RuntimeError("Source differs from pinned C1 (7ccec19); do not compare results silently")
spec = importlib.util.spec_from_file_location('prototype', SOURCE)
p = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = p
spec.loader.exec_module(p)
results = {'python': platform.python_version(), 'platform': platform.platform(), 'sqlite': sqlite3.sqlite_version, 'source_commit': '7ccec19b4f10a2e19c21e178706005f268762678', 'checks': [], 'observations': []}

def rowcount(path):
    with sqlite3.connect(path) as c:
        return c.execute('SELECT COUNT(*) FROM readings').fetchone()[0]

def check(name, fn):
    started = time.perf_counter()
    try:
        detail = fn()
        results['checks'].append({'id': name, 'status': 'PASS', 'detail': detail, 'seconds': round(time.perf_counter()-started, 4)})
    except Exception as e:
        results['checks'].append({'id': name, 'status': 'FAIL', 'error': repr(e)})

with contextlib.nullcontext(tempfile.mkdtemp(prefix='ad022-', dir=ROOT)) as td:
    root = Path(td)
    def service(name, **kw):
        r = p.SQLiteEventRepository(root / (name+'.sqlite3'))
        r.initialize()
        return p.EventIngestionService(r, **kw)

    def duplicate():
        s = service('duplicate')
        e = p.example_event()
        assert s.ingest(e).status == 'accepted'
        r = p.SQLiteEventRepository(s.repository.database_path)
        assert p.EventIngestionService(r).ingest(e).status == 'duplicate'
        assert rowcount(r.database_path) == 1
        altered = dict(e, value=99)
        try:
            s.ingest(altered)
        except p.IdempotencyConflict:
            pass
        else:
            raise AssertionError('conflicting event ID was not rejected')
        return 'accepted -> new instance duplicate; conflicting payload rejected; 1 row'
    check('T01-idempotency', duplicate)

    def invalid():
        s = service('invalid')
        values = [dict(p.example_event(), value=True), dict(p.example_event(), value=float('nan')), dict(p.example_event(), measured_at='2026-10-25T03:00:00'), dict(p.example_event(), event_id='')]
        for e in values:
            try:
                s.ingest(e)
            except p.EventValidationError:
                pass
            else:
                raise AssertionError('invalid event accepted')
        assert rowcount(s.repository.database_path) == 0
        return '4 invalid payloads rejected; 0 rows'
    check('T02-validation', invalid)

    def rollback():
        s = service('rollback')
        try:
            with s.repository._transaction() as c:
                c.execute("INSERT INTO readings VALUES ('x','d','b','2026-10-25T00:00:00.000000Z','energy',1,'kWh','2026-10-25T00:00:00.000000Z')")
                raise RuntimeError('injected failure before commit')
        except RuntimeError:
            pass
        assert rowcount(s.repository.database_path) == 0
        return 'failure after INSERT before commit rolled back; 0 rows'
    check('T03-transaction', rollback)

    def locked_retry(recover):
        s = service('retry-recover' if recover else 'retry-exhaust')
        ready, release = threading.Event(), threading.Event()
        def hold():
            c = sqlite3.connect(s.repository.database_path)
            c.execute('BEGIN EXCLUSIVE')
            ready.set()
            release.wait(5)
            c.rollback()
            c.close()
        holder = threading.Thread(target=hold)
        holder.start()
        assert ready.wait(3)
        timer = threading.Timer(0.18, release.set) if recover else None
        if timer:
            timer.start()
        start = time.perf_counter()
        try:
            try:
                result = s.ingest(p.example_event())
            except p.EventStoreUnavailable:
                if recover:
                    raise
                result = None
            else:
                assert recover and result.status == 'accepted'
        finally:
            release.set()
            holder.join()
            if timer:
                timer.join()
        elapsed = time.perf_counter()-start
        assert rowcount(s.repository.database_path) == (1 if recover else 0)
        return {'recovered': recover, 'elapsed_seconds': round(elapsed, 4), 'rows': rowcount(s.repository.database_path)}
    check('T04-lock-recovery', lambda: locked_retry(True))
    check('T05-lock-exhaustion', lambda: locked_retry(False))

    def retention():
        s = service('retention')
        now = datetime(2026,10,25,12,tzinfo=timezone.utc)
        cutoff = now-timedelta(days=28)
        for i, offset in enumerate([-1,0,1]):
            s.ingest(dict(p.example_event(), event_id='cutoff-'+str(i), measured_at=(cutoff+timedelta(microseconds=offset)).isoformat()))
        deleted = s.purge_expired(now=now)
        assert deleted == 1 and rowcount(s.repository.database_path) == 2
        return 'older by 1 microsecond deleted; exact boundary and newer retained'
    check('T06-retention-boundary', retention)

    def recovery():
        s = service('restore')
        events = [dict(p.example_event(), event_id='replay-'+str(i), value=10+i) for i in range(3)]
        s.ingest(events[0])
        snap_path = root/'snapshot.sqlite3'
        a=sqlite3.connect(s.repository.database_path); b=sqlite3.connect(snap_path)
        a.backup(b); a.close(); b.close()
        journal=root/'buffer.jsonl'
        journal.write_text('\n'.join(json.dumps(e) for e in events), encoding='utf-8')
        for e in events[1:]: s.ingest(e)
        with sqlite3.connect(s.repository.database_path) as c:
            c.execute('UPDATE readings SET value=999')
        t=time.perf_counter()
        a=sqlite3.connect(snap_path); b=sqlite3.connect(s.repository.database_path)
        a.backup(b); a.close(); b.close()
        statuses=[s.ingest(json.loads(line)).status for line in journal.read_text().splitlines()]
        with sqlite3.connect(s.repository.database_path) as c:
            got=c.execute('SELECT event_id,value FROM readings ORDER BY event_id').fetchall()
        assert got == [('replay-0',10.0),('replay-1',11.0),('replay-2',12.0)]
        assert statuses == ['duplicate','accepted','accepted']
        return {'rows':got,'replay_status':statuses,'restore_replay_seconds':round(time.perf_counter()-t,4),'scope':'harness-only snapshot + JSONL; not production feature'}
    check('T07-restore-replay-demo', recovery)

    # Characterize a safe extraction on a separate local copy; do not change the pinned source.
    def refactor_equivalence():
        original=SOURCE.read_text(encoding='utf-8')
        helper='''def event_content(event):
    return (event.device_id, event.building_id, event.measured_at,
            event.metric, event.value, event.unit)


'''
        altered=original.replace('class SQLiteEventRepository:',helper+'class SQLiteEventRepository:')
        old='''                incoming = (
                    event.device_id,
                    event.building_id,
                    event.measured_at,
                    event.metric,
                    event.value,
                    event.unit,
                )'''
        assert old in altered
        altered=altered.replace(old,'                incoming = event_content(event)')
        target=ROOT/'prototype_refactor_candidate.py'; target.write_text(altered,encoding='utf-8')
        ms=importlib.util.spec_from_file_location('candidate',target)
        mod=importlib.util.module_from_spec(ms);sys.modules[ms.name]=mod;ms.loader.exec_module(mod)
        signatures=[]
        for i, module in enumerate([p,mod]):
            repo=module.SQLiteEventRepository(root/f'equivalence-{i}.sqlite3')
            svc=module.EventIngestionService(repo)
            e=module.example_event()
            sig=[svc.ingest(e).status,svc.ingest(e).status]
            try:svc.ingest(dict(e,value=88))
            except Exception as ex:sig.append(type(ex).__name__)
            sig.append(rowcount(repo.database_path))
            signatures.append(sig)
        assert signatures[0]==signatures[1]
        return {'before':signatures[0],'after':signatures[1],'candidate':'local only; not pushed'}
    check('T08-small-refactor-equivalence', refactor_equivalence)

    # Real current-code limitations: reproduce without describing them as successes.
    s=service('stale')
    old=dict(p.example_event(),measured_at='2026-08-01T00:00:00Z')
    s.ingest(old);s.purge_expired(now=datetime(2026,10,25,tzinfo=timezone.utc))
    status=s.ingest(old).status
    results['observations'].append({'id':'F01-stale-replay','actual':status,'rows_after_replay':rowcount(s.repository.database_path),'impact':'expired event can be reinserted after purge; no age admission rule'})
    fresh=p.EventIngestionService(p.SQLiteEventRepository(root/'uninitialized.sqlite3'))
    try:fresh.purge_expired()
    except Exception as ex:
        results['observations'].append({'id':'F02-error-taxonomy','actual_exception':type(ex).__name__,'message':str(ex),'impact':'purge emits raw OperationalError instead of service-level typed error'})

    # Optional fast execution verifies functional behavior without repeating load.
    if '--functional-only' in sys.argv:
        results['burst_291'] = {'status': 'NOT_RUN', 'reason': '--functional-only'}
    else:
        # One simultaneous burst, not an application/API or sustained-user benchmark.
        s=service('burst')
        barrier=threading.Barrier(291)
        def send(i):
            event=dict(p.example_event(),event_id=f'load-{i}')
            barrier.wait(timeout=20)
            started=time.perf_counter()
            try:
                status=s.ingest(event).status
            except Exception as ex:
                status=type(ex).__name__
            return {'status':status,'seconds':time.perf_counter()-started}
        with cf.ThreadPoolExecutor(max_workers=291) as pool:
            burst=list(pool.map(send,range(291)))
        def p95(values):
            return round(sorted(values)[math.ceil(len(values)*0.95)-1],4) if values else None
        ok=[r for r in burst if r['status']=='accepted']
        results['burst_291']={'submitted':291,'threads':291,'accepted':len(ok),'errors':291-len(ok),'p95_all_terminal_seconds':p95([r['seconds'] for r in burst]),'p95_success_seconds':p95([r['seconds'] for r in ok]),'status_counts':{k:sum(r['status']==k for r in burst) for k in set(r['status'] for r in burst)},'rows':rowcount(s.repository.database_path),'scope':'single local burst; no MQTT, HTTP, network, dashboard or sustained workload; terminal timing excludes barrier wait'}

(ROOT/'verification_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
if any(r['status']=='FAIL' for r in results['checks']):
    raise SystemExit(1)
