"""Build a deterministic source-only candidate archive from the reviewed allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'publication-files.txt'
BLOCKED=re.compile(
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|'
    r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b|'
    r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b|/home/[A-Za-z0-9_.-]+/|'
    r'\b[A-Za-z0-9._%+-]+@(?:gmail|outlook|yahoo|icloud)\.com\b'
)
EXTENSIONS={'.py','.md','.json','.txt','.toml','.cpp'}

def paths():
    entries=MANIFEST.read_text().splitlines()
    if entries!=sorted(set(entries)):raise ValueError('Publication allowlist must be sorted and unique.')
    for entry in entries:
        path=Path(entry)
        if path.is_absolute() or '..' in path.parts or (
            path.suffix not in EXTENSIONS and entry!='.gitignore'):
            raise ValueError(f'Unexpected release path {entry}')
        if any(part.startswith('.') for part in path.parts) and entry!='.gitignore':
            raise ValueError(f'Unexpected hidden path {entry}')
        file=ROOT/path
        if not file.is_file() or file.resolve()!=file:raise ValueError(f'Missing or linked release file {entry}')
        yield entry,file

def build(output):
    files=[]
    for entry,file in paths():
        content=file.read_bytes()
        if BLOCKED.search(content.decode('utf-8')):raise ValueError(f'Secret or private path indicator in {entry}')
        files.append((entry,content))
    metadata={name:dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for name,blob in files}
    with output.open('xb') as out,zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,blob in files+[('SOURCE-MANIFEST.json',json.dumps(metadata,indent=2,sort_keys=True).encode()+b'\n')]:
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.external_attr=0o100644<<16
            z.writestr(info,blob,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    print(json.dumps(dict(files=len(files),bytes=output.stat().st_size,
                          sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('output',type=Path)
    build(p.parse_args().output)
