

import os
import ujson
import glob

from lxml import etree
from tqdm import tqdm

from .utils import cached_property, parse_numeric, split_mime, parse_datetime
from . import logger


NAMESPACES = {
    'dcterms': 'http://purl.org/dc/terms/',
    'pgterms': 'http://www.gutenberg.org/2009/pgterms/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}


def xpath(root, query, parser=None, first=False):
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

    @cached_property
    def name(self):
        return self.xpath('//pgterms:name/text()', first=True)

    @cached_property
    def given_name_surname(self):
        return self.name.split(', ', 1)

    @cached_property
    def given_name(self):
        return self.given_name_surname[1]

    @cached_property
    def surname(self):
        return self.given_name_surname[0]

    def to_dict(self):
        return dict(given_name=self.given_name, surname=self.surname)


class BookXML(Tree):

    # _json_keys = ('id', 'title', 'creators', 'author', 'surname',
    #     'subjects', 'formats', 'links', 'bookshelves', 'issued', 'rights',
    #     'downloads', 'publisher', 'language',)

    def __repr__(self):
        return '%s<%d>' % (self.__class__.__name__, self.id)

    @cached_property
    def id(self):
        raw = self.xpath('//pgterms:ebook/@rdf:about', first=True)
        return int(raw.split('/')[-1])

    @cached_property
    def title(self):
        return self.xpath('//dcterms:title/text()', first=True)

    @cached_property
    def agents(self):
        return [
            Agent.from_element(el)
            for el in self.xpath('//dcterms:creator/pgterms:agent')
        ]

    def to_dict(self):
        return dict(
            id=self.id,
            title=self.title,
            authors=[a.to_dict() for a in self.agents]
        )

    # def creators_iter(self):
    #     """Parse each <dcterms:creator>
    #     """
    #     for el in self.xpath('//dcterms:creator/pgterms:agent'):
    #         yield Agent.from_element(el)
    #
    # @cached_property
    # def creators(self):
    #     return [c.row() for c in self.creators_iter()]
    #
    # @cached_property
    # def first_author(self):
    #     return self.creators[0]['name']
    #
    # @cached_property
    # def first_author_surname(self):
    #     return self.first_author.split(', ')[0]
    #
    # @safe_property
    # def subjects(self):
    #     return self.xpath('//dcterms:subject//rdf:value/text()')
    #
    # def formats_iter(self):
    #     """Parse each <dcterms:hasFormat>
    #     """
    #     for el in self.xpath('//dcterms:hasFormat/pgterms:file'):
    #         format = Format.from_element(el)
    #         yield format.row()
    #
    # @safe_property.cached
    # def formats(self):
    #     return list(self.formats_iter())
    #
    # @safe_property
    # def links(self):
    #     """Map mime type -> download URL.
    #     """
    #     return {
    #         split_mime(f['formats'][0]): f['url']
    #         for f in self.formats
    #         if len(f['formats'])==1
    #     }
    #
    # @safe_property
    # def bookshelves(self):
    #     return self.xpath('//pgterms:bookshelf//rdf:value/text()')
    #
    # @safe_property
    # def issued(self):
    #     return self.xpath('//dcterms:issued/text()', first=True,
    #         parser=parse_datetime)
    #
    # @safe_property
    # def rights(self):
    #     return self.xpath('//dcterms:rights/text()', first=True)
    #
    # @safe_property
    # def downloads(self):
    #     return self.xpath('//pgterms:downloads/text()', first=True,
    #         parser=parse_numeric)
    #
    # @safe_property
    # def language(self):
    #     return self.xpath('//dcterms:language//rdf:value/text()', first=True)
    #
    # @safe_property
    # def publisher(self):
    #     return self.xpath('//dcterms:publisher/text()', first=True)
    #
    # def __iter__(self):
    #     for key in self._json_keys:
    #         yield key, getattr(self, key)
    #
    # def to_json(self):
    #     return ujson.dumps(dict(self))


class CatalogDump:

    def __init__(self, root):
        self.root = root

    def paths(self):
        pattern = os.path.join(self.root, '**/*.rdf')
        return glob.iglob(pattern, recursive=True)

    def books_iter(self):
        for path in self.paths():
            yield BookXML.from_file(path)

    def creator_term_names(self):
        """Gather set of all creator terms.
        """
        logger.info('Gathering creator terms.')

        names = set()
        for book in tqdm(self.books_iter()):
            for agent in book.creators_iter():
                names.update(agent.term_names())

        return names
