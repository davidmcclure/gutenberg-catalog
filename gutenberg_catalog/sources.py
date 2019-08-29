

import os
import ujson
import glob

from lxml import etree
from tqdm import tqdm

from .utils import cached_property, parse_numeric, split_mime, parse_datetime
from . import logger


"""
infer namespaces from root
iter / dict
"""


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

    _dict_keys = ()

    @classmethod
    def from_file(cls, path):
        return cls(etree.parse(path))

    @classmethod
    def from_element(cls, element):
        return cls(etree.ElementTree(element))

    def __init__(self, root):
        self.root = root

    def __iter__(self):
        for key in self._dict_keys:
            yield key, getattr(self, key)

    def xpath(self, *args, **kwargs):
        return xpath(self.root, *args, **kwargs)


class Agent(Tree):

    _dict_keys = ('given_name', 'surname')

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


class BookXML(Tree):

    _dict_keys = ('id', 'title', 'authors')

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
        els = self.xpath('//dcterms:creator/pgterms:agent')
        return [Agent.from_element(el) for el in els]

    @cached_property
    def authors(self):
        return [dict(agent) for agent in self.agents]
