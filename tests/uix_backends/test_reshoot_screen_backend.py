import shutil
from os.path import join, dirname, exists
from tempfile import mkdtemp
from unittest import TestCase

from ia_scribe.cameras import camera_system
from ia_scribe.detectors.common_actions import *
from ia_scribe.detectors.reshoot_action_detector import *
from ia_scribe.scribe_globals import (
    DEFAULT_RESHOOT_ACTION_BINDINGS,
    FAKE_IMAGE
)
from ia_scribe.uix_backends.reshoot_screen_backend import ReShootScreenBackend
from tests.dummies import DummyWindow, DummyLogger, DummyCameraSystem


class ReShootScreenBackendCase(TestCase):

    def setUp(self):
        self.temp_book_path = book_path = mkdtemp(prefix='ia_scribe_')
        self.setup_files()
        self.backend = backend = self.create_backend()
        backend.init()
        backend.enable_keyboard_actions()
        self.all_note_leaf_numbers = \
            list(backend.scandata.iter_flagged_leafs())
        self.event_handler_called = False
        self.event_handler_last_args = None
        self.event_handler_args_list = []
        self.max_leaf_index = len(self.all_note_leaf_numbers) - 1
        self.min_leaf_index = 0
        self.even_leaf_number_index = 0
        self.odd_leaf_number_index = 1

    def create_backend(self):
        backend = ReShootScreenBackend()
        backend.keyboard_detector = \
            ReShootActionDetector(DEFAULT_RESHOOT_ACTION_BINDINGS)
        backend.book = {'path': self.temp_book_path}
        backend.reopen_at = 0
        backend.scandata = None
        backend.camera_system = DummyCameraSystem(cameras_count=1)
        backend.window = DummyWindow()
        backend.logger = DummyLogger()
        return backend

    def setup_files(self):
        current_dir = dirname(__file__)
        shutil.copy(join(current_dir, 'reshoot_scandata.json'),
                    join(self.temp_book_path, 'scandata.json'))
        shutil.copy(join(current_dir, 'reshoot_metadata.xml'),
                    join(self.temp_book_path, 'metadata.xml'))

    def tearDown(self):
        shutil.rmtree(self.temp_book_path)
        self.backend.reset()
        self.backend = None
        self.event_handler_called = False
        self.event_handler_last_args = None
        self.event_handler_args_list = None

    def event_handler(self, *args, **kwargs):
        self.event_handler_called = True
        self.event_handler_last_args = (args, kwargs)
        self.event_handler_args_list.append((args, kwargs))

    def assertEventDispatched(self, event_name, method, *args):
        backend = self.backend
        backend.fbind(event_name, self.event_handler)
        method(*args)
        message = 'Event {} not dispatched'.format(event_name)
        assert self.event_handler_called, message

    def assertEventNotDispatched(self, event_name, method, *args):
        backend = self.backend
        backend.fbind(event_name, self.event_handler)
        method(*args)
        message = 'Event {} dispatched'.format(event_name)
        assert not self.event_handler_called, message

    def keyboard_dispatch(self, scancode):
        keycode = None
        window = self.backend.window
        window.dispatch('on_key_down', keycode, scancode)
        window.dispatch('on_key_up', keycode, scancode)

    def create_expected_capture_report_list(self, side):
        backend = self.backend
        start_report = self.create_expected_capture_start_report(side)
        end_report = self.create_expected_capture_end_report(side)
        return [
            ((backend, start_report), {}),
            ((backend, end_report), {})
        ]

    def create_expected_capture_start_report(self, side):
        return {camera_system.KEY_CAPTURE_START: True}

    def create_expected_capture_end_report(self, side):
        path, thumb_path = self.backend.get_current_reshoot_paths()
        return {
            camera_system.KEY_SIDE: side,
            camera_system.KEY_THUMB_PATH: thumb_path,
            camera_system.KEY_IMAGE_WIDGET: None,
            camera_system.KEY_ERROR: None,
            camera_system.KEY_CAPTURE_END: True,
            camera_system.KEY_STATS: {
                'capture_time': 0,
                'thumb_time': 0
            },
            camera_system.KEY_EXTRA: {
                'leaf_number': self.backend.get_current_leaf_number()
            }
        }


class TestReShootScreenBackend(ReShootScreenBackendCase):

    def test_is_initialized(self):
        self.assertTrue(self.backend.is_initialized())

    def test_is_not_initialized(self):
        self.backend.reset()
        self.assertFalse(self.backend.is_initialized())

    def test_is_capture_running(self):
        self.assertFalse(self.backend.is_capture_running())

    def test_is_reshoot_leaf_ready(self):
        self.assertFalse(self.backend.is_reshoot_leaf_ready())

    def test_get_current_leaf_number(self):
        backend = self.backend
        for index, leaf_number in enumerate(self.all_note_leaf_numbers):
            backend.set_current_leaf_index(index)
            self.assertEqual(backend.get_current_leaf_number(), leaf_number)

    def test_get_current_leaf_index(self):
        backend = self.backend
        for index, leaf_number in enumerate(self.all_note_leaf_numbers):
            backend.set_current_leaf_index(index)
            self.assertEqual(backend.get_current_leaf_index(), index)

    def test_set_current_leaf_index(self):
        self.backend.set_current_leaf_index(1)
        self.assertEventDispatched(self.backend.EVENT_CURRENT_LEAF,
                                   self.backend.set_current_leaf_index, 0)

    def test_set_current_leaf_index_min_limit(self):
        backend = self.backend
        index = backend.get_current_leaf_index()
        backend.set_current_leaf_index(self.max_leaf_index - 1)
        self.assertEqual(backend.get_current_leaf_index(), index)

    def test_set_current_leaf_index_max_limit(self):
        backend = self.backend
        index = backend.get_current_leaf_index()
        backend.set_current_leaf_index(self.max_leaf_index + 1)
        self.assertEqual(backend.get_current_leaf_index(), index)

    def test_get_leafs_count(self):
        self.assertEqual(self.backend.get_leafs_count(),
                         len(self.all_note_leaf_numbers))

    def test_get_book_metadata(self):
        data = {
            'identifier': None,
            'path': self.temp_book_path,
            'title': 'test040417',
            'creator': None,
            'language': 'eng'
        }
        self.assertDictEqual(self.backend.get_book_metadata(), data)

    def test_get_leaf_data(self):
        self.backend.set_current_leaf_index(0)
        data = {
            'hand_side': 'LEFT',
            'page_number': 12,
            'page_type': 'Normal',
            'note': 'Reshoot this page'
        }
        self.assertDictEqual(self.backend.get_leaf_data(), data)

    def test_get_current_reshoot_paths(self):
        backend = self.backend
        image_name = '{:04d}.jpg'.format(backend.get_current_leaf_number())
        expected_path = join(self.temp_book_path, 'reshooting', image_name)
        expected_thumb_path = join(self.temp_book_path,
                                   'reshooting', 'thumbnails', image_name)
        expected = (expected_path, expected_thumb_path)
        self.assertTupleEqual(expected, backend.get_current_reshoot_paths())

    def test_get_current_original_paths(self):
        backend = self.backend
        image_name = '{:04d}.jpg'.format(backend.get_current_leaf_number())
        expected_path = join(self.temp_book_path, image_name)
        expected_thumb_path = join(self.temp_book_path,
                                   'thumbnails', image_name)
        expected = (expected_path, expected_thumb_path)
        self.assertTupleEqual(expected, backend.get_current_original_paths())

    def test_goto_previous_leaf(self):
        backend = self.backend
        backend.set_current_leaf_index(1)
        backend.goto_previous_leaf()
        self.assertEqual(backend.get_current_leaf_index(), 0)

    def test_goto_previous_leaf_limit(self):
        backend = self.backend
        backend.set_current_leaf_index(self.min_leaf_index)
        backend.goto_previous_leaf()
        self.assertEqual(backend.get_current_leaf_index(), self.min_leaf_index)

    def test_goto_previous_leaf_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_PREVIOUS_LEAF):
            backend.set_current_leaf_index(1)
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(backend.get_current_leaf_index(), 0)

    def test_goto_next_leaf(self):
        backend = self.backend
        backend.set_current_leaf_index(0)
        backend.goto_next_leaf()
        self.assertEqual(backend.get_current_leaf_index(), 1)

    def test_goto_next_leaf_limit(self):
        backend = self.backend
        backend.set_current_leaf_index(self.max_leaf_index)
        backend.goto_next_leaf()
        self.assertEqual(backend.get_current_leaf_index(), self.max_leaf_index)

    def test_goto_next_leaf_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_NEXT_LEAF):
            backend.set_current_leaf_index(0)
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(backend.get_current_leaf_index(), 1)

    def test_goto_first_leaf(self):
        backend = self.backend
        backend.set_current_leaf_index(self.max_leaf_index)
        backend.goto_first_leaf()
        self.assertEqual(backend.get_current_leaf_index(), self.min_leaf_index)

    def test_goto_first_leaf_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_FIRST_LEAF):
            backend.set_current_leaf_index(self.max_leaf_index)
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(backend.get_current_leaf_index(),
                             self.min_leaf_index)

    def test_goto_last_leaf(self):
        backend = self.backend
        backend.set_current_leaf_index(self.min_leaf_index)
        backend.goto_last_leaf()
        self.assertEqual(backend.get_current_leaf_index(), self.max_leaf_index)

    def test_goto_last_leaf_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_LAST_LEAF):
            backend.set_current_leaf_index(self.min_leaf_index)
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(backend.get_current_leaf_index(),
                             self.max_leaf_index)

    def test_goto_rescribe_screen(self):
        self.assertEventDispatched(self.backend.EVENT_GO_BACK,
                                   self.backend.goto_rescribe_screen)

    def test_goto_rescribe_screen_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_GO_BACK, self.event_handler)
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_GO_RESCRIBE_SCREEN):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_show_original_file(self):
        self.assertEventDispatched(self.backend.EVENT_SHOW_ORIGINAL_FILE,
                                   self.backend.show_original_file)

    def test_show_original_file_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_SHOW_ORIGINAL_FILE, self.event_handler)
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SHOW_ORIGINAL_FILE):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_show_reshoot_file_event_dispatched(self):
        self.backend.capture_spread()
        self.assertEventDispatched(
            self.backend.EVENT_SHOW_RESHOOT_FILE,
            self.backend.show_reshoot_file
        )

    def test_show_reshoot_file_event_dispatched_keyboard(self):
        backend = self.backend
        backend.capture_spread()
        backend.fbind(backend.EVENT_SHOW_RESHOOT_FILE, self.event_handler)
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SHOW_RESHOOT_FILE):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_show_reshoot_file_event_not_dispatched(self):
        self.assertEventNotDispatched(
            self.backend.EVENT_SHOW_RESHOOT_FILE,
            self.backend.show_reshoot_file
        )

    def test_show_reshoot_file_event_not_dispatched_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_SHOW_RESHOOT_FILE, self.event_handler)
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SHOW_RESHOOT_FILE):
            self.keyboard_dispatch(action.scancode)
            self.assertFalse(self.event_handler_called)
            self.event_handler_called = False

    def test_show_page_type_form_popup_event_dispatched(self):
        self.backend.capture_spread()
        self.assertEventDispatched(
            self.backend.EVENT_SHOW_PAGE_TYPE_FORM_POPUP,
            self.backend.show_page_type_form_popup
        )

    def test_show_page_type_form_popup_event_dispatched_keyboard(self):
        backend = self.backend
        backend.capture_spread()
        backend.fbind(backend.EVENT_SHOW_PAGE_TYPE_FORM_POPUP,
                      self.event_handler)
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SHOW_PAGE_TYPE):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_show_page_type_form_popup_event_not_dispatched(self):
        self.assertEventNotDispatched(
            self.backend.EVENT_SHOW_PAGE_TYPE_FORM_POPUP,
            self.backend.show_page_type_form_popup
        )

    def test_show_page_type_form_popup_event_not_dispatched_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_SHOW_PAGE_TYPE_FORM_POPUP,
                      self.event_handler)
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SHOW_PAGE_TYPE):
            self.keyboard_dispatch(action.scancode)
            self.assertFalse(self.event_handler_called)
            self.event_handler_called = False

    def test_update_page_type(self):
        self.assertEventDispatched(
            self.backend.EVENT_PAGE_TYPE,
            self.backend.update_page_type,
            self.all_note_leaf_numbers[0],
            'Normal'
        )

    def test_enable_keyboard_actions(self):
        self.backend.enable_keyboard_actions()
        self.assertTrue(self.backend.are_keyboard_actions_enabled())

    def test_disable_keyboard_actions(self):
        self.backend.enable_keyboard_actions()
        self.backend.disable_keyboard_actions()
        self.assertFalse(self.backend.are_keyboard_actions_enabled())

    def test_delete_current_spread(self):
        path, thumb_path = self.backend.get_current_reshoot_paths()
        shutil.copy(FAKE_IMAGE, path)
        shutil.copy(FAKE_IMAGE, thumb_path)
        self.backend.delete_current_spread()
        self.assertFalse(exists(path))
        self.assertFalse(exists(thumb_path))

    def test_rotate_reshoot_leaf_failure(self):
        self.assertEventNotDispatched(
            self.backend.EVENT_ROTATE_LEAF,
            self.backend.rotate_reshoot_leaf
        )

    def test_rotate_reshoot_leaf_success(self):
        self.backend.capture_spread()
        self.assertEventDispatched(
            self.backend.EVENT_ROTATE_LEAF,
            self.backend.rotate_reshoot_leaf
        )

    def test_save_leaf_note(self):
        note = 'aaa'
        leaf_number = self.backend.get_current_leaf_number()
        self.backend.save_leaf_note(note)
        self.assertEqual(
            self.backend.scandata.get_note(leaf_number),
            note
        )


class TestReShootScreenBackendKeyboardAssert(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_book_path = book_path = mkdtemp(prefix='ia_scribe_')
        current_dir = dirname(__file__)
        shutil.copy(join(current_dir, 'reshoot_scandata.json'),
                    join(book_path, 'scandata.json'))
        cls.backend = backend = ReShootScreenBackend()
        backend.keyboard_detector = \
            ReShootActionDetector(DEFAULT_RESHOOT_ACTION_BINDINGS)
        backend.book = {'path': book_path}
        backend.reopen_at = 0
        backend.scandata = None
        backend.camera_system = DummyCameraSystem(cameras_count=1)
        backend.window = DummyWindow()
        backend.logger = DummyLogger()
        backend.init()
        backend.capture_spread()
        backend.enable_keyboard_actions()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_book_path)

    def setUp(self):
        backend = self.backend
        backend.fbind(backend.EVENT_PAGE_TYPE, self.event_handler)
        self.event_handler_args = None

    def tearDown(self):
        backend = self.backend
        backend.funbind(backend.EVENT_PAGE_TYPE, self.event_handler)
        self.event_handler_args = None

    def event_handler(self, *args):
        self.event_handler_args = args

    def keyboard_dispatch(self, scancode):
        keycode = None
        window = self.backend.window
        window.dispatch('on_key_down', keycode, scancode)
        window.dispatch('on_key_up', keycode, scancode)

    def assertKeyboardAssertPage(self, action_name):
        backend = self.backend
        default_type = ASSERT_ACTIONS_TO_PAGE_TYPE[A_ASSERT_NORMAL]
        if action_name == A_ASSERT_NORMAL:
            default_type = ASSERT_ACTIONS_TO_PAGE_TYPE[A_ASSERT_CHAPTER]
        leaf_number = backend.get_current_leaf_number()
        page_type = ASSERT_ACTIONS_TO_PAGE_TYPE[action_name]
        for action in backend.keyboard_detector.\
                find_actions_by_name(action_name):
            backend.update_page_type(leaf_number, default_type)
            self.event_handler_args = None
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(self.event_handler_args[1], page_type)

    def test_keyboard_assert_chapter(self):
        self.assertKeyboardAssertPage(A_ASSERT_CHAPTER)

    def test_keyboard_assert_normal(self):
        self.assertKeyboardAssertPage(A_ASSERT_NORMAL)

    def test_keyboard_assert_title(self):
        self.assertKeyboardAssertPage(A_ASSERT_TITLE)

    def test_keyboard_assert_copyright(self):
        self.assertKeyboardAssertPage(A_ASSERT_COPYRIGHT)

    def test_keyboard_assert_cover(self):
        self.assertKeyboardAssertPage(A_ASSERT_COVER)

    def test_keyboard_assert_contents(self):
        self.assertKeyboardAssertPage(A_ASSERT_CONTENTS)

    def test_keyboard_assert_white_card(self):
        self.assertKeyboardAssertPage(A_ASSERT_WHITE_CARD)

    def test_keyboard_assert_foldout(self):
        self.assertKeyboardAssertPage(A_ASSERT_FOLDOUT)

    def test_keyboard_assert_color_card(self):
        self.assertKeyboardAssertPage(A_ASSERT_COLOR_CARD)

    def test_keyboard_assert_index(self):
        self.assertKeyboardAssertPage(A_ASSERT_INDEX)


class TestReShootScreenBackendCameras1(ReShootScreenBackendCase):

    def test_can_switch_cameras(self):
        self.assertFalse(self.backend.can_switch_cameras())

    def test_are_cameras_switched(self):
        self.backend.switch_cameras()
        self.assertFalse(self.backend.are_cameras_switched())

    def test_capture_spread_even_leaf_number(self):
        self.backend.set_current_leaf_index(self.even_leaf_number_index)
        self.backend.capture_spread()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_odd_leaf_number(self):
        self.backend.set_current_leaf_index(self.odd_leaf_number_index)
        self.backend.capture_spread()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_event_dispatched(self):
        self.assertEventDispatched(
            self.backend.EVENT_CAPTURE_LEAF,
            self.backend.capture_spread
        )

    def test_capture_spread_event_args(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        backend.capture_spread()
        expected = self.create_expected_capture_report_list('foldout')
        self.assertListEqual(expected, self.event_handler_args_list)

    def test_capture_spread_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        for action in backend.keyboard_detector.find_actions_by_name(A_SHOOT):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_switch_cameras_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SWITCH_CAMERAS):
            self.keyboard_dispatch(action.scancode)
            self.assertFalse(backend.are_cameras_switched())
            self.event_handler_called = False


class TestReShootScreenBackendCameras2(ReShootScreenBackendCase):

    def create_backend(self):
        backend = \
            super(TestReShootScreenBackendCameras2, self).create_backend()
        backend.camera_system = DummyCameraSystem(cameras_count=2)
        return backend

    def test_can_switch_cameras(self):
        self.assertTrue(self.backend.can_switch_cameras())

    def test_are_cameras_switched(self):
        self.backend.switch_cameras()
        self.assertTrue(self.backend.are_cameras_switched())

    def test_capture_spread_even_leaf_number(self):
        self.backend.set_current_leaf_index(self.even_leaf_number_index)
        self.backend.capture_spread()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_odd_leaf_number(self):
        self.backend.set_current_leaf_index(self.odd_leaf_number_index)
        self.backend.capture_spread()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_with_switched_cameras(self):
        self.backend.set_current_leaf_index(self.even_leaf_number_index)
        self.backend.switch_cameras()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_with_switched_cameras_odd_leaf_number(self):
        self.backend.set_current_leaf_index(self.odd_leaf_number_index)
        self.backend.switch_cameras()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_event_dispatched(self):
        self.assertEventDispatched(
            self.backend.EVENT_CAPTURE_LEAF,
            self.backend.capture_spread
        )

    def test_capture_spread_event_args(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        backend.capture_spread()
        expected = self.create_expected_capture_report_list('left')
        self.assertListEqual(expected, self.event_handler_args_list)

    def test_capture_spread_event_args_with_switched_cameras(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        backend.switch_cameras()
        expected = self.create_expected_capture_report_list('right')
        self.assertListEqual(expected, self.event_handler_args_list)

    def test_capture_spread_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        for action in backend.keyboard_detector.find_actions_by_name(A_SHOOT):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_switch_cameras_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SWITCH_CAMERAS):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(backend.are_cameras_switched())
            self.event_handler_called = False


class TestReShootScreenBackendCameras3(ReShootScreenBackendCase):

    def create_backend(self):
        backend = \
            super(TestReShootScreenBackendCameras3, self).create_backend()
        backend.camera_system = DummyCameraSystem(cameras_count=3)
        return backend

    def test_can_switch_cameras(self):
        self.assertTrue(self.backend.can_switch_cameras())

    def test_are_cameras_switched(self):
        self.backend.switch_cameras()
        self.assertTrue(self.backend.are_cameras_switched())

    def test_capture_spread_even_leaf_number(self):
        self.backend.set_current_leaf_index(self.even_leaf_number_index)
        self.backend.capture_spread()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_odd_leaf_number(self):
        self.backend.set_current_leaf_index(self.odd_leaf_number_index)
        self.backend.capture_spread()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_with_switched_cameras_even_leaf_number(self):
        self.backend.set_current_leaf_index(self.even_leaf_number_index)
        self.backend.switch_cameras()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_with_switched_cameras_odd_leaf_number(self):
        self.backend.set_current_leaf_index(self.odd_leaf_number_index)
        self.backend.switch_cameras()
        self.assertTrue(self.backend.is_reshoot_leaf_ready())

    def test_capture_spread_event_dispatched(self):
        self.assertEventDispatched(
            self.backend.EVENT_CAPTURE_LEAF,
            self.backend.capture_spread
        )

    def test_capture_spread_event_args(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        backend.capture_spread()
        expected = self.create_expected_capture_report_list('left')
        self.assertListEqual(expected, self.event_handler_args_list)

    def test_capture_spread_event_args_with_switched_cameras(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        backend.switch_cameras()
        expected = self.create_expected_capture_report_list('right')
        self.assertListEqual(expected, self.event_handler_args_list)

    def test_capture_spread_keyboard(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self.event_handler)
        for action in backend.keyboard_detector.find_actions_by_name(A_SHOOT):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(self.event_handler_called)
            self.event_handler_called = False

    def test_switch_cameras_keyboard(self):
        backend = self.backend
        for action in backend.keyboard_detector.\
                find_actions_by_name(A_SWITCH_CAMERAS):
            self.keyboard_dispatch(action.scancode)
            self.assertTrue(backend.are_cameras_switched())
            self.event_handler_called = False
