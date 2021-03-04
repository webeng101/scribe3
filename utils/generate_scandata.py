import os, re
from ia_scribe.book import scandata

BOOKS_DIR = os.path.expanduser('~/scribe_books')

def list_books(books_dir = BOOKS_DIR):
    return [x[0] for x in os.walk(books_dir)]

def extract_number_from_file(filename):
    number= filename.split('.jpg')[0]
    ret = number.lstrip('0')
    return int(ret)

def build_scandata_from_image_stack(image_stack, target_file):
    sd = scandata.ScanData(target_file)
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
    scandata_file = dest_dir
    if not dest_dir:
        scandata_file = '/tmp/temp_scandata.json'
    print('checking that thumbs and files match')
    assert check_thumbs_and_files_match(directory) == True
    print('Building image stack')
    image_stack = build_image_stack(directory)
    print('Got {} leafs. Building scandata'.format(len(image_stack)))
    sd = build_scandata_from_image_stack(image_stack, scandata_file)
    print('Built scandata at {}'.format(scandata_file))
    check_for_missing_images(directory, sd)


if __name__ == '__main__':
    bd = '/home/vagrant/scribe_books/9abca055-7c01-43e4-94bf-ace43ba875f1'
    main(bd)