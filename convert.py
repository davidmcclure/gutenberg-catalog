

import click
import os

from glob import glob
from tqdm import tqdm

from gutenberg_catalog.sources import BookXML


"""TODO
- handle missing authors
- editors
"""


@click.command()
@click.argument('src', type=click.Path(), default='cache')
@click.argument('dst', type=click.Path(), default='catalog.json')
def main(src, dst):
    """Dump JSON lines to file.
    """
    pattern = os.path.join(src, '**/*.rdf')

    paths = glob(pattern, recursive=True)

    with open(dst, 'w') as fh:
        for path in tqdm(paths):
            b = BookXML.from_file(path)
            print(b.to_json(), file=fh)


if __name__ == '__main__':
    main()
