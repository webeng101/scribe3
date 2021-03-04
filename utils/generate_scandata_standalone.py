import sys, os, re, json
from collections import OrderedDict


SIDE_TO_DEGREE = {'left': -90, 'right': 90, 'foldout': 0}
BOOKS_DIR = os.path.expanduser('~/scribe_books')

def text_type(input_str):
    return str(input_str)

class ScanData(object):

    def __init__(self, path):
        self.path = path
        self.file_path =  os.path.join(path, 'scandata.json')
        self.data = {}
        self._load()

    def _load(self):
        scandata = {
            'bookData': {},
            'pageData': OrderedDict(),
        }
        self.data = scandata

    def _write(self):
        with open(self.file_path, 'w+') as f:
            f.write(self.dump())

    def dump(self):
        return json.dumps(self.data, indent=4, separators=(',', ': '))

    def save(self):
        self._write()

    def insert(self, leaf_number, side, page_type):
        new_leaf_data = {'pageType': page_type,
                         'ppi': 300,
                         'rotateDegree': SIDE_TO_DEGREE[side]}
        self.data['pageData'][text_type(leaf_number)] = new_leaf_data

    def get_max_leaf_number(self):
        leafs_data = self.data['pageData']
        return max(map(int, leafs_data)) if leafs_data else None

    def get_page_data(self, leaf_num):
        return self.data['pageData'].get(text_type(leaf_num), {})


def list_books(books_dir = BOOKS_DIR):
    return [x[0] for x in os.walk(books_dir)]

def extract_number_from_file(filename):
    number= filename.split('.jpg')[0]
    ret = number.lstrip('0')
    return int(ret)

def build_scandata_from_image_stack(image_stack, target_file):
    sd = ScanData(target_file)
    for image in image_stack:
        if image == '0000.jpg':
            leaf_number = 0
        else:
            leaf_number = extract_number_from_file(image)
        side = 'left' if leaf_number % 2 == 0 else 'right'
        page_type = 'Normal'
        if image == '0000.jpg':
            page_type = 'Color Card'
        elif image == '0001.jpg':
            page_type = 'Cover'
        elif leaf_number == len(image_stack) - 1:
            page_type = 'Color Card'
        sd.insert(leaf_number, side, page_type)
    return sd

def build_image_stack(book_dir):
    ret = [ k for k in next(os.walk(os.path.join(book_dir)))[2]
                if re.match('\d{4}\.jpg$', os.path.basename(k))]
    return sorted(ret)

def check_thumbs_and_files_match(book_dir):
    images_list = build_image_stack(book_dir)
    thumbs_list = build_image_stack(os.path.join(book_dir, 'thumbnails'))
    return images_list == thumbs_list

def check_for_missing_images(book_dir, scandata):
    book_path = book_dir
    scandata = scandata
    if not (book_path and scandata):
        return 'Cover image is missing!'
    max_leaf_number = scandata.get_max_leaf_number()
    if max_leaf_number is None or max_leaf_number < 1:
        return 'Cover image is missing'
    for leaf_number in range(max_leaf_number + 1):
        leaf_data = scandata.get_page_data(leaf_number)
        image_path = os.path.join(book_path, '{:04d}.jpg'.format(leaf_number))
        if not (leaf_data and os.path.exists(image_path)):
            if leaf_number == 0 or leaf_number == 1:
                return 'Cover image is missing!'
            return 'Image #{} is missing'.format(leaf_number)

def main(directory, dest_dir=None):
    if not dest_dir:
        dest_dir = directory
    print('checking that thumbs and files match')
    assert check_thumbs_and_files_match(directory) == True
    print('Building image stack')
    image_stack = build_image_stack(directory)
    print('Got {} leafs. Building scandata'.format(len(image_stack)))
    sd = build_scandata_from_image_stack(image_stack, dest_dir)
    print('Built scandata'.format(dest_dir))
    check_for_missing_images(directory, sd)
    print('Saving scandata at {}'.format(dest_dir))
    sd.save()

if __name__ == '__main__':
    main(sys.argv[1])
