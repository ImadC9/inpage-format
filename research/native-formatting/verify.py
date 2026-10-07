"""Verify native originals against the recorded discovery excerpts, read only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import struct

from reader import read_stream, UnsupportedProfile

for vendor in (Path(__file__).parent/'vendor',
               Path(__file__).parent.parent/'legacy-structures/vendor',
               Path(__file__).parent.parent/'inp-lab/vendor'):
    if vendor.is_dir():
        sys.path.insert(0,str(vendor))
        break
import olefile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def negative_checks(data):
    """In-memory corruptions test rejection; these are not native fixtures."""
    parsed=read_stream(data)
    variants=[]
    def altered(name,offset,raw):
        copy=bytearray(data)
        copy[offset:offset+len(raw)]=raw
        variants.append((name,copy))
    altered('invalid directory id',16,struct.pack('<H',9))
    altered('out-of-bounds directory target',36,struct.pack('<I',len(data)+100))
    altered('unverified default-style profile',parsed['default_header']['offset']+120,bytes.fromhex('997f'))
    altered('text length escapes story section',parsed['text_offset']-4,struct.pack('<I',2**32-1))
    altered('unknown body property width',parsed['format_entries'][1]['properties'][-1]['offset'],bytes.fromhex('997f'))
    altered('unverified span ownership profile',parsed['format_entries'][0]['offset'],struct.pack('<I',2))
    variants.append(('truncated full stream',data[:-1]))
    results=[]
    for name,bad in variants:
        try:read_stream(bad)
        except UnsupportedProfile:results.append({'case':name,'rejected':True})
        else:raise ValueError('malformed stream accepted: '+name)
    return results


def verify(folder, evidence):
    results=[]
    rejection_tests=[]
    for sample in evidence['samples']:
        path=folder/sample['file']
        if path.stat().st_size!=sample['file_size']:
            raise ValueError(f"original file size mismatch: {path.name}")
        raw=path.read_bytes()
        if sha(raw)!=sample['file_sha256']:
            raise ValueError(f"original file hash mismatch: {path.name}")
        with olefile.OleFileIO(path) as doc:
            data=doc.openstream('InPage100').read()
        if sha(data)!=sample['stream_sha256']:
            raise ValueError(f"logical stream hash mismatch: {path.name}")
        for excerpt in sample['excerpts']:
            offset=excerpt['offset']
            expected=bytes.fromhex(excerpt['hex'])
            if data[offset:offset+len(expected)]!=expected:
                raise ValueError(f"excerpt mismatch: {path.name} at {offset}")
        parsed=read_stream(data)
        if not rejection_tests:
            rejection_tests=negative_checks(data)
        body=parsed['body']['style']
        for key,value in sample['expected_body'].items():
            if body[key]!=value:
                raise ValueError(f"semantic check failed: {path.name} {key}")
        if parsed['text_sha256']!=evidence['shared_text_sha256']:
            raise ValueError(f"text changed: {path.name}")
        # The entire stream remains available locally. Only formatting excerpts
        # and hashes are included in this shareable report.
        results.append({'file':path.name,'file_sha256':sha(raw),
                        'stream_sha256':sha(data),'text_sha256':parsed['text_sha256'],
                        'format_entry_spans':[e['span_value'] for e in parsed['format_entries']],
                        'body_style':body,'trailing_cr_style':parsed['trailing_cr']['style'],
                        'passed':True})
    controls=[r['stream_sha256'] for r in results if r['file'] in evidence['controls']]
    if len(controls)!=3 or len(set(controls))!=1:
        raise ValueError('unchanged control streams do not match')
    return {'passed':True, 'native_files_checked':len(results),
            'control_streams_identical':True,'independent_held_out_document_checked':False,
            'general_inline_ownership_verified':False,
            'body_and_cr_ownership':'inferred single-paragraph profile only',
            'malformed_input_checks':rejection_tests,
            'native_reopen':'reported successful by sample author; not independently replayed',
            'samples':results}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        evidence=json.loads((Path(__file__).parent/'evidence.json').read_text(encoding='utf-8'))
        report=verify(args.samples,evidence)
        rendered=json.dumps(report,indent=2,ensure_ascii=True)+'\n'
        if args.report:
            with args.report.open('x',encoding='utf-8') as out:
                out.write(rendered)
            print(f"PASS: {len(report['samples'])} native files, matching controls, exact excerpts and formatting checks")
        else:
            print(rendered,end='')
    except (ValueError,OSError,UnsupportedProfile) as error:
        # Avoid an exception traceback or local absolute path in public logs.
        print('FAIL: '+(error.strerror if isinstance(error,OSError) else str(error)),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
