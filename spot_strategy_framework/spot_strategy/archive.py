"""Transactional authority plus immutable accepted payloads and source snapshots."""
from pathlib import Path
import sqlite3,json,hashlib,os,uuid,datetime,zipfile

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temp.open('w') as f:json.dump(data,f,sort_keys=True,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
def revision():
    root=Path(__file__).parent;files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.suffix in ('.py','.cpp')};return digest(files),files
class Archive:
    def __init__(self,path):
        self.root=Path(path);self.root.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(self.root/'research.sqlite3',isolation_level=None);self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS jobs(key TEXT PRIMARY KEY,strategy_id TEXT,status TEXT,payload TEXT,primary_data TEXT,error TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS accepted(key TEXT PRIMARY KEY,strategy_id TEXT,path TEXT,sha256 TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,config TEXT,revision TEXT,next_index INTEGER,status TEXT,counters TEXT);
        CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,track TEXT,scope TEXT,value TEXT,key TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS history(id TEXT PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS run_events(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,candidate_index INTEGER,strategy_id TEXT,status TEXT,detail TEXT);''')
    def snapshot_source(self):
        rev,files=revision();path=self.root/'revisions'/f'{rev}.zip'
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
            with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED) as z:
                for name in sorted(files):z.write(Path(__file__).parent/name,name)
            with temporary.open('rb') as f:os.fsync(f.fileno())
            try:os.link(temporary,path)
            except FileExistsError:pass
            finally:temporary.unlink(missing_ok=True)
        with zipfile.ZipFile(path) as z:
            for name,sha in files.items():
                if hashlib.sha256(z.read(name)).hexdigest()!=sha:raise ValueError('Source snapshot is incomplete.')
        manifest=path.with_suffix('.json')
        if manifest.exists() and json.loads(manifest.read_text())!={'revision':rev,'files':files}:raise ValueError('Source manifest collision.')
        if not manifest.exists():atomic_json(manifest,{'revision':rev,'files':files})
        return rev
    def job(self,key):return self.db.execute('SELECT * FROM jobs WHERE key=?',(key,)).fetchone()
    def stage(self,key,strategy_id,payload):
        self.db.execute('INSERT OR IGNORE INTO jobs VALUES(?,?,?,?,?,?,?)',(key,strategy_id,'evaluating',json.dumps(payload),None,None,stamp()))
    def primary_done(self,key,data):self.db.execute('UPDATE jobs SET status=?,primary_data=?,error=NULL WHERE key=?',('primary_done',json.dumps(data),key))
    def defer(self,key,error):self.db.execute('UPDATE jobs SET status=?,error=? WHERE key=?',('deferred',str(error),key))
    def accepted(self,key):
        row=self.db.execute('SELECT * FROM accepted WHERE key=?',(key,)).fetchone()
        if row is None:return None
        path=self.root/row['path'];raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Accepted archive integrity failure.')
        return json.loads(raw)
    def accept(self,key,result):
        if not result.get('verification',{}).get('passed'):raise ValueError('Cannot accept an unverified result.')
        from .probability import Counts
        from .model import PAYTABLE_SHA256
        counts=Counts.from_dict(result['counts']);law=counts.to_dict();law.pop('method');proof=result['verification']
        required=('full_gross_match','full_paying_count_match','full_jackpot_count_match','marginals','overlap_variance','strict_and_inclusive_thresholds')
        if not all(proof.get(x) is True for x in required) or proof.get('primary_law_sha256')!=digest(law) or proof.get('independent_law_sha256')!=digest(law):raise ValueError('Independent full-law evidence is incomplete.')
        if result['paytable_sha256']!=PAYTABLE_SHA256 or result['strategy_id']!=self.job(key)['strategy_id']:raise ValueError('Accepted-result provenance mismatch.')
        path=self.root/'accepted'/f'{key}.json';result=dict(result);result['research_timestamp']=self.job(key)['created'];raw=json.dumps(result,sort_keys=True,indent=2).encode();path.parent.mkdir(exist_ok=True)
        # A crash after this durable write leaves an orphan, never a verified DB row.
        if path.exists():
            if path.read_bytes()!=raw:raise ValueError('Immutable result collision.')
        else:
            temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
            with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            try:os.link(temporary,path)
            except FileExistsError:
                if path.read_bytes()!=raw:raise ValueError('Immutable result collision.')
            finally:temporary.unlink(missing_ok=True)
        sha=hashlib.sha256(raw).hexdigest()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT OR IGNORE INTO accepted VALUES(?,?,?,?,?)',(key,result['strategy_id'],str(path.relative_to(self.root)),sha,stamp()));self.db.execute('UPDATE jobs SET status=?,error=NULL WHERE key=?',('verified',key));self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise
        return self.accepted(key)
    def results(self):return [self.accepted(r['key']) for r in self.db.execute('SELECT key FROM accepted ORDER BY key')]
    def promote(self,track,scope,value,key):
        from fractions import Fraction as F
        result=self.accepted(key)
        if result is None:raise ValueError('Only independently accepted results can be promoted.')
        metric='frequency' if track=='jackpot_frequency' else track
        if F(result['metrics'][metric])!=F(value):raise ValueError('Promotion score differs from verified evidence.')
        if track in ('jackpot','jackpot_frequency') and F(result['metrics']['jackpot'])<=0:raise ValueError('No jackpot eligibility.')
        if scope.startswith('{'):
            constraints=json.loads(scope)
            if F(result['metrics']['frequency'])<F(constraints.get('minimum_frequency','0')):raise ValueError('Frequency guard failed.')
            if constraints.get('cards') is not None and len(result['strategy']['cards'])!=constraints['cards']:raise ValueError('Card-count scope failed.')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.db.execute('SELECT value FROM records WHERE track=? AND scope=? ORDER BY id DESC LIMIT 1',(track,scope)).fetchone()
            better=old is None or (F(value)<F(old['value']) if track=='volatility' else F(value)>F(old['value']))
            if better:self.db.execute('INSERT INTO records(track,scope,value,key,created) VALUES(?,?,?,?,?)',(track,scope,value,key,stamp()))
            self.db.execute('COMMIT');return better
        except BaseException:self.db.execute('ROLLBACK');raise
    def records(self):return [dict(r) for r in self.db.execute('SELECT * FROM records ORDER BY id')]
    def history(self,item):self.db.execute('INSERT OR IGNORE INTO history VALUES(?,?)',(digest(item),json.dumps(item,sort_keys=True)))
    def new_run(self,config):
        rid=uuid.uuid4().hex;rev=self.snapshot_source();self.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?)',(rid,json.dumps(config.to_dict(),sort_keys=True),rev,0,'running',json.dumps({'attempted':0,'duplicates':0,'verified':0,'pruned':0,'deferred':0})));return rid
    def run(self,rid):
        row=self.db.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
        if row is None:raise ValueError('Unknown run.')
        return dict(row)
    def checkpoint(self,rid,next_index,status,counters):self.db.execute('UPDATE runs SET next_index=?,status=?,counters=? WHERE id=?',(next_index,status,json.dumps(counters),rid))
    def event(self,rid,index,sid,status,detail):self.db.execute('INSERT INTO run_events(run_id,candidate_index,strategy_id,status,detail) VALUES(?,?,?,?,?)',(rid,index,sid,status,json.dumps(detail,sort_keys=True)))
    def audit(self):
        accepted=self.results();orphans=[];known={str(self.root/r['path']) for r in self.db.execute('SELECT path FROM accepted')}
        for p in (self.root/'accepted').glob('*.json'):
            if str(p) not in known:orphans.append(str(p))
        revisions=0
        for manifest in (self.root/'revisions').glob('*.json'):
            data=json.loads(manifest.read_text());rev=data['revision']
            if digest(data['files'])!=rev:raise ValueError('Source revision manifest changed.')
            with zipfile.ZipFile(manifest.with_suffix('.zip')) as z:
                for name,sha in data['files'].items():
                    if hashlib.sha256(z.read(name)).hexdigest()!=sha:raise ValueError('Source snapshot integrity failure.')
            revisions+=1
        return {'passed':True,'source_revisions_checked':revisions,'accepted_records_checked':len(accepted),'uncommitted_orphans_not_advertised_as_verified':orphans}

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
