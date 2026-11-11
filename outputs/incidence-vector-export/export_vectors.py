"""Deterministic, lossless export of existing SQLite vector rows."""
import csv,gzip,hashlib,io,json,sqlite3
from collections import Counter
from fractions import Fraction
from pathlib import Path

OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'persistent-progressive'/'search.sqlite'
BACKUP=SOURCE.with_name('search-backup.sqlite')
EXPECTED=1108647
D=3535316142212174320
DATA=OUT/'incidence_vectors_complete.csv.gz'
FIELDS=['vector_id','vector_identity','identity_scope','card_count','cards','card_sizes','incidence_vector',
        'support','total_incidences','maximum_number_membership','evaluation_status','zero_payout_draws',
        'winning_draws','payout_probability_exact','source','completion_zero_lower','branch_status']
QUERY="""SELECT c.*,b.status branch_status FROM config c JOIN branch b ON b.config=c.id ORDER BY c.id"""

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def connect(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    return db

def cells(row):
    zero=row['zero']
    scope='literal_fallback' if row['key'].startswith('literal:') else 'exact_canonical'
    return [row['id'],row['key'],scope,row['depth'],row['cards'],row['composition'],row['memberships'],
            row['support'],row['incidences'],row['max_owner'],row['state'],zero,row['wins'],
            None if zero is None else str(Fraction(row['wins'],D)),row['source'],row['lower'],row['branch_status']]

def write_export(db,path):
    with path.open('wb') as binary, gzip.GzipFile(fileobj=binary,filename='',mode='wb',mtime=0) as packed:
        with io.TextIOWrapper(packed,encoding='utf-8',newline='') as stream:
            w=csv.writer(stream,lineterminator='\n')
            w.writerow(FIELDS)
            for row in db.execute(QUERY):w.writerow(cells(row))

def main():
    initial=sha(SOURCE)
    with connect(SOURCE) as db,connect(BACKUP) as backup:
        db.execute('BEGIN')
        count,ids,keys,vectors=db.execute('SELECT count(*),count(DISTINCT id),count(DISTINCT key),count(DISTINCT memberships) FROM config').fetchone()
        assert count==ids==keys==vectors
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert backup.execute('SELECT count(*) FROM config').fetchone()[0]==count
        assert all(tuple(a)==tuple(b) for a,b in zip(db.execute(QUERY),backup.execute(QUERY),strict=True))
        write_export(db,DATA)
        repeat=OUT/'determinism-check.csv.gz'
        try:
            write_export(db,repeat)
            assert sha(repeat)==sha(DATA)
        finally:repeat.unlink()
        summary=Counter()
        with gzip.open(DATA,'rt',encoding='utf-8',newline='') as f:
            reader=csv.reader(f)
            assert next(reader)==FIELDS
            n=0
            previous=0
            seen=set()
            for row,line in zip(db.execute(QUERY),reader,strict=True):
                assert line==['' if v is None else str(v) for v in cells(row)]
                identity=line[1]
                assert identity not in seen and int(line[0])>previous
                previous=int(line[0])
                seen.add(identity)
                summary[int(line[3]),line[2],line[10]]+=1
                n+=1
        assert n==count
        summary_path=OUT/'incidence_vectors_summary.csv'
        with summary_path.open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f,lineterminator='\n')
            w.writerow(['card_count','identity_scope','evaluation_status','actual_rows'])
            for key,value in sorted(summary.items()):w.writerow([*key,value])
        depths={d:sum(v for (k,_,_),v in summary.items() if k==d) for d in sorted({k for k,_,_ in summary})}
        assert sha(SOURCE)==initial
        manifest=dict(requested_count=EXPECTED,actual_source_count=count,export_count=n,
                      shortfall=EXPECTED-n,claim_1108647_status='No matching source dataset located in the inspected workspace',
                      unique_stored_ids=ids,unique_stored_keys=keys,unique_original_membership_vectors=vectors,
                      exact_canonical=sum(v for (_,k,_),v in summary.items() if k=='exact_canonical'),
                      literal_fallback=sum(v for (_,k,_),v in summary.items() if k=='literal_fallback'),
                      literal_scope='Literal keys are distinct stored identities. Their global nonisomorphism has not been certified.',
                      construction_depths=depths,partial_rows=n-depths[20],completed_layout_rows=depths[20],
                      source=str(SOURCE),source_sha256=initial,backup=str(BACKUP),backup_matches_all_rows=True,
                      ordering='Ascending original SQLite config.id',draw_denominator=D,
                      identity_and_incidence='Original config.key, config.cards, config.composition and config.memberships text copied verbatim.',
                      exact_probability='Exact wins/draw denominator in lowest terms; blank if unknown.',
                      verification=dict(sqlite_integrity='ok',foreign_key_errors=0,all_fields_reconciled=True,
                                        deterministic_regeneration=True,source_unchanged=True),
                      files={DATA.name:sha(DATA),summary_path.name:sha(summary_path)})
    (OUT/'incidence_vectors_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
