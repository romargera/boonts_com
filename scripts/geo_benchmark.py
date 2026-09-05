#!/usr/bin/env python3
"""Private API pilot; not a measurement of consumer Gemini, ChatGPT or Perplexity."""
import argparse,csv,json,os,time,threading
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
from seo_env import ROOT,load_env,private_json

def sample(item,repeat,model):
    started=datetime.now(timezone.utc).isoformat()
    req=Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps({'contents':[{'role':'user','parts':[{'text':item['prompt']}]}],
          'tools':[{'google_search':{}}], 'generationConfig':{'maxOutputTokens':1500,'temperature':0.7,'thinkingConfig':{'thinkingBudget':0}}}).encode(),
        headers={'x-goog-api-key':os.environ['GEMINI_API_KEY'],'Content-Type':'application/json'})
    result={'id':item['id'],'language':item['language'],'group':item['group'],'prompt':item['prompt'],'repeat':repeat,'model':model,'timestamp_utc':started,'surface':'Gemini API; independent request; Google Search tool enabled','parameters':{'temperature':0.7,'maxOutputTokens':1500,'thinkingBudget':0}}
    try:
        with urlopen(req,timeout=120) as response: raw=json.load(response)
        result['status']=200;result['raw']=raw
        c=(raw.get('candidates') or [{}])[0]; answer='\n'.join(p.get('text','') for p in c.get('content',{}).get('parts',[]))
        g=c.get('groundingMetadata',{})
        result.update(answer=answer,finish_reason=c.get('finishReason'),search_queries=g.get('webSearchQueries',[]),citations=[v['web'] for v in g.get('groundingChunks',[]) if 'web' in v])
        result['brand_mentioned']=any(x in answer.lower() for x in ['roman babunts','roman babuntc','роман бабунц','boonts.com'])
        result['direct_boonts_citation']=any(urlsplit(v.get('uri','')).hostname=='boonts.com' for v in result['citations'])
        result['redirect_citations_unresolved']=sum(urlsplit(v.get('uri','')).hostname=='vertexaisearch.cloud.google.com' for v in result['citations'])
    except HTTPError as error:
        result['status']=error.code
        try: result['error']=json.loads(error.read())
        except ValueError: result['error']='Non-JSON response'
    except Exception as error: result.update(status='failed',error_type=type(error).__name__)
    private_json(ROOT/f"seo/private/geo/{item['id']}-{repeat}.json",result)
    print(item['id'],repeat,result['status'],flush=True)
    return result

def main():
    load_env();p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repeats',type=int,default=3);p.add_argument('--limit',type=int,default=12);p.add_argument('--model',default='gemini-2.5-flash');a=p.parse_args()
    if not 1<=a.repeats<=3 or not 1<=a.limit<=12:p.error('Bounded to 12 prompts × 3 repeats')
    rows=list(csv.DictReader((ROOT/'seo/GEO_PROMPTS.csv').open()))[:a.limit]
    results=[];jobs=[]
    for row in rows:
        for repeat in range(1,a.repeats+1):
            path=ROOT/f"seo/private/geo/{row['id']}-{repeat}.json"
            previous=json.loads(path.read_text()) if path.exists() else {}
            if previous.get('status')==200 and previous.get('model')==a.model and previous.get('prompt')==row['prompt']:
                results.append(previous)
            else:jobs.append((row,repeat))
    lock=threading.Lock();next_start=[0.0]
    def limited(job):
        with lock:
            wait=max(0,next_start[0]-time.monotonic())
            if wait:time.sleep(wait)
            next_start[0]=time.monotonic()+14
        return sample(*job,a.model)
    with ThreadPoolExecutor(max_workers=2) as pool:results+=list(pool.map(limited,jobs))
    private_json(ROOT/'seo/private/geo-pilot.json',{'captured_at_utc':datetime.now(timezone.utc).isoformat(),'results':results,'limits':'API pilot only; prompts mentioning the brand are separate from nonbrand. Google redirect citations require resolution before citation-rate scoring. A tool-enabled response may not actually search; inspect search_queries and finish_reason. Failed/truncated responses are not negative visibility.'})
if __name__=='__main__':main()
