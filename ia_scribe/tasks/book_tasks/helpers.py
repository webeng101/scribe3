import os, json, copy
from lxml import etree
from ia_scribe.libraries.xmltojson import xml2json

class Object(object):
    pass

def get_cluster_proxy_url_by_leaf(scc, item, leaf_num, **kwargs):
    PROXY_TYPE = 'sourceFileName'
    thumb_path_full = scc.get_page_data(leaf_num)[PROXY_TYPE]
    if thumb_path_full is None:
        return None
    rotation = int(scc.get_page_data(leaf_num)['rotateDegree']) % 360
    url = ('https://{server}/BookReader/BookReaderImages.php'
           '?zip={item_dir}/{item_identifier}_orig_jp2.tar&file={thumb_path}'
           '&rotate={rotation}&scale=6'
           .format(server=item.d1,
                   item_dir=item.dir,
                   item_identifier=item.identifier,
                   thumb_path=thumb_path_full,
                   rotation=rotation)
           )
    print("Proxy url -> ", url)
    return url


def validate_scandata_xml(sc_path, book):
    try:
        tree = etree.parse(sc_path, etree.XMLParser(encoding='utf-8'))
    except Exception as e:
        book.logger.error('Download book: Error pulling scandata from cluster.'
                          'Does scandata still exist on the cluster? You may need'
                          'to open this book in RePublisher to confirm.'
                          .format())
        raise e
    return tree


def create_normalized_scandata(tree, book):
    book.logger.info('Download book: Normalizing page numbers from cluster xml scandata')
    pd = tree.getroot().find('pageData')
    pd_counter = 0
    for jsel in pd.iterfind('page'):
        jsel.tag = 'p_' + jsel.attrib['leafNum']
        del jsel.attrib['leafNum']
        pd_counter += 1
    tree.write(os.path.join(book.path, 'scandata_norm.xml'), encoding='utf-8', pretty_print=True)
    book.logger.info('Download book: Done, normalized {} page numbers from scandata.xml'.format(pd_counter))
    scandata_xml = open(os.path.join(book.path,
                                     'scandata_norm.xml')).read()
    return scandata_xml


def convert_normalized_scandata_to_json(scandata_xml):
    obj = Object()
    obj.pretty = False
    json_data = json.loads(xml2json(scandata_xml, obj))
    return json_data


def build_bookdata(json_data, book):
    res = {}
    temp_bookData = copy.deepcopy(json_data['book']['bookData'])
    page_num_data_block = build_page_num_data_block(temp_bookData, book)
    for key, value in temp_bookData.items():
        if key != 'pageNumData':
            res[key] = value
    res['pageNumData'] = page_num_data_block
    return res


def build_page_num_data_block(temp_bookData, book):
    pageNumData_block = {}
    book.logger.info('Download book: Rewriting page number '
                     'assertions...')
    try:
        if 'pageNumData' in temp_bookData \
                and 'assertion' in temp_bookData['pageNumData']:
            if type(temp_bookData['pageNumData'][
                        'assertion']) is dict:
                book.logger.debug('download_books: Fixing single '
                                  'assertion dict -> list')
                a1 = temp_bookData['pageNumData']['assertion']
                temp_bookData['pageNumData']['assertion'] = [a1]
            for assertion in temp_bookData['pageNumData']['assertion']:
                pageNumData_block[assertion['leafNum']] = int(
                    assertion['pageNum'])
                book.logger.debug('Download book: Adding assertion {}:{}'.format(
                    assertion['leafNum'],
                    assertion['pageNum']))

        temp_bookData['pageNumData'] = pageNumData_block
        book.logger.info('Download book: Done. Imported {} assertions'
                         .format(len(list(pageNumData_block.keys()))))
    except Exception as e:
        book.logger.exception('Download book: No pageNumData block '
                              'found')
    return pageNumData_block


def build_pagedata(json_data, book):
    page_data = {}
    for page in json_data['book']['pageData']:
        leaf_nr = page.split('p_')[1]
        page_data[leaf_nr] = \
            json_data['book']['pageData'][page]

    book.logger.info('Download book: Imported {} p-nums into JSON '
                     'scandata'
                     .format(len(json_data['book']['pageData'])))
    return page_data