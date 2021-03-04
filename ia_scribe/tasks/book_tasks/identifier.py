import os

from ia_scribe.tasks.book_tasks.upload import purify_string, random_string, id_available
from ia_scribe.exceptions import ScribeException


def get_identifier_fysom(fysom):
    return new_get_identifier(fysom.obj)


def new_get_identifier(book):
    book.logger.debug('Getting identifier from path')
    id_file = os.path.join(book.path, 'identifier.txt')
    if book.has_identifier() and not os.path.exists(id_file):
        book.logger.debug('Using previously generated identifier {}'
                          .format(book.identifier))
        return

    if os.path.exists(id_file):
        try:
            identifier = open(id_file).read().strip()
            book.logger.debug('Using preset identifier ' + identifier)
            if hasattr(book, 'identifier'):
                if identifier != book['identifier']:
                    book.logger.warn(
                        'RESETTING IDENTIFIER from {old} to {new}'
                        .format(old=book.identifier, new=identifier)
                        )
        except Exception:
            raise ScribeException('File identifier.txt exists but cannot '
                                  'be read')
    else:
        return None
    return identifier


def make_identifier(title='unset', volume='00', creator='unset'):
    title = purify_string(title)
    volume = purify_string(volume)
    creator = purify_string(creator)
    num_attempts = 10
    for i in range(num_attempts):
        if i == 0:
            random_str = ''
        else:
            random_str = '_' + random_string()

        identifier = ('{title}{vol:>04}{creator}{rand}'
                      .format(title=title[:16], vol=volume[:4],
                              creator=creator[:4], rand=random_str))
        if id_available(identifier):
            return identifier
    raise ValueError('Failed to create new identifier for: '
                     'title={}, volume={}, creator={}'
                     .format(title, volume, creator))