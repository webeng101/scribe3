#!/usr/bin/env python

import fcntl
import json
import traceback
from codecs import open
from collections import OrderedDict

from os.path import exists, join, splitext

from kivy.compat import text_type
from kivy.event import EventDispatcher
from sortedcontainers import SortedSet

from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
CONFIG = Scribe3Configuration()

PT_NORMAL = 'Normal'
PT_COVER = 'Cover'
PT_TITLE = 'Title'
PT_COPYRIGHT = 'Copyright'
PT_CONTENTS = 'Contents'
PT_TISSUE = 'Tissue'
PT_COLOR_CARD = 'Color Card'
PT_CHAPTER = 'Chapter'
PT_WHITE_CARD = 'White Card'
PT_FOLDOUT = 'Foldout'
PT_ABSTRACT = 'Abstract'
PT_APPENDIX = 'Appendix'
PT_CONTRIBUTIONS = 'Contributions'
PT_DELETE = 'Delete'
PT_FOREWORD = 'Foreword'
PT_GLOSSARY = 'Glossary'
PT_INDEX = 'Index'
PT_INSCRIPTIONS = 'Inscriptions'
PT_INTRODUCTION = 'Introduction'
PT_LIST_OF_FIGURES = 'List of Figures'
PT_LIST_OF_TABLES = 'List of Tables'
PT_NOTES = 'Notes'
PT_PREFACE = 'Preface'
PT_QUOTATIONS = 'Quotations'
PT_REFERENCE = 'Reference'
PT_SUBCHAPTER = 'Subchapter'
PT_SUBSUBCHAPTER = 'SubSubchapter'

VALID_PAGE_TYPES = {
    PT_NORMAL, PT_COVER, PT_TITLE, PT_COPYRIGHT, PT_CONTENTS, PT_TISSUE,
    PT_COLOR_CARD, PT_CHAPTER, PT_WHITE_CARD, PT_FOLDOUT, PT_ABSTRACT,
    PT_APPENDIX, PT_CONTRIBUTIONS, PT_DELETE, PT_FOREWORD, PT_GLOSSARY,
    PT_INDEX, PT_INSCRIPTIONS, PT_INTRODUCTION, PT_LIST_OF_FIGURES,
    PT_LIST_OF_TABLES, PT_NOTES, PT_PREFACE, PT_QUOTATIONS, PT_REFERENCE,
    PT_SUBCHAPTER, PT_SUBSUBCHAPTER
}
KEY_NOTE = 'note'
KEY_BOOK_INTERNAL_NOTE = 'internalNotes'
SIDE_TO_DEGREE = {'left': -90, 'right': 90, 'foldout': 0}
FILE_PATH_KEYS = {
    'sourceFileName', 'origFileName', 'proxyFileName', 'proxyFullFileName'
}


class ScandataCache(object):

    def __init__(self, keys, load=1000):
        self._cache = {x: SortedSet(load=load) for x in keys}
        self._report = set()

    def __getitem__(self, item):
        return self._cache[item]

    def add(self, key, value):
        self._cache[key].add(value)
        self._report.add(key)

    def discard(self, key, value):
        self._cache[key].discard(value)
        self._report.add(key)

    def pop_change_report(self):
        report = self._report
        self._report = set()
        return report

    def clear(self):
        for sorted_set in self._cache.values():
            sorted_set.clear()
        for key in self._cache:
            self._report.add(key)


class ScanData(EventDispatcher):
    '''Manipulates book scandata which is saved to <book_dir>/scandata.json 
    file. All keys are in lower camel case style.
    '''

    __events__ = ('on_leafs',)

    def __init__(self, book_dir, downloaded=False, **kwargs):
        super(ScanData, self).__init__(**kwargs)
        self.scandata = None
        self.book_dir = book_dir
        self._downloaded = downloaded
        self._cache = None
        self._load()
        self.default_ppi = self._init_ppi_for_bookdata()

    def _load(self):
        scandata = {
            'bookData': {},
            'pageData': OrderedDict(),
        }
        cache = ScandataCache(VALID_PAGE_TYPES | {KEY_NOTE})
        if self.book_dir is None:
            self._cache = cache
            self.scandata = scandata
        path = join(self.book_dir, 'scandata.json')
        if not exists(path):
            self._cache = cache
            self.scandata = scandata
            self.dispatch('on_leafs', cache.pop_change_report())
            return
        f = None
        try:
            f = open(path, 'rb', 'utf-8')
            tmp = json.load(f)
            tmp_page_data = tmp.get('pageData', None)
            if tmp_page_data:
                max_leaf_number = max(map(int, tmp_page_data))
                for leaf_int in range(max_leaf_number + 1):
                    leaf_str = str(leaf_int)
                    leaf_data = tmp_page_data.get(leaf_str, None)
                    if not leaf_data:
                        continue
                    page_type = leaf_data.get('pageType', None)
                    if page_type not in VALID_PAGE_TYPES:
                        continue
                    scandata['pageData'][leaf_str] = leaf_data
                    cache.add(page_type, leaf_int)
                    if KEY_NOTE in leaf_data:
                        cache.add(KEY_NOTE, leaf_int)
            page_data = scandata['pageData']
            tmp_book_data = tmp.get('bookData', None)
            if tmp_book_data:
                page_num_data = tmp_book_data.get('pageNumData', None)
                if self._downloaded and page_num_data:
                    assertions = page_num_data.get('assertion', None)
                    if assertions:
                        # Delete assertions where leafNum doesn't exists in
                        # pageData
                        for_deletion = []
                        for index, assertion in enumerate(assertions):
                            if not page_data.get(assertion['leafNum'], None):
                                for_deletion.append(index)
                        while for_deletion:
                            assertions.pop(for_deletion.pop())
                elif page_num_data:
                    # Delete leaf number for pageNumData if it doesn't exists
                    # in pageData
                    for_deletion = []
                    for leaf_str in page_num_data:
                        if not page_data.get(leaf_str, None):
                            for_deletion.append(leaf_str)
                    while for_deletion:
                        page_num_data.pop(for_deletion.pop())
                scandata['bookData'] = tmp_book_data
                if self._downloaded:
                    # Ensure that leafCount is correct
                    tmp_book_data['leafCount'] = text_type(len(page_data))
        except Exception:
            traceback.print_exc()
            print(('Could not load scandata from {}'.format(path)))
        finally:
            if f:
                f.close()
        self._cache = cache
        self.scandata = scandata
        self.dispatch('on_leafs', cache.pop_change_report())

    def save(self, name='scandata.json'):
        if self.book_dir is None:
            return
        path = join(self.book_dir, name)
        try:
            f = open(path, 'wb', 'utf-8')
            fcntl.lockf(f, fcntl.LOCK_EX)
            json.dump(self.scandata, f, indent=4, separators=(',', ': '),
                      ensure_ascii=False)
            fcntl.lockf(f, fcntl.LOCK_UN)
            f.close()
        except Exception:
            traceback.print_exc()
            print(('Could not save scandata to {}'.format(path)))

    def has_leafs(self, key=PT_FOLDOUT):
        return bool(self._cache[key])

    def iter_leafs(self, key=PT_FOLDOUT):
        return iter(self._cache[key])

    def iter_flagged_leafs(self):
        for leaf_str, leaf_data in self.scandata['pageData'].items():
            if leaf_data.get('TTSflag', 0) is not None:
                if int(leaf_data.get('TTSflag', 0)) == 1:
                    yield int(leaf_str)

    def iter_key(self, key):
        for leaf_str, leaf_data in self.scandata['pageData'].items():
            if leaf_data.get(key) is not None:
                    yield leaf_data.get(key)

    def get_previous_leaf(self, leaf_number, key=PT_FOLDOUT):
        leafs = self._cache[key]
        if leafs:
            first, last = leafs[0], leafs[-1]
            if first > leaf_number:
                return None
            elif last < leaf_number:
                return last
            index = leafs.bisect_left(leaf_number)
            return None if index == 0 else leafs[index - 1]
        return None

    def get_next_leaf(self, leaf_number, key=PT_FOLDOUT):
        leafs = self._cache[key]
        if leafs:
            first, last = leafs[0], leafs[-1]
            if first > leaf_number:
                return first
            elif last < leaf_number:
                return None
            index = leafs.bisect_right(leaf_number)
            return None if index == len(leafs) else leafs[index]
        return None

    def clear(self):
        self.scandata['bookData'].clear()
        self.scandata['pageData'].clear()
        self._cache.clear()
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def backfill(self, curr_page_num, page_type=PT_NORMAL):
        '''If we are adding images to a book that was started before
        `scandata.json` files were being written, backfill the data using
        default values.
        '''
        if self._downloaded:
            return
        if curr_page_num == 0:
            return
        page_data_keys = set(self.scandata['pageData'])
        # Note that xrange is not inclusive, so we add one to the end
        for i in range(curr_page_num + 1):
            if text_type(i) not in page_data_keys:
                side = 'left' if i % 2 == 0 else 'right'
                self.update(i, side, page_type)

    def get_page_data(self, leaf_num):
        return self.scandata['pageData'].get(text_type(leaf_num), {})

    def update(self, leaf_number, side, page_type=PT_NORMAL):
        '''Update or set pageData['leaf_number'] with `rotateDegree` computed
        from side.
        '''
        page_data = self.get_page_data(leaf_number)
        old_page_type = page_data['pageType']
        if not self._downloaded:
            page_data['rotateDegree'] = SIDE_TO_DEGREE[side]
        elif page_data.get('rotateDegree', None) is None:
            page_data['rotateDegree'] = SIDE_TO_DEGREE[side]
        page_data['pageType'] = page_type
        self.scandata['pageData'][text_type(leaf_number)] = page_data
        self._cache.add(page_type, leaf_number)
        self._cache.add(old_page_type, leaf_number)
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def insert(self, leaf_number, side, page_type=PT_NORMAL):
        if self._downloaded:
            self._downloaded_insert(leaf_number, side, page_type)
        else:
            self._default_insert(leaf_number, side, page_type)

    def _default_insert(self, leaf_number, side, page_type):
        page_data = self.scandata['pageData']
        page_num_data = self.scandata['bookData'].get('pageNumData', None)
        new_page_num_data = {}
        max_leaf_number = self.get_max_leaf_number()
        total = 0 if max_leaf_number is None else max_leaf_number + 1
        new_leaf_data = {'pageType': page_type,
                         'ppi': self.default_ppi,
                         'rotateDegree': SIDE_TO_DEGREE[side]}
        # If we are not appending, but actually inserting
        if leaf_number < total:
            stack = []
            # Put all the leafs after insertion point into a stack
            for leaf_int in range(total - 1, leaf_number - 1, -1):
                leaf_str = text_type(leaf_int)
                leaf_data = page_data.pop(leaf_str, None)
                if not leaf_data:
                    stack.append(None)
                    continue
                self._cache.discard(leaf_data['pageType'], leaf_int)
                self._cache.discard(KEY_NOTE, leaf_int)
                stack.append(leaf_data)

            # Porting assertions for leafs BEFORE insertion point
            for leaf in page_data.items():
                if 'pageNumber' in leaf[1]:
                    if leaf[1]['pageNumber']['type'] == 'assert':
                        leaf_str = text_type(leaf[0])
                        new_page_num_data[leaf_str] = leaf[1]['pageNumber']['num']

            # drop in the new leaf
            page_data[text_type(leaf_number)] = new_leaf_data

            # add leafs from the stack and update references to assertions
            for leaf_int in range(leaf_number + 1, total + 1):
                leaf_str = text_type(leaf_int)
                leaf_data = stack.pop()
                if not leaf_data:
                    continue
                if 'pageNumber' in leaf_data:
                    assertion = leaf_data.pop('pageNumber')
                    if assertion['type'] == 'assert':
                        new_page_num_data[text_type(leaf_int)] = assertion['num']

                page_data[leaf_str] = leaf_data
                self._cache.add(leaf_data['pageType'], leaf_int)
                if KEY_NOTE in leaf_data:
                    self._cache.add(KEY_NOTE, leaf_int)
                # self.compute_page_nums(total + 1)

            # Replace old assertion block with new one
            if page_num_data:
                self.scandata['bookData']['pageNumData'] = new_page_num_data
                self.compute_page_nums(total + 1 )

        # This is an insertion at the end
        else:
            page_data[text_type(leaf_number)] = new_leaf_data

        self._cache.add(page_type, leaf_number)
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def _downloaded_insert(self, leaf_number, side, page_type):
        page_data = self.scandata['pageData']
        max_leaf_number = self.get_max_leaf_number()
        total = 0 if max_leaf_number is None else max_leaf_number + 1
        new_leaf_data = {
            'pageType': page_type,
            'ppi': text_type(self.default_ppi),
            'rotateDegree': text_type(SIDE_TO_DEGREE[side]),
            'type': 'INSERT',
            'handSide': 'LEFT' if leaf_number % 2 == 0 else 'RIGHT'
        }
        new_page_num_data = {}
        book_data = self.scandata['bookData']
        if leaf_number < total:
            stack = []
            for leaf_int in range(total - 1, leaf_number - 1, -1):
                leaf_data = page_data.pop(text_type(leaf_int), None)
                if not leaf_data:
                    stack.append(None)
                    continue
                self._cache.discard(leaf_data['pageType'], leaf_int)
                self._cache.discard(KEY_NOTE, leaf_int)
                stack.append(leaf_data)
            page_data[text_type(leaf_number)] = new_leaf_data

            page_num_data = book_data.get('pageNumData', None)

            # Porting assertions for leafs BEFORE insertion point
            if page_num_data:
                assertions = page_num_data.get('assertion', None)
                if assertions:
                    for item in assertions:
                        leaf_int = int(item['leafNum'])
                        if leaf_int >= leaf_number:
                            item['leafNum'] = text_type(leaf_int + 1)

            for leaf_int in range(leaf_number + 1, total + 1):
                leaf_data = stack.pop()
                if not leaf_data:
                    continue
                # self._update_file_paths(leaf_data, leaf_int)
                hand_side = 'LEFT' if leaf_int % 2 == 0 else 'RIGHT'
                leaf_data['handSide'] = hand_side
                page_data[text_type(leaf_int)] = leaf_data
                self._cache.add(leaf_data['pageType'], leaf_int)
                if KEY_NOTE in leaf_data:
                    self._cache.add(KEY_NOTE, leaf_int)
            self.compute_page_nums(total + 1)
        else:
            page_data[text_type(leaf_number)] = new_leaf_data

        self._cache.add(page_type, leaf_number)
        book_data['leafCount'] = text_type(len(page_data))
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def _update_file_paths(self, leaf_data, leaf_number):
        for file_key in FILE_PATH_KEYS:
            full_path = leaf_data.get(file_key, None)
            if full_path is not None:
                path, ext = splitext(full_path)
                name = path.split('_')[-1]
                path = path.rstrip(name + ext)
                new_name = text_type(leaf_number).rjust(4, '0')
                leaf_data[file_key] = path + new_name + ext

    def update_page(self, leaf_number, page_type, page_number):
        if page_type not in VALID_PAGE_TYPES:
            return
        page_data = self.get_page_data(leaf_number)
        old_page_type = page_data['pageType']
        page_data['pageType'] = page_type
        self.update_page_assertion(leaf_number, page_number)
        self._cache.add(page_type, leaf_number)
        self._cache.discard(old_page_type, leaf_number)
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def get_page_assertion(self, leaf_number):
        book_data = self.scandata['bookData']
        page_num_data = book_data.get('pageNumData', None)
        if not page_num_data:
            return None
        if self._downloaded:
            assertions = page_num_data.get('assertion', None)
            if assertions:
                for item in assertions:
                    if int(item['leafNum']) == leaf_number:
                        return int(item['pageNum'])
            return None
        else:
            return page_num_data.get(text_type(leaf_number), None)

    def update_page_assertion(self, leaf_number, page_number):
        '''Updates pageNumData dict by setting `page_number` to key
        `leaf_num` or removing `leaf_num` entry if `page_number` is None.
        '''
        book_data = self.scandata['bookData']
        page_num_data = book_data.get('pageNumData', None)
        if page_num_data is None:
            book_data['pageNumData'] = page_num_data = {}
        if self._downloaded:
            assertions = page_num_data.get('assertion', None)
            if assertions is None:
                page_num_data['assertion'] = assertions = []
            if page_number is not None:
                for item in assertions:
                    if int(item['leafNum']) == leaf_number:
                        item['pageNum'] = text_type(page_number)
                        return
                assertions.append({'leafNum': text_type(leaf_number),
                                   'pageNum': text_type(page_number)})
            else:
                for index, item in enumerate(assertions):
                    if int(item['leafNum']) == leaf_number:
                        assertions.pop(index)
                        return
        else:
            if page_number is not None:
                page_num_data[text_type(leaf_number)] = page_number
            else:
                page_num_data.pop(text_type(leaf_number), None)

    def update_rotate_degree(self, leaf_number, degree):
        data = self.get_page_data(leaf_number)
        degree = text_type(degree) if self._downloaded else degree
        data['rotateDegree'] = degree
        self.scandata['pageData'][text_type(leaf_number)] = data

    def update_page_type(self, leaf_number, page_type):
        leaf_data = self.scandata['pageData'].get(text_type(leaf_number), None)
        if leaf_data is not None:
            old_page_type = leaf_data['pageType']
            leaf_data['pageType'] = page_type
            self._cache.add(page_type, leaf_number)
            self._cache.discard(old_page_type, leaf_number)
            self.dispatch('on_leafs', self._cache.pop_change_report())

    def _init_ppi_for_bookdata(self):
        should_save = False
        ppi = self.get_bookdata('ppi')
        if ppi is None or int(float(ppi)) < 1:
            ppi = CONFIG.get('camera_ppi')
            if ppi is None or int(float(ppi)) < 1:
                ppi = scribe_globals.DEFAULT_PPI
            should_save = True
        elif ppi == str(float(ppi)):
            ppi = int(float(ppi))
            should_save = True
        if should_save:
            self.set_bookdata('ppi', ppi)
        return ppi

    def get_ppi(self, leaf_number):
        data = self.get_page_data(leaf_number)
        return data.get('ppi', None)

    def set_ppi(self, leaf_number, ppi_value):
        data = self.get_page_data(leaf_number)
        ppi_value = text_type(ppi_value) if self._downloaded else ppi_value
        data['ppi'] = ppi_value
        self.scandata['pageData'][text_type(leaf_number)] = data

    def get_internal_book_notes(self):
        return self.get_bookdata(KEY_BOOK_INTERNAL_NOTE)

    def set_internal_book_notes(self, note):
        self.set_bookdata(KEY_BOOK_INTERNAL_NOTE, note)

    def get_bookdata(self, key):
        book_data = self.scandata['bookData']
        return book_data.get(key, None)

    def set_bookdata(self, key, value):
        if value == '' or value is None:
            self.scandata['bookData'].pop(key, None)
        else:
            self.scandata['bookData'][key] = value

    def get_capture_time(self, leaf_number):
        leaf_data = self.get_page_data(leaf_number)
        if leaf_data:
            capture_time = leaf_data.get('cameraTime', None)
            return None if capture_time is None else float(capture_time)
        return None

    def set_capture_time(self, leaf_number, capture_time):
        leaf_data = self.get_page_data(leaf_number)
        leaf_data['cameraTime'] = capture_time
        self.scandata['pageData'][text_type(leaf_number)] = leaf_data

    def set_blurriness(self, leaf_number, is_blurry, blurriness_value):
        leaf_data = self.get_page_data(leaf_number)
        leaf_data['blurriness'] = blurriness_value
        leaf_data['is_blurry'] = is_blurry

    def get_note(self, leaf_number):
        leaf_data = self.get_page_data(leaf_number)
        return leaf_data.get(KEY_NOTE) if leaf_data else None

    def set_note(self, leaf_number, note):
        leaf_data = self.get_page_data(leaf_number)
        if note:
            leaf_data[KEY_NOTE] = note
            self._cache.add(KEY_NOTE, leaf_number)
        else:
            leaf_data.pop(KEY_NOTE, None)
            self._cache.discard(KEY_NOTE, leaf_number)
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def delete_spread(self, left_leaf_num, right_leaf_num):
        end_leaf_num = self.get_max_leaf_number()
        page_data = self.scandata['pageData']
        book_data = self.scandata['bookData']
        page_num_data = book_data.get('pageNumData', None)

        # Pop the spread
        for leaf_int in range(left_leaf_num, right_leaf_num + 1):
            # If there is an asserted page number, delete the assertion from
            # pageNumData block
            leaf_str = text_type(leaf_int)
            if page_num_data and leaf_str in page_num_data:
                del page_num_data[leaf_str]
            leaf_data = page_data.pop(leaf_str, None)
            if leaf_data:
                self._cache.discard(leaf_data['pageType'], leaf_int)
                self._cache.discard(KEY_NOTE, leaf_int)

        if self._downloaded:
            book_data['leafCount'] = text_type(len(page_data))

        # If we are deleting at the end
        if end_leaf_num == right_leaf_num:
            if page_num_data is None:
                return
            if self._downloaded:
                assertions = page_num_data.get('assertion', None)
                if assertions:
                    for_deletion = []
                    leaf_ints = set(range(left_leaf_num, right_leaf_num + 1))
                    for index, item in enumerate(assertions):
                        leaf_int = int(item['leafNum'])
                        if leaf_int in leaf_ints:
                            for_deletion.append(index)
                            leaf_ints.remove(leaf_int)
                        if not leaf_ints:
                            break
                    while for_deletion:
                        assertions.pop(for_deletion.pop())
            else:
                for leaf_int in range(left_leaf_num, right_leaf_num + 1):
                    page_num_data.pop(text_type(leaf_int), None)
            self.dispatch('on_leafs', self._cache.pop_change_report())
            return

        # if we are deleting in the middle, split at the deletion point
        # and cycle through the leafs up to the end and, if deleting a
        # single-page spread, swap sides accordingly
        delta = right_leaf_num - left_leaf_num + 1
        should_update_hand_side = delta % 2 != 0
        # Update leaf numbers because insert is not at the end
        for leaf_int in range(right_leaf_num + 1, end_leaf_num + 1):
            leaf_str = text_type(leaf_int)
            leaf_data = page_data.get(leaf_str, None)
            if not leaf_data:
                continue
            # move the leaf back
            prev_leaf_int = leaf_int - delta
            # Add handSide if the book has been downloaded
            if self._downloaded and should_update_hand_side:
                hand_side = 'LEFT' if prev_leaf_int % 2 == 0 else 'RIGHT'
                leaf_data['handSide'] = hand_side
                # self._update_file_paths(leaf_data, prev_leaf_int)
            # Finally, add the constructed leaf_data to page_data in the new
            # position
            page_data[text_type(prev_leaf_int)] = leaf_data
            # and delete the original leaf. This strikes me as dangerous.
            del page_data[leaf_str]
            self._cache.discard(leaf_data['pageType'], leaf_int)
            self._cache.add(leaf_data['pageType'], prev_leaf_int)
            if KEY_NOTE in leaf_data:
                self._cache.discard(KEY_NOTE, leaf_int)
                self._cache.add(KEY_NOTE, prev_leaf_int)

        # If there is no assertion, we're done!
        if page_num_data is None:
            return

        # Fix page assertions
        # sorted_leafs is a list of strings, but sorted by int value
        if self._downloaded:
            assertions = page_num_data.get('assertion', None)
            if assertions:
                assertions = {x['leafNum']: x['pageNum'] for x in assertions}
                sorted_leafs = sorted(assertions, key=int)
                for leaf_str in sorted_leafs:
                    leaf_int = int(leaf_str)
                    if leaf_int > right_leaf_num + 1:
                        assertions[text_type(leaf_int - delta)] = assertions[leaf_str]
                        del assertions[leaf_str]
                page_num_data['assertion'] = [
                    {'leafNum': k, 'pageNum': v} for k, v in assertions.items()
                ]
        else:
            sorted_leafs = sorted(page_num_data, key=int)
            for leaf_str in sorted_leafs:
                leaf_int = int(leaf_str)
                if leaf_int > right_leaf_num:
                    prev_leaf_str = text_type(leaf_int - delta)
                    page_num_data[prev_leaf_str] = page_num_data[leaf_str]
                    del page_num_data[leaf_str]
        self.compute_page_nums(end_leaf_num)
        self.dispatch('on_leafs', self._cache.pop_change_report())

    def get_page_num(self, leaf_num):
        page_data = self.get_page_data(leaf_num)
        return page_data.get('pageNumber', None)

    def add_page_num(self, leaf_num, page_num, page_num_type):
        page_data = self.get_page_data(leaf_num)
        if not page_data:
            # Only update existing page_data
            return
        if self._downloaded:
            page_num = text_type(page_num)
        page_data['pageNumber'] = {'num': page_num, 'type': page_num_type}

    def add_page_nums(self, first_leaf_num, first_page_num, range_end, page_num_type):
        '''range_end is last leaf + 1'''
        page_num = first_page_num
        for leaf_num in range(first_leaf_num, range_end):
            self.add_page_num(leaf_num, page_num, page_num_type)
            page_num += 1

    def clear_page_nums(self, first_leaf_num, range_end):
        for leaf_num in range(first_leaf_num, range_end):
            page_data = self.get_page_data(leaf_num)
            page_data.pop('pageNumber', None)

    def compute_page_nums(self, end_leaf_num):
        book_data = self.scandata['bookData']
        page_num_data = book_data.get('pageNumData', None)
        if not page_num_data:
            self.clear_page_nums(0, self.get_max_leaf_number())
            return
        if self._downloaded:
            assertions = page_num_data.get('assertion', [])
            page_num_data = {
                x['leafNum']: int(x['pageNum']) for x in assertions
            }
        asserted_leaf_nums = sorted(page_num_data, key=int)
        # Clear page number for every leaf before the first asserted leaf
        # if there are no asserted leafs, clear all page numbers
        if len(asserted_leaf_nums) == 0:
            clear_leaf_range = end_leaf_num + 1
        else:
            clear_leaf_range = int(asserted_leaf_nums[0])
        self.clear_page_nums(0, clear_leaf_range)
        prev_leaf_num = None
        prev_page_num = None
        for leaf_num in asserted_leaf_nums:
            self.add_page_num(leaf_num, page_num_data[leaf_num], 'assert')
            if prev_leaf_num is None:
                prev_leaf_num = leaf_num
                prev_page_num = page_num_data[leaf_num]
                continue
            prev_leaf_int = int(prev_leaf_num)
            leaf_int = int(leaf_num)
            page_num = page_num_data[leaf_num]
            if (leaf_int - prev_leaf_int) == (page_num - prev_page_num):
                self.add_page_nums(
                    prev_leaf_int + 1, prev_page_num + 1, leaf_int, 'match'
                )
            else:
                self.add_page_nums(
                    prev_leaf_int + 1, prev_page_num + 1, leaf_int, 'mismatch'
                )
            prev_leaf_num = leaf_num
            prev_page_num = page_num_data[leaf_num]
        # From the last assertion, carry page nums forward to the end
        if prev_leaf_num is not None:
            self.add_page_nums(int(prev_leaf_num) + 1,
                               int(prev_page_num) + 1,
                               end_leaf_num + 1,
                               'match')

    def dump_raw(self):
        return self.scandata

    def dump(self):
        return json.dumps(self.scandata, indent=4, separators=(',', ': '))

    def get_max_leaf_number(self):
        leafs_data = self.scandata['pageData']
        return max(map(int, leafs_data)) if leafs_data else None

    def count_pages(self):
        return len(self.scandata['pageData'])

    def count_notes(self):
        return len(self.get_notes())

    def get_notes(self):
        return [x for x in self.iter_key(KEY_NOTE)]

    def on_leafs(self, report):
        pass
