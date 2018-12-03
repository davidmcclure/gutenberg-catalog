

import ujson

from lxml import etree

from .utils import safe_property, parse_numeric, split_mime, parse_datetime


NAMESPACES = {
    'dcterms': 'http://purl.org/dc/terms/',
    'pgterms': 'http://www.gutenberg.org/2009/pgterms/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}


def xpath(root, query, first=False, parser=None):
    """Query text.
    """
    res = root.xpath(query, namespaces=NAMESPACES)

    if parser:
        res = list(map(parser, res))

    if first:
        res = res[0] if res else None

    return res


class Tree:

    @classmethod
    def from_file(cls, path):
        return cls(etree.parse(path))

    @classmethod
    def from_element(cls, element):
        return cls(etree.ElementTree(element))

    def __init__(self, root):
        self.root = root

    def xpath(self, *args, **kwargs):
        return xpath(self.root, *args, **kwargs)


class Agent(Tree):

    def kv_pairs(self):
        """Parse metadata fields.

        Returns: list<(key, val)>
        """
        pairs = []
        for field in self.xpath('pgterms:*'):

            key = etree.QName(field.tag).localname

            # Take tag text if present, or @rdf:resource for webpage.
            val = (xpath(field, './text()', first=True) or
                   xpath(field, './@rdf:resource', first=True))

            if val:
                pairs.append((key, val))

        return pairs


class Format(Tree):

    @safe_property
    def url(self):
        return self.xpath('@rdf:about', first=True)

    @safe_property
    def formats(self):
        return self.xpath('dcterms:format//rdf:value/text()')

    @safe_property
    def extent(self):
        return self.xpath('dcterms:extent/text()', first=True,
            parser=parse_numeric)

    def row(self):
        return dict(url=self.url, formats=self.formats, extent=self.extent)


class BookXML(Tree):

    _json_keys = ('id', 'title', 'creators', 'author', 'surname',
        'subjects', 'formats', 'links', 'bookshelves', 'issued', 'rights',
        'downloads', 'publisher', 'language',)

    def __repr__(self):
        return '%s<%d>' % (self.__class__.__name__, self.id)

    @safe_property
    def id(self):
        raw = self.xpath('//pgterms:ebook/@rdf:about', first=True)
        return int(raw.split('/')[-1])

    @safe_property
    def title(self):
        return self.xpath('//dcterms:title/text()', first=True)

    def creators_iter(self):
        """Parse each <dcterms:creator>
        """
        for el in self.xpath('//dcterms:creator/pgterms:agent'):
            # TODO: Handle errors?
            agent = Agent.from_element(el)
            yield agent.kv_pairs()

    @safe_property.cached
    def creators(self):
        return list(self.creators_iter())

    @safe_property.cached
    def author(self):
        return dict(self.creators[0])['name']

    @safe_property
    def surname(self):
        return self.author.split(', ')[0]

    @safe_property
    def subjects(self):
        return self.xpath('//dcterms:subject//rdf:value/text()')

    def formats_iter(self):
        """Parse each <dcterms:hasFormat>
        """
        for el in self.xpath('//dcterms:hasFormat/pgterms:file'):
            format = Format.from_element(el)
            yield format.row()

    @safe_property.cached
    def formats(self):
        return list(self.formats_iter())

    @safe_property
    def links(self):
        """Map mime type -> download URL.
        """
        return {
            split_mime(f['formats'][0]): f['url']
            for f in self.formats
            if len(f['formats'])==1
        }

    @safe_property
    def bookshelves(self):
        return self.xpath('//pgterms:bookshelf//rdf:value/text()')

    @safe_property
    def issued(self):
        return self.xpath('//dcterms:issued/text()', first=True,
            parser=parse_datetime)

    @safe_property
    def rights(self):
        return self.xpath('//dcterms:rights/text()', first=True)

    @safe_property
    def downloads(self):
        return self.xpath('//pgterms:downloads/text()', first=True,
            parser=parse_numeric)

    @safe_property
    def language(self):
        return self.xpath('//dcterms:language//rdf:value/text()', first=True)

    @safe_property
    def publisher(self):
        return self.xpath('//dcterms:publisher/text()', first=True)

    def __iter__(self):
        for key in self._json_keys:
            yield key, getattr(self, key)

    def to_json(self):
        return ujson.dumps(dict(self))
