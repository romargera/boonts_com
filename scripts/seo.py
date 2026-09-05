#!/usr/bin/env python3
"""Dependency-free SEO generation and checks against actual static HTML.

python3 scripts/seo.py generate
python3 scripts/seo.py check [--root dist]
python3 scripts/seo.py live --output seo/live-baseline.json
"""
import argparse
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://boonts.com'
PERSON = ORIGIN + '/#person'
SM = 'http://www.sitemaps.org/schemas/sitemap/0.9'
XHTML = 'http://www.w3.org/1999/xhtml'
AGENTS = ['Googlebot', 'bingbot', 'YandexBot', 'OAI-SearchBot', 'GPTBot',
          'ClaudeBot', 'Claude-SearchBot', 'PerplexityBot', 'Google-Extended',
          'Applebot-Extended', 'Diffbot', 'cohere-ai', 'CCBot']


class Robots:
    """Group specificity + longest path match, unlike urllib's first-rule match.

    Supports the site's UTF-8 paths, wildcard and end-anchor rules. This is a
    deployment contract check, not a replacement for search-engine diagnostics.
    """
    def parse(self, lines):
        self.groups, self.sitemaps = [], []
        agents, rules = [], []
        for line in lines:
            key, separator, value = line.split('#', 1)[0].partition(':')
            if not separator: continue
            key, value = key.strip().lower(), value.strip()
            if key == 'user-agent':
                if rules:
                    self.groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif key in ('allow', 'disallow') and agents:
                rules.append((key, value))
            elif key == 'sitemap': self.sitemaps.append(value)
        if agents: self.groups.append((agents, rules))

    def can_fetch(self, agent, url):
        candidates = []
        for agents, rules in self.groups:
            matches = [len(a) if a != '*' else 0 for a in agents if a == '*' or a in agent.lower()]
            if matches: candidates.append((max(matches), rules))
        if not candidates: return True
        specificity = max(score for score, _ in candidates)
        path = urlsplit(url).path or '/'
        if urlsplit(url).query: path += '?' + urlsplit(url).query
        matched = []
        for score, rules in candidates:
            if score != specificity: continue
            for directive, pattern in rules:
                if not pattern: continue
                end = pattern.endswith('$')
                value = pattern[:-1] if end else pattern
                regex = '^' + '.*'.join(re.escape(part) for part in value.split('*')) + ('$' if end else '')
                if re.search(regex, path): matched.append((len(value.replace('*', '').encode('utf8')), directive == 'allow'))
        return max(matched)[1] if matched else True

    def site_maps(self): return self.sitemaps


def clean(value):
    return ' '.join(value.split())


class Page(HTMLParser):
    """Parse SEO metadata and reader-facing text; never execute page scripts."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.lang = ''
        self.links, self.anchors, self.metas, self.ids = [], [], [], set()
        self.schemas, self.schema_errors = [], []
        self.title, self.h1, self.text = [], [], []
        self.in_title = self.in_h1 = self.in_body = False
        self.skip = []
        self.json_buffer = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang', '')
        if tag == 'link': self.links.append(a)
        if tag == 'meta': self.metas.append(a)
        if tag == 'a' and 'href' in a: self.anchors.append(a['href'])
        if a.get('id'): self.ids.add(a['id'])
        if tag == 'title': self.in_title = True
        if tag == 'h1':
            self.in_h1 = True
            self.h1.append('')
        if tag == 'body': self.in_body = True
        if tag == 'script' and a.get('type') == 'application/ld+json': self.json_buffer = []
        if tag in ('script', 'style', 'noscript', 'nav', 'footer'): self.skip.append(tag)
        if tag in ('p', 'div', 'section', 'h1', 'h2', 'h3', 'li', 'tr', 'br', 'summary'):
            self.text.append('\n')
        if tag in ('td', 'th'): self.text.append(' | ')

    def handle_endtag(self, tag):
        if tag == 'script' and self.json_buffer is not None:
            try: self.schemas.append(json.loads(''.join(self.json_buffer)))
            except ValueError as e: self.schema_errors.append(str(e))
            self.json_buffer = None
        if tag in self.skip:
            self.skip.remove(tag)
        if tag == 'title': self.in_title = False
        if tag == 'h1': self.in_h1 = False
        if tag == 'body': self.in_body = False
        if tag in ('p', 'div', 'section', 'h1', 'h2', 'h3', 'li', 'tr', 'summary'):
            self.text.append('\n')

    def handle_data(self, value):
        if self.json_buffer is not None: self.json_buffer.append(value)
        if self.in_title: self.title.append(value)
        if self.in_h1: self.h1[-1] += value
        if self.in_body and not self.skip: self.text.append(value)

    def meta(self, name):
        return [m.get('content', '') for m in self.metas if m.get('name', m.get('property')) == name]

    @property
    def canonical(self):
        return [a.get('href', '') for a in self.links if a.get('rel') == 'canonical']

    @property
    def alternates(self):
        return [(a['hreflang'], a.get('href', '')) for a in self.links
                if a.get('rel') == 'alternate' and 'hreflang' in a]

    @property
    def visible(self):
        return '\n'.join(clean(line) for line in ''.join(self.text).splitlines() if clean(line))


def nodes(value):
    if isinstance(value, dict):
        yield value
        for item in value.values(): yield from nodes(item)
    elif isinstance(value, list):
        for item in value: yield from nodes(item)


def registry():
    return json.loads((ROOT / 'seo/pages.json').read_text())


def output_path(path):
    return path.lstrip('/') + ('index.html' if path.endswith('/') else '')


def load_pages(build=None):
    return [(entry, Page(((build / output_path(entry['path'])) if build else
                         ROOT / entry['source']).read_text())) for entry in registry()]


def generated(pages):
    ET.register_namespace('', SM)
    ET.register_namespace('xhtml', XHTML)
    root = ET.Element(f'{{{SM}}}urlset')
    brief = ['# Roman Babunts — website guide', '',
             '> Navigation and page descriptions from boonts.com. Author-published material; not independent verification of claims.', '',
             '## Pages', '']
    full = ['# boonts.com — reader-facing page text', '',
            '> Generated from the same HTML delivered to readers. This export does not independently verify biographies, results, or product claims. Navigation, scripts and footers are omitted. Follow each source URL for formatting and references.', '']
    for entry, page in pages:
        url = ORIGIN + entry['path']
        item = ET.SubElement(root, f'{{{SM}}}url')
        ET.SubElement(item, f'{{{SM}}}loc').text = url
        modified = [n['dateModified'] for n in nodes(page.schemas)
                    if n.get('@type') in ('Article', 'TechArticle') and 'dateModified' in n]
        # Never infer editorial freshness from deployment time or file mtime.
        if modified: ET.SubElement(item, f'{{{SM}}}lastmod').text = max(modified)
        for lang, href in page.alternates:
            ET.SubElement(item, f'{{{XHTML}}}link', rel='alternate', hreflang=lang, href=href)
        title = clean(''.join(page.title)).replace('[', '(').replace(']', ')')
        description = clean(' '.join(page.meta('description')))
        brief.append(f'- [{title}]({url}): {description}')
        if entry.get('export'):
            full.extend([f'## {title}', '', f'Source: {url}', f'Language: {page.lang}', '', page.visible, ''])
    brief.extend(['', '## Optional', '', '- [Page text export](https://boonts.com/llms-full.txt): Text from the pages above.', ''])
    ET.indent(root, space='  ')
    return {'sitemap.xml': '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n',
            'llms.txt': '\n'.join(brief), 'llms-full.txt': '\n'.join(full)}


def validate(pages, robots, build=None, check_files=True):
    errors = []
    by_url = {ORIGIN + e['path']: p for e, p in pages}
    if len(by_url) != len(pages): errors.append('Duplicate URL in seo/pages.json')
    rp = Robots()
    rp.parse(robots.splitlines())
    titles, descriptions = set(), set()
    for entry, page in pages:
        url = ORIGIN + entry['path']
        def check(ok, message):
            if not ok: errors.append(f'{entry["path"]}: {message}')
        check(page.canonical == [url], 'expected one self-referencing canonical')
        check(bool(page.lang), 'missing HTML language')
        check(len(page.h1) == 1 and bool(clean(page.h1[0])), 'expected one nonempty H1')
        title = clean(''.join(page.title))
        check(bool(title) and title not in titles, 'missing or duplicate title')
        titles.add(title)
        desc = page.meta('description')
        check(len(desc) == 1 and bool(clean(desc[0])) and desc[0] not in descriptions, 'missing or duplicate description')
        descriptions.update(desc)
        check(not any('noindex' in v.lower() for v in page.meta('robots')), 'sitemap page is noindex')
        check(not page.schema_errors, 'invalid JSON-LD: ' + '; '.join(page.schema_errors))
        if page.meta('og:url'): check(page.meta('og:url') == [url], 'og:url differs from canonical')
        alternatives = dict(page.alternates)
        check(len(alternatives) == len(page.alternates), 'duplicate hreflang')
        if alternatives:
            check(alternatives.get(page.lang) == url, 'hreflang missing self')
            for lang, target in alternatives.items():
                check(target in by_url, f'hreflang target absent from registry: {target}')
                if target in by_url:
                    check(dict(by_url[target].alternates) == alternatives, 'hreflang cluster not reciprocal/equal')
                    if lang != 'x-default': check(by_url[target].lang == lang, 'hreflang target language differs')
        for agent in AGENTS: check(rp.can_fetch(agent, url), f'blocked for {agent}')
        for n in nodes(page.schemas):
            if n.get('@type') in ('Article', 'TechArticle') and 'datePublished' in n:
                check(n.get('author', {}).get('@id') == PERSON, 'article author entity differs')
                check(n.get('inLanguage') == page.lang, 'article language differs')
                check(n.get('url') == url, 'article URL differs')
                try:
                    published = date.fromisoformat(n['datePublished'][:10])
                    modified = date.fromisoformat(n.get('dateModified', n['datePublished'])[:10])
                    check(published <= modified <= date.today(), 'invalid publication/modification order or future date')
                except (ValueError, TypeError): check(False, 'invalid article date')
            if n.get('@type') == 'Question':
                visible = clean(page.visible)
                check(clean(n.get('name', '')) in visible, 'FAQ question absent from visible text')
                check(clean(n.get('acceptedAnswer', {}).get('text', '')) in visible, 'FAQ answer differs from visible text')
        for href in page.anchors:
            target = urlsplit(urljoin(url, href))
            if target.scheme not in ('http', 'https') or target.netloc != 'boonts.com': continue
            target_url = ORIGIN + target.path
            if target_url in by_url:
                if target.fragment: check(unquote(target.fragment) in by_url[target_url].ids, f'broken anchor: {href}')
            elif check_files:
                relative = output_path(unquote(target.path))
                candidates = [build / relative] if build else [ROOT / 'public' / relative, ROOT / 'src' / relative]
                check(any(p.is_file() for p in candidates), f'missing internal destination: {href}')
    for agent in AGENTS:
        if rp.can_fetch(agent, ORIGIN + '/pru_translator/'):
            errors.append(f'robots.txt: {agent} bypasses /pru_translator/ exclusion')
    if rp.site_maps() != [ORIGIN + '/sitemap.xml']: errors.append('robots.txt: sitemap declaration differs')
    # Every built source HTML page must have an explicit indexing decision.
    for path in ((build or ROOT / 'src').rglob('*.html') if check_files else []):
        if not build and 'content' in path.parts: continue
        parsed = Page(path.read_text())
        if parsed.canonical and parsed.canonical[0] in by_url: continue
        if any('noindex' in value.lower() for value in parsed.meta('robots')): continue
        # Public embedded demos and verification files are outside this inventory.
        if build and (path.relative_to(build).parts[0] in ('cables', 'pru_translator') or path.name.startswith('yandex_')): continue
        errors.append(f'{path.relative_to(build or ROOT)}: HTML page needs registry entry or explicit noindex')
    return errors


def fetch(url, agent=None):
    cmd = ['curl', '-sS', '--max-time', '30', '--max-redirs', '5', '-L', '-w', '\n%{http_code}\t%{url_effective}', url]
    if agent: cmd.extend(['-A', agent])
    with tempfile.NamedTemporaryFile() as headers:
        result = subprocess.run(cmd + ['-D', headers.name], capture_output=True, text=True)
        header_text = Path(headers.name).read_text()
    if result.returncode: return {'url': url, 'error': result.stderr.strip()}, ''
    body, info = result.stdout.rsplit('\n', 1)
    status, final_url = info.split('\t', 1)
    relevant = {}
    for line in header_text.splitlines():
        if line.startswith('HTTP/'): relevant = {}
        key, _, value = line.partition(':')
        if key.lower() in ('server', 'content-type', 'x-robots-tag', 'cf-cache-status'):
            relevant[key.lower()] = value.strip()
    return {'url': url, 'status': int(status), 'final_url': final_url, 'headers': relevant}, body


def live(output):
    records = []
    record, robots = fetch(ORIGIN + '/robots.txt')
    records.append(record)
    if record.get('status') != 200: raise RuntimeError('Cannot read robots.txt; live crawl stopped')
    rp = Robots()
    rp.parse(robots.splitlines())
    pages = []
    for entry in registry():
        url = ORIGIN + entry['path']
        if not rp.can_fetch('BoontsSEOCheck', url):
            records.append({'url': url, 'skipped': 'robots.txt'})
            continue
        time.sleep(1)
        record, body = fetch(url)
        if record.get('status') == 200:
            page = Page(body)
            pages.append((entry, page))
            record.update(canonical=page.canonical, lang=page.lang,
                          title=clean(''.join(page.title)), h1=page.h1,
                          robots=page.meta('robots'), schema_errors=page.schema_errors)
            record['edge_email_rewriting'] = any('/cdn-cgi/l/email-protection' in href for href in page.anchors)
        records.append(record)
    for suffix in ('sitemap.xml', 'llms.txt', 'llms-full.txt', 'seo-check-missing-page-20260905'):
        time.sleep(1)
        record, _ = fetch(ORIGIN + '/' + suffix)
        records.append(record)
    # UA probes demonstrate HTTP access only; they do not impersonate a verified crawler IP.
    for agent in ('OAI-SearchBot', 'Claude-SearchBot', 'PerplexityBot'):
        if not rp.can_fetch(agent, ORIGIN + '/'): continue
        time.sleep(1)
        record, _ = fetch(ORIGIN + '/', agent)
        record['user_agent_probe'] = agent
        records.append(record)
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'HTTP and HTML snapshot; no ranking, index coverage, verified bot access or field CWV measurement',
              'robots_txt': robots, 'responses': records,
              'html_findings': validate(pages, robots, check_files=False)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'Wrote {len(records)} HTTP observations to {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['generate', 'check', 'live'])
    parser.add_argument('--root', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'seo/live-baseline.json')
    args = parser.parse_args()
    if args.command == 'live':
        live(args.output)
        return
    pages = load_pages(args.root)
    target = args.root or ROOT / 'public'
    errors = validate(pages, (target / 'robots.txt').read_text(), args.root)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    for name, content in generated(pages).items():
        path = target / name
        if args.command == 'generate': path.write_text(content)
        elif not path.exists() or path.read_text() != content: errors.append(f'{name}: stale; run npm run seo:generate')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    print(f'SEO {args.command}: {len(pages)} pages passed; sitemap and text exports are consistent.')


if __name__ == '__main__': main()
