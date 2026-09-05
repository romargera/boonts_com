#!/usr/bin/env python3
"""Submit the published sitemap and optionally request a bounded recrawl."""
import argparse,json,os
from urllib.parse import quote
from seo_env import ROOT,load_env,private_json
from search_baseline import api

def main():
    load_env();p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recrawl',action='store_true');args=p.parse_args()
    token=os.environ['YANDEX_WEBMASTER_OAUTH_TOKEN'];base='https://api.webmaster.yandex.net/v4'
    user=api(base+'/user',token,scheme='OAuth');assert user['status']==200
    uid=user['data']['user_id'];hosts=api(f'{base}/user/{uid}/hosts',token,scheme='OAuth');assert hosts['status']==200
    host=next(h for h in hosts['data']['hosts'] if h.get('ascii_host_url')=='https://boonts.com/')
    prefix=f'{base}/user/{uid}/hosts/'+quote(host['host_id'],safe='')
    result={'sitemap':api(prefix+'/user-added-sitemaps',token,{'url':'https://boonts.com/sitemap.xml'},scheme='OAuth')}
    print('Sitemap',result['sitemap']['status'],'(409 means already registered)')
    if args.recrawl:
        result['quota']=api(prefix+'/recrawl/quota',token,scheme='OAuth');result['recrawl']=[]
        for page in json.loads((ROOT/'seo/pages.json').read_text()):
            if not page.get('export'):continue
            url='https://boonts.com'+page['path']
            receipt=api(prefix+'/recrawl/queue',token,{'url':url},scheme='OAuth')
            result['recrawl'].append({'url':url,**receipt});print(page['path'],receipt['status'])
            if receipt['status']==429:break
    private_json(ROOT/'seo/private/yandex-submission.json',result)
if __name__=='__main__':main()
