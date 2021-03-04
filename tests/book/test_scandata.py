import os, shutil
from unittest import TestCase

from ia_scribe.book.scandata import ScanData


class TestScanData(TestCase):
    def setUp(self):
        self.path = 'scandata_test'
        os.mkdir(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
            print("Directory removed")

# test if initialized scandata object has ppi field in bookData dict
    def test__init_ppi_for_bookdata(self):
        scandata = ScanData(self.path)
        self.assertIsNotNone(scandata.get_bookdata('ppi'))
