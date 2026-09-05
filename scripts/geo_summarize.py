#!/usr/bin/env python3
"""Resolve only Google's citation redirects, then summarize the private pilot."""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.request import HTTPRedirectHandler,build_opener
from urllib.error import HTTPError
from urllib.parse import urlsplit
from seo_env import ROOT,private_json
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):return None

def resolve(uri):
    if urlsplit(uri).hostname!='vertexaisearch.cloud.google.com':return uri
    try:
        response=build_opener(NoRedirect).open(uri,timeout=20)
        response.close()
    except HTTPError as e:
        if e.code in (301,302,303,307,308):return e.headers.get('Location')
    except Exception:pass
    return None

def main():
    path=ROOT/'seo/private/geo-pilot.json';data=json.loads(path.read_text())
    sources={s['uri'] for r in data['results'] if r.get('status')==200 for s in r.get('citations',[]) if 'uri' in s}
    cachepath=ROOT/'seo/private/geo-citation-urls.json';cache=json.loads(cachepath.read_text()) if cachepath.exists() else {}
    missing=[u for u in sources if not cache.get(u)]
    with ThreadPoolExecutor(max_workers=4) as pool:cache.update(zip(missing,pool.map(resolve,missing)))
    private_json(cachepath,cache)
    summaries=[]
    for r in data['results']:
        if r.get('status')!=200:continue
        r['roman_mentioned']=any(x in r['answer'].lower() for x in ['roman babunts','roman babuntc','роман бабунц','boonts.com'])
        r['brand_mentioned']=(any(x in r['answer'].lower() for x in ['shesafe','she safe']) if r['id'].endswith('03') else r['roman_mentioned'])
        resolved=[cache.get(s.get('uri')) for s in r.get('citations',[])]
        r['resolved_boonts_citations']=[u for u in resolved if u and urlsplit(u).hostname in ('boonts.com','www.boonts.com')]
        r['unresolved_citations']=sum(u is None for u in resolved)
        summaries.append({k:r[k] for k in ['id','repeat','group','finish_reason','brand_mentioned','resolved_boonts_citations','unresolved_citations']})
    private_json(path,data)
    report={'total_attempts':len(data['results']),'successful':len(summaries),'http_statuses':dict(Counter(str(r.get('status')) for r in data['results'])),'rows':summaries,'note':'Do not compute a complete benchmark from this partial, uneven API sample. Brand prompts name the brand explicitly. Successful citations do not validate claims, endorsement, consumer product visibility or causality.'}
    private_json(ROOT/'seo/private/geo-summary.json',report)
    print('Successful',len(summaries),'of',len(data['results']),'with resolved boonts citation',sum(bool(r['resolved_boonts_citations']) for r in summaries),'unresolved citations',sum(r['unresolved_citations'] for r in summaries))
if __name__=='__main__':main()
