import os
from pprint import pformat
import unidecode

from kivy.compat import string_types, text_type
from kivy.logger import Logger
from lxml import etree

from ia_scribe import scribe_globals

# Default ordered keys used by UI
MD_ORDERED_KEYS = ['title', 'creator', 'language', 'isbn', 'publisher',
                   'volume', 'date', 'issn', 'operator', 'scanningcenter']

# Key options used to add new key in metadata
MD_CUSTOM_KEY_OPTIONS = ['title', 'creator','date', 'isbn', 'issn', 'language', 'publisher',
                         'page-progression', 'volume', 'custom']

MD_REQUIRED_KEYS = set()
MD_NEW_BOOK_KEYS = {'title', 'creator', 'language', 'isbn', 'publisher', 'scanningcenter',
                    'volume', 'date'} | MD_REQUIRED_KEYS
MD_READONLY_KEYS = {'identifier', 'operator', 'notes', 'tts_version',
                    'source', 'curatenote', 'scanningcenter',
                    'sponsor', 'partner', 'contributor', 'rcs_key', 'collection_set',
                    }
MD_ACRONYMS = {'isbn', 'issn', 'ppi'}
MD_KEYS_WITH_SINGLE_VALUE = {'identifier', 'title', 'volume', 'operator', 'page-progression',
                             'ppi', 'notes', 'source', 'tts_version', 'boxid',
                             'old_pallet', 'scanningcenter', 'rcs_key', 'collection_set',
                             'sponsor', 'partner', 'contributor'}


def get_metadata(meta_dir, file_name='metadata.xml'):
    md = {}
    meta_dir_expanded = os.path.expanduser(meta_dir)
    meta_file = os.path.join(meta_dir_expanded, file_name)
    if os.path.exists(meta_file):
        tree = etree.parse(meta_file, etree.XMLParser(encoding='utf-8'))
        root = tree.getroot()
        for key in root:
            if key.text is not None:
                # this can only be alphanumeric: https://archive.org/services/docs/api/metadata-schema/index.html#internet-archive-metadata
                key_tag = unidecode.unidecode(key.tag)
                if key_tag in md:
                    if isinstance(md[key_tag], list):
                        md[key_tag].append(key.text.encode('utf-8').decode('utf-8'))
                    elif isinstance(md[key_tag], string_types):
                        md[key_tag] = [md[key_tag], key.text.encode('utf-8').decode('utf-8')]
                else:
                    md[key_tag] = key.text.encode('utf-8').decode('utf-8')
    return md


def set_metadata(md, meta_dir, file_name='metadata.xml', root_element='metadata'):
    meta_dir_expanded = os.path.expanduser(meta_dir)
    meta_file = os.path.join(meta_dir_expanded, file_name)
    root = etree.Element(root_element)
    for key, value in md.items():
        if isinstance(value, list):
            for item in value:
                child = etree.SubElement(root, key)
                child.text = item
        else:
            if value is not None:
                child = etree.SubElement(root, key)
                child.text = text_type(value)
    tree = etree.ElementTree(root)
    tree.write(meta_file, encoding='utf-8', pretty_print=True)
    Logger.info('Metadata: Saved at path "{}" with root element "{}"{}{}'
                .format(meta_file, root_element, os.linesep, pformat(md)))


def get_sc_metadata():
    return get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)

def get_collections_from_metadata():
    """
        Get number of collection sets
    :return:
    """
    conf_file = os.path.join(scribe_globals.CONFIG_DIR,
                             'collections_metadata.xml')
    if not os.path.isfile(conf_file):
        top = etree.Element('collections')
        tree = etree.ElementTree(top)
        tree.write(conf_file, encoding='utf-8', pretty_print=True)
        return []
    parser = etree.XMLParser(encoding='utf-8')
    root = etree.parse(conf_file, parser).getroot()
    cols = []
    for child_of_root in root:
        if child_of_root.tag == 'set':
            cols.append(child_of_root.text)
    return cols


def is_valid_issn(issn):
    if not issn:
        return False
    cleaned = issn.replace('-', '').replace(' ', '').upper()
    if len(cleaned) != 8:
        return False
    if not cleaned[:-1].isdigit():
        return False
    check = (11 - sum((8 - i) * int(n) for i, n in enumerate(cleaned))) % 11
    check = 'X' if check == 10 else str(check)
    if check != cleaned[-1]:
        return False
    return True

def get_sc_metadata():
    return get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)

def set_sc_metadata(md):
    import copy
    # TODO: Try catch, dependency on figuring out what the best course of
    # action would be
    config = get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)
    # Make a copy of it
    new_config = copy.deepcopy(config)
    # Load all textboxs in the interface in a dict
    # For each of them, get the value in the textbox  and assign it to the
    # new copy of the dict
    for k, v in md.items():
        Logger.debug('Scancenter metadata: {0} -> {1}'.format(k, v))
        new_config[k] = v
    # if the two dicts are different, set the new one as default
    if config != new_config:
        set_metadata(new_config, scribe_globals.SCANCENTER_METADATA_DIR)
    return get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)
