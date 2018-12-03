

import ujson
import maya
import click
import os

from lxml import etree
from functools import lru_cache
from glob import glob
from tqdm import tqdm


"""TODO
- module-ize
- use safe_property
- try/except in creators/formats loops
- handle missing authors
- editors
"""


def parse_numeric(val):
    """Try to cast str -> int/float.

    Args:
        val (str)
    """
    try: return int(val)
    except: pass

    try: return float(val)
    except: pass

    return val


def parse_datetime(val):
    """Try to cast str -> datetime.
    """
    try:
        return maya.parse(val).datetime()
    except:
        return val


def split_mime(text):
    return text.split(';')[0]


NAMESPACES = {
    'dcterms': 'http://purl.org/dc/terms/',
    'pgterms': 'http://www.gutenberg.org/2009/pgterms/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}


class CatalogXML:

    _json_keys = ('id', 'title', 'creators', 'author', 'surname',
                  'subjects', 'formats', 'links', 'bookshelves', 'issued',
                  'rights', 'downloads', 'publisher', 'language',)

    @classmethod
    def from_file(cls, path):
        return cls(etree.parse(path))

    def __init__(self, tree):
        self.tree = tree

    def xpath(self, query, root=None, first=False, parser=None):
        """Query text.
        """
        root = root if root is not None else self.tree

        res = root.xpath(query, namespaces=NAMESPACES)

        if parser:
            res = list(map(parser, res))

        if first:
            res = res[0] if res else None

        return res

    def id(self):
        raw = self.xpath('//pgterms:ebook/@rdf:about', first=True)
        return int(raw.split('/')[-1])

    def title(self):
        return self.xpath('//dcterms:title/text()', first=True)

    def creators_iter(self):
        """Parse each <dcterms:creator>.

        Yields: list<(key, val)>
        """
        for root in self.xpath('//dcterms:creator/pgterms:agent'):

            creator = []
            for field in self.xpath('pgterms:*', root):

                key = etree.QName(field.tag).localname

                # Take tag text if present, or @rdf:resource for webpage.
                val = (self.xpath('./text()', field, first=True) or
                       self.xpath('./@rdf:resource', field, first=True))

                if val:
                    creator.append((key, val))

            yield creator

    @lru_cache()
    def creators(self):
        return list(self.creators_iter())

    def author(self):
        return dict(self.creators()[0])['name']

    def surname(self):
        return self.author().split(', ')[0]

    def subjects(self):
        return self.xpath('//dcterms:subject//rdf:value/text()')

    def formats_iter(self):
        """Parse each <dcterms:hasFormat>.

        Yields: list<dict>
        """
        for root in self.xpath('//dcterms:hasFormat/pgterms:file'):

            url = self.xpath('./@rdf:about', root, first=True)

            formats = self.xpath('./dcterms:format//rdf:value/text()', root)

            extent = self.xpath('./dcterms:extent/text()', root, first=True,
                parser=parse_numeric)

            yield dict(url=url, formats=formats, extent=extent)

    @lru_cache()
    def formats(self):
        return list(self.formats_iter())

    def links(self):
        """Map mime type -> download URL.
        """
        return {
            split_mime(f['formats'][0]): f['url']
            for f in self.formats() if len(f['formats'])==1
        }

    def bookshelves(self):
        return self.xpath('//pgterms:bookshelf//rdf:value/text()')

    def issued(self):
        return self.xpath('//dcterms:issued/text()', first=True,
            parser=parse_datetime)

    def rights(self):
        return self.xpath('//dcterms:rights/text()', first=True)

    def downloads(self):
        return self.xpath('//pgterms:downloads/text()', first=True,
            parser=parse_numeric)

    def publisher(self):
        return self.xpath('//dcterms:publisher/text()', first=True)

    def language(self):
        return self.xpath('//dcterms:language//rdf:value/text()', first=True)

    def __iter__(self):
        for key in self._json_keys:
            try:
                yield key, getattr(self, key)()
            except Exception as e:
                print(self.id(), key, e)

    def to_json(self):
        return ujson.dumps(dict(self))


@click.command()
@click.argument('src', type=click.Path(), default='cache')
@click.argument('dst', type=click.Path(), default='catalog.json')
def convert(src, dst):
    """Dump JSON lines to file.
    """
    pattern = os.path.join(src, '**/*.rdf')

    paths = glob(pattern, recursive=True)

    with open(dst, 'w') as fh:
        for path in tqdm(paths):
            b = CatalogXML.from_file(path)
            print(b.to_json(), file=fh)


if __name__ == '__main__':
    convert()
