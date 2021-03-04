#!/usr/bin/env python


from os.path import join, dirname
import sys
parent_dir = join(dirname(__file__), '..')
sys.path.append(parent_dir)

import filecmp
import glob
import shutil

from ia_scribe.book.scandata import ScanData

# copy_scandata()
#_________________________________________________________________________________________
def copy_scandata(book_dir, src):
    '''
    book_dir is a tmpdir without a scandata file. copy src to book_dir/scandata.json,
    and then load it by creating a ScanData instance
    '''
    dst = join(book_dir, 'scandata.json')
    shutil.copyfile(src, dst)


# test_load_save()
#_________________________________________________________________________________________
def test_load_save(tmpdir):
    '''we should be able to load then save scandata without any changes'''

    for f in glob.glob(join(dirname(__file__), 'scandata/*')):
        book_dir = str(tmpdir)
        copy_scandata(book_dir, f)
        scandata = ScanData(book_dir)
        scandata.save('scandata_save.json')
        assert filecmp.cmp(f, join(str(tmpdir), 'scandata_save.json'))


# test_backfill()
#_________________________________________________________________________________________
def test_backfill(tmpdir):
    book_dir = str(tmpdir) #blank book_dir
    scandata = ScanData(book_dir)
    current_page_num = 1 #two pages, 0 and 1
    scandata.backfill(current_page_num)
    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "rotateDegree": 90
        }
    },
    "bookData": {}
}'''
    assert scandata.dump() == out


# test_update()
#_________________________________________________________________________________________
def test_update(tmpdir):
    book_dir = str(tmpdir) #blank book_dir
    scandata = ScanData(book_dir)
    scandata.update(0, 'left')
    scandata.update(1, 'right')
    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "rotateDegree": 90
        }
    },
    "bookData": {}
}'''
    assert scandata.dump() == out

    scandata.update(0, 'left', page_type='Color Card')
    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Color Card",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "rotateDegree": 90
        }
    },
    "bookData": {}
}'''
    assert scandata.dump() == out


# test_update_page()
#_________________________________________________________________________________________
def test_update_page(tmpdir):
    book_dir = str(tmpdir) #blank book_dir
    scandata = ScanData(book_dir)
    scandata.update(0, 'left')
    scandata.update(1, 'right')

    scandata.update_page(0, 'Cover', 101)
    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Cover",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "rotateDegree": 90
        }
    },
    "bookData": {
        "pageNumData": {
            "0": 101
        }
    }
}'''
    assert scandata.dump() == out


# test_delete_spread()
#_________________________________________________________________________________________
def test_delete_spread(tmpdir):
    book_dir = str(tmpdir) #blank book_dir
    scandata = ScanData(book_dir)
    scandata.update(0, 'left')
    scandata.update(1, 'right')
    scandata.update(2, 'left')
    scandata.update(3, 'right')

    leaf_leaf = 2
    right_leaf = 3
    end_leaf = 3
    scandata.delete_spread(leaf_leaf, right_leaf)
    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "rotateDegree": 90
        }
    },
    "bookData": {}
}'''
    assert scandata.dump() == out


# test_page_nums()
#_________________________________________________________________________________________
def test_page_nums(tmpdir):
    book_dir = str(tmpdir) #blank book_dir
    scandata = ScanData(book_dir)
    scandata.update(0, 'left')
    scandata.update(1, 'right')
    scandata.update(2, 'left')
    scandata.update(3, 'right')
    scandata.update(4, 'left')
    scandata.update(5, 'right')
    scandata.update(6, 'left')
    scandata.update(7, 'right')

    scandata.update_page(1, 'Normal', 1)
    scandata.update_page(3, 'Normal', 3)
    scandata.update_page(5, 'Normal', 50)
    scandata.compute_page_nums(7)

    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 1,
                "type": "assert"
            },
            "rotateDegree": 90
        },
        "2": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 2,
                "type": "match"
            },
            "rotateDegree": -90
        },
        "3": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 3,
                "type": "assert"
            },
            "rotateDegree": 90
        },
        "4": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 4,
                "type": "mismatch"
            },
            "rotateDegree": -90
        },
        "5": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 50,
                "type": "assert"
            },
            "rotateDegree": 90
        },
        "6": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 51,
                "type": "match"
            },
            "rotateDegree": -90
        },
        "7": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 52,
                "type": "match"
            },
            "rotateDegree": 90
        }
    },
    "bookData": {
        "pageNumData": {
            "1": 1,
            "3": 3,
            "5": 50
        }
    }
}'''
    print(scandata.dump())
    assert scandata.dump() == out


# test_delete_spread_page_nums()
#_________________________________________________________________________________________
def test_delete_spread_page_nums(tmpdir):
    book_dir = str(tmpdir) #blank book_dir
    scandata = ScanData(book_dir)
    scandata.update(0, 'left')
    scandata.update(1, 'right')
    scandata.update(2, 'left')
    scandata.update(3, 'right')
    scandata.update(4, 'left')
    scandata.update(5, 'right')

    leaf_leaf = 2
    right_leaf = 3
    end_leaf = 5

    scandata.update_page(1, 'Normal', 1)
    scandata.update_page(5, 'Normal', 3)
    scandata.compute_page_nums(end_leaf)

    scandata.delete_spread(leaf_leaf, right_leaf)
    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 1,
                "type": "assert"
            },
            "rotateDegree": 90
        },
        "2": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 2,
                "type": "match"
            },
            "rotateDegree": -90
        },
        "3": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 3,
                "type": "assert"
            },
            "rotateDegree": 90
        }
    },
    "bookData": {
        "pageNumData": {
            "1": 1,
            "3": 3
        }
    }
}'''
    print(scandata.dump())
    assert scandata.dump() == out

    #now, clear the first assertion
    end_leaf = 3
    scandata.update_page(1, 'Normal', None)
    scandata.compute_page_nums(end_leaf)

    out = \
'''{
    "pageData": {
        "0": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "1": {
            "pageType": "Normal",
            "rotateDegree": 90
        },
        "2": {
            "pageType": "Normal",
            "rotateDegree": -90
        },
        "3": {
            "pageType": "Normal",
            "pageNumber": {
                "num": 3,
                "type": "assert"
            },
            "rotateDegree": 90
        }
    },
    "bookData": {
        "pageNumData": {
            "3": 3
        }
    }
}'''
    print(scandata.dump())
    assert scandata.dump() == out
