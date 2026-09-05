#!/usr/bin/env python3
"""Capture private, reproducible GSC and Yandex Webmaster API evidence.

Install requirements-seo.txt in .venv-seo, then use npm run seo:baseline.
No credentials or raw query exports are written into the public build.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from seo_env import ROOT, load_env, private_json


def api(url, token, body=None, method=None, scheme='Bearer'):
    request = Request(url, data=json.dumps(body).encode() if body is not None else None,
                      method=method, headers={'Authorization': scheme + ' ' + token,
                                              'Content-Type': 'application/json'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                data = response.read()
                return {'status': response.status, 'data': json.loads(data) if data else {}}
        except HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            try: details = json.loads(error.read())
            except ValueError: details = {'message': 'Non-JSON API error'}
            return {'status': error.code, 'error': details}


def google_token(write=False):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as AuthRequest
    path = Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS']).expanduser()
    if not path.is_absolute(): path = ROOT / path
    credentials = service_account.Credentials.from_service_account_file(
        str(path), scopes=['https://www.googleapis.com/auth/webmasters' + ('' if write else '.readonly')])
    credentials.refresh(AuthRequest())
    return credentials.token


def search_rows(endpoint, token, start, end, dimensions):
    rows = []
    base = {'startDate': start, 'endDate': end, 'type': 'web', 'dataState': 'final',
            'dimensions': dimensions, 'rowLimit': 25000}
    last = {}
    # A finite capture with an explicit truncation flag, never silent partial totals.
    for start_row in range(0, 100000, 25000):
        last = api(endpoint, token, {**base, 'startRow': start_row})
        if last['status'] != 200: return last
        batch = last['data'].get('rows', [])
        rows.extend(batch)
        if len(batch) < 25000: break
    return {'status': 200, 'request': base, 'rows': rows,
            'truncated': len(rows) >= 100000,
            'aggregation_type': last['data'].get('responseAggregationType')}


def gsc(start, end, pages):
    token = google_token()
    prop = os.environ.get('GSC_PROPERTY', 'sc-domain:boonts.com')
    root = 'https://www.googleapis.com/webmasters/v3/sites/' + quote(prop, safe='')
    result = {'property': prop, 'date_range': {'start': start, 'end': end},
              'date_timezone': 'America/Los_Angeles', 'data_state': 'final'}
    for dimensions in ([], ['date'], ['page'], ['query', 'page'], ['country'], ['device']):
        key = '_'.join(dimensions) or 'totals'
        result[key] = search_rows(root + '/searchAnalytics/query', token, start, end, dimensions)
    result['sitemaps'] = api(root + '/sitemaps', token)
    result['inspection'] = []
    for page in pages:
        url = 'https://boonts.com' + page['path']
        inspected = api('https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', token,
                        {'inspectionUrl': url, 'siteUrl': prop, 'languageCode': 'en-US'})
        result['inspection'].append({'url': url, **inspected})
        time.sleep(0.25)
    return result


def yandex(start, end):
    token = os.environ.get('YANDEX_WEBMASTER_OAUTH_TOKEN')
    if not token: return {'status': 'missing_oauth_token'}
    # Fixed official host: a local setting cannot redirect the credential elsewhere.
    base = 'https://api.webmaster.yandex.net/v4'
    user = api(base + '/user', token, scheme='OAuth')
    if user['status'] != 200: return user
    uid = user['data']['user_id']
    hosts = api(f'{base}/user/{uid}/hosts', token, scheme='OAuth')
    if hosts['status'] != 200: return hosts
    host = next((h for h in hosts['data'].get('hosts', [])
                 if h.get('ascii_host_url') == 'https://boonts.com/'), None)
    if not host: return {'status': 'host_not_available'}
    prefix = f'{base}/user/{uid}/hosts/' + quote(host['host_id'], safe='')
    result = {'host': host, 'requested_date_range': {'start': start, 'end': end}}
    queries = urlencode([('order_by','TOTAL_SHOWS'), ('query_indicator','TOTAL_SHOWS'),
                         ('query_indicator','TOTAL_CLICKS'), ('date_from', start), ('date_to', end), ('limit',500)])
    for name, endpoint in [('summary','/summary'), ('diagnostics','/diagnostics'),
                           ('popular_queries','/search-queries/popular?' + queries),
                           ('search_history','/search-urls/in-search/history'),
                           ('sitemaps','/sitemaps'), ('in_search','/search-urls/in-search/samples?limit=100')]:
        result[name] = api(prefix + endpoint, token, scheme='OAuth')
        time.sleep(0.5)
    # Preserve returned dates/count; the popular query endpoint is not a complete query census.
    return result


def submit_sitemap():
    prop = os.environ.get('GSC_PROPERTY', 'sc-domain:boonts.com')
    target = 'https://boonts.com/sitemap.xml'
    google = api('https://www.googleapis.com/webmasters/v3/sites/' + quote(prop,safe='') +
                 '/sitemaps/' + quote(target,safe=''), google_token(write=True), method='PUT')
    return {'gsc': google, 'sitemap': target}


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=90)
    parser.add_argument('--end-date', default=(date.today()-timedelta(days=3)).isoformat())
    parser.add_argument('--submit-sitemap', action='store_true', help='Explicitly submit the published sitemap to GSC')
    args = parser.parse_args()
    if args.days < 1: parser.error('--days must be positive')
    if args.submit_sitemap:
        result = submit_sitemap()
        private_json(ROOT/'seo/private/sitemap-submission.json', result)
        print('GSC sitemap submission HTTP',result['gsc']['status'])
        return
    end = date.fromisoformat(args.end_date)
    start = end - timedelta(days=args.days-1)
    pages = json.loads((ROOT/'seo/pages.json').read_text())
    report = {'captured_at_utc': datetime.now(timezone.utc).isoformat()}
    for name, run in [('gsc', lambda: gsc(start.isoformat(),end.isoformat(),pages)),
                      ('yandex', lambda: yandex(start.isoformat(),end.isoformat()))]:
        try: report[name] = run()
        except Exception as error: report[name] = {'status':'failed','error_type':type(error).__name__}
        print(name + ': capture completed; details in private report')
    private_json(ROOT/'seo/private/search-baseline.json',report)
    totals = report.get('gsc',{}).get('totals',{}).get('rows',[])
    print('GSC aggregate:',json.dumps(totals,ensure_ascii=False))


if __name__ == '__main__': main()
