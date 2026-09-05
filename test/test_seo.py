"""Regression tests: corrupt valid site metadata and require the guard to fail."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('seo', Path(__file__).resolve().parents[1] / 'scripts/seo.py')
seo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seo)


class SEOTests(unittest.TestCase):
    def setUp(self):
        self.pages = seo.load_pages()
        self.robots = (seo.ROOT / 'public/robots.txt').read_text()

    def assert_rejected(self, fragment):
        self.assertTrue(any(fragment in e for e in seo.validate(self.pages, self.robots)))

    def test_current_site(self):
        self.assertEqual(seo.validate(self.pages, self.robots), [])

    def test_cross_language_canonical(self):
        page = self.pages[3][1]
        next(a for a in page.links if a.get('rel') == 'canonical')['href'] = seo.ORIGIN + self.pages[2][0]['path']
        self.assert_rejected('self-referencing canonical')

    def test_missing_return_hreflang(self):
        page = self.pages[3][1]
        page.links = [a for a in page.links if a.get('hreflang') != 'en']
        self.assert_rejected('reciprocal')

    def test_noindex_cannot_enter_sitemap(self):
        self.pages[0][1].metas.append({'name': 'robots', 'content': 'noindex,follow'})
        self.assert_rejected('sitemap page is noindex')

    def test_machine_only_faq_claim(self):
        question = next(n for n in seo.nodes(self.pages[2][1].schemas) if n.get('@type') == 'Question')
        question['acceptedAnswer']['text'] = 'Invented claim that readers cannot see.'
        self.assert_rejected('FAQ answer differs')

    def test_article_author_identity(self):
        article = next(n for n in seo.nodes(self.pages[2][1].schemas) if n.get('@type') in ('Article', 'TechArticle'))
        article['author']['@id'] = 'https://example.org/#person'
        self.assert_rejected('author entity differs')

    def test_future_modified_date(self):
        article = next(n for n in seo.nodes(self.pages[2][1].schemas) if n.get('@type') in ('Article', 'TechArticle'))
        article['dateModified'] = '2099-01-01'
        self.assert_rejected('future date')

    def test_broken_deep_link(self):
        self.pages[0][1].anchors.append('/insights/en/roman-vs-experts.html#missing-heading')
        self.assert_rejected('broken anchor')

    def test_original_robots_inheritance_bug(self):
        self.robots = 'User-agent: *\nDisallow: /pru_translator/\n\nUser-agent: OAI-SearchBot\nAllow: /\nSitemap: https://boonts.com/sitemap.xml'
        self.assert_rejected('OAI-SearchBot bypasses')

    def test_robots_specificity_allow_tie_and_query(self):
        robots = seo.Robots()
        robots.parse('User-agent: *\nDisallow: /\nUser-agent: ExampleBot\nAllow: /\nDisallow: /private/\nAllow: /private/public$\nDisallow: /*?secret=\n'.splitlines())
        self.assertFalse(robots.can_fetch('ElseBot', seo.ORIGIN + '/'))
        self.assertTrue(robots.can_fetch('ExampleBot/1.0', seo.ORIGIN + '/'))
        self.assertFalse(robots.can_fetch('ExampleBot', seo.ORIGIN + '/private/file'))
        self.assertTrue(robots.can_fetch('ExampleBot', seo.ORIGIN + '/private/public'))
        self.assertFalse(robots.can_fetch('ExampleBot', seo.ORIGIN + '/private/public/'))
        self.assertFalse(robots.can_fetch('ExampleBot', seo.ORIGIN + '/?secret=x'))
        robots.parse('User-agent: *\nDisallow: /same\nAllow: /same'.splitlines())
        self.assertTrue(robots.can_fetch('ExampleBot', seo.ORIGIN + '/same'))

    def test_exports_follow_visible_content_without_scripts(self):
        page = seo.Page('<html lang="en"><head><title>Test</title></head><body><nav>Navigation</nav><main><h1>Title</h1><p>Reader claim &amp; evidence.</p><script>Hidden invention</script></main><footer>Footer</footer></body></html>')
        generated = seo.generated([({'path': '/', 'export': True}, page)])
        self.assertIn('Reader claim & evidence.', generated['llms-full.txt'])
        self.assertNotIn('Hidden invention', generated['llms-full.txt'])
        self.assertNotIn('Navigation\n', generated['llms-full.txt'])
        page.text.append('New visible evidence.')
        self.assertNotEqual(generated['llms-full.txt'], seo.generated([({'path': '/', 'export': True}, page)])['llms-full.txt'])

    def test_sitemap_has_only_registered_canonicals_and_editorial_dates(self):
        tree = ET.fromstring(seo.generated(self.pages)['sitemap.xml'])
        self.assertEqual([e.text for e in tree.findall(f'{{{seo.SM}}}url/{{{seo.SM}}}loc')],
                         [seo.ORIGIN + e['path'] for e, _ in self.pages])
        self.assertEqual(len(tree.findall(f'{{{seo.SM}}}url/{{{seo.SM}}}lastmod')), 4)


if __name__ == '__main__': unittest.main()
