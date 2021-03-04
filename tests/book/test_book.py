from unittest import TestCase
from ia_scribe.book import book, smau
from uuid import uuid4
from ia_scribe import scribe_globals
import os, shutil
from fysom import Canceled

class TestEmptyBook(TestCase):
    def test_book_creation_noargs_raises_exception(self):
        self.assertRaises(Exception, book.Book)

class TestBookConstructor(TestCase):

    def setUp(self):
        self.uuid = str(uuid4())
        self.path = os.path.expanduser(os.path.join(scribe_globals.BOOKS_DIR, self.uuid))

    def tearDown(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
            print("file removed")

    def test_book_creation_succeeds_with_uuid(self):
        init_dict = {'uuid': self.uuid}
        book_object = book.Book(init_dict)
        self.assertEqual(book_object.path, self.path)
        self.assertEqual(book_object.uuid, self.uuid)
        self.assertEqual(book_object.status, 'uuid_assigned')
        assert os.path.exists(self.path)
        self.assertEqual(book_object.exists, True)
        self.assertEqual(book_object.STATUS_FILE, os.path.join(self.path, 'status'))
        self.assertEqual(book_object.STATUS_HISTORY_FILE, os.path.join(self.path, 'status_history'))
        self.assertIsNotNone(book_object.logger)

    def test_book_creation_with_natural_callback(self):
        fun = lambda x: x
        init_dict = {'uuid': self.uuid}
        book_object = book.Book(init_dict, callback=fun)
        self.assertIs(book_object.natural_callback, fun)


class TestBookBehavior(TestCase):

    def setUp(self):
        self.uuid = str(uuid4())
        self.book = book.Book({'uuid': self.uuid})
        self.path = self.book.path

    def tearDown(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
            print("file removed")

    def test_book_lock_set(self):
        set_lock_res = self.book.set_lock()
        res = self.book.is_locked()
        self.assertTrue(res)
        self.assertTrue(set_lock_res)

    def test_book_lock_set_unset(self):
        set_lock_res = self.book.set_lock()
        res = self.book.is_locked()
        self.assertTrue(set_lock_res)
        self.assertTrue(res)

        self.book.release_lock()
        res_2= self.book.is_locked()
        self.assertFalse(res_2)

class TestBookCallbacks(TestBookBehavior):


    def mock_callback(self, *args, **kwargs):
        print("called mock callback with", args, kwargs)
        self.callback_result_arg = args
        self.callback_result_kwargs = kwargs

    def setUp(self):
        self.uuid = str(uuid4())
        self.book = book.Book({'uuid': self.uuid}, callback = self.mock_callback)
        self.path = self.book.path
        self.book.status = 'identifier_assigned'

    def tearDown(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
            print("file removed")

    def test_book_status_change(self):
        self.assertRaises(Canceled, self.book.do_queue_processing)
        self.assertEqual(self.callback_result_arg[0], 'has_full_imgstack_wrapper')
        self.assertEqual(self.callback_result_arg[1], self.book )
        self.assertEqual(self.callback_result_arg[2], 'errors')
        self.callback_result_arg = None

'''
    def test_book_lifecycle(self):
        path_to_success = smau.get_transition_plan('scribing', 'uploaded')
        print "PTS", path_to_success, 'begin'
        for state in path_to_success[1:]:
            print 'state', state
            print 'self.book.status', self.book.status
            print smau.G.get_edge_data(self.book.status, state)
            print smau.G
            transition = smau.G.get_edge_data(self.book.status, state)['name']
            print 'transition',transition
            att = getattr(self.book, transition)
            try:
                print 'calling ', att
                res = att()
            except Exception as e:
                res = e
            self.assertIsNotNone(res)

'''


