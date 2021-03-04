import os
from os.path import join, exists

from PIL import Image

from ia_scribe.cameras import camera_system
from ia_scribe.detectors.common_actions import ASSERT_ACTIONS_TO_PAGE_TYPE
from ia_scribe.detectors.reshoot_action_detector import *
from ia_scribe.exceptions import DiskFullError
from ia_scribe.book.metadata import get_metadata
from ia_scribe.book.scandata import ScanData
from ia_scribe.scribe_globals import RESHOOT_ACTION_BINDINGS
from ia_scribe.uix_backends.widget_backend import WidgetBackend
from ia_scribe.utils import ensure_dir_exists, has_free_disk_space, convert_scandata_angle_to_thumbs_rotation
from ia_scribe.config.config import Scribe3Configuration

from ia_scribe.utils import cradle_closed

class ReShootScreenBackend(WidgetBackend):

    EVENT_CAPTURE_LEAF = 'on_capture_leaf'
    EVENT_CURRENT_LEAF = 'on_current_leaf'
    EVENT_ROTATE_LEAF = 'on_rotate_leaf'
    EVENT_PAGE_TYPE = 'on_page_type'
    EVENT_SHOW_ORIGINAL_FILE = 'on_show_original_file'
    EVENT_SHOW_RESHOOT_FILE = 'on_show_reshoot_file'
    EVENT_SHOW_PAGE_TYPE_FORM_POPUP = 'on_show_page_type_form_popup'
    EVENT_GO_BACK = 'on_go_back'

    __events__ = (EVENT_CAPTURE_LEAF, EVENT_CURRENT_LEAF, EVENT_ROTATE_LEAF,
                  EVENT_PAGE_TYPE, EVENT_GO_BACK, EVENT_SHOW_ORIGINAL_FILE,
                  EVENT_SHOW_RESHOOT_FILE, EVENT_SHOW_PAGE_TYPE_FORM_POPUP)

    def __init__(self, **kwargs):
        super(ReShootScreenBackend, self).__init__(**kwargs)
        self._note_leafs = []
        self._reverse_cams = False
        self._cameras_count = 0
        self._current_leaf_index = 0
        self._capture_running = False
        self._keyboard_action_handler = ReShootScreenKeyboardHandler(self)
        self.keyboard_detector = None
        self.book = None
        self.reopen_at = 0
        self.scandata = None
        self.camera_system = None
        self.window = None

    def init(self):
        if not self.scandata:
            self.scandata = ScanData(self.book['path'], downloaded=True)
        self._note_leafs[:] = self.scandata.iter_flagged_leafs()
        try:
            leaf_index = self._note_leafs.index(self.reopen_at)
        except ValueError:
            leaf_index = 0
        self.set_current_leaf_index(leaf_index)
        if not self.keyboard_detector:
            detector = ReShootActionDetector(RESHOOT_ACTION_BINDINGS)
            self.keyboard_detector = detector
        self._keyboard_action_handler.detector = self.keyboard_detector
        self._cameras_count = self.camera_system.cameras.get_num_cameras()
        self._capture_running = False
        self._reverse_cams = False
        self.config = Scribe3Configuration()
        super(ReShootScreenBackend, self).init()

    def reset(self):
        self.book = None
        self.reopen_at = None
        self.scandata = None
        self.camera_system = None
        self.window = None
        del self._note_leafs[:]
        self._current_leaf_index = 0
        self._reverse_cams = False
        self._cameras_count = 0
        self._capture_running = False
        super(ReShootScreenBackend, self).reset()

    def is_capture_running(self):
        return self._capture_running

    def is_reshoot_leaf_ready(self):
        path, thumb_path = self.get_current_reshoot_paths()
        return exists(path) and exists(thumb_path)

    def can_switch_cameras(self):
        return self._cameras_count > 1

    def can_capture_spread(self):
        return cradle_closed and not self._capture_running and self._cameras_count > 0

    def get_current_leaf_number(self):
        return self._note_leafs[self._current_leaf_index]

    def get_current_leaf_index(self):
        return self._current_leaf_index

    def set_current_leaf_index(self, index):
        max_index = max(0, len(self._note_leafs) - 1)
        if 0 <= index <= max_index and self._current_leaf_index != index:
            self._current_leaf_index = index
            self.dispatch(self.EVENT_CURRENT_LEAF)

    def get_leafs_count(self):
        return len(self._note_leafs)

    def get_book_metadata(self):
        md = get_metadata(self.book['path'])
        return {
            'identifier': self.book.get('identifier', None),
            'path': self.book['path'],
            'title': md.get('title', None),
            'creator': md.get('creator', md.get('author', None)),
            'language': md.get('language', None)
        }

    def get_leaf_data(self):
        leaf_number = self.get_current_leaf_number()
        leaf_data = self.scandata.get_page_data(leaf_number)
        page_number_data = leaf_data.get('pageNumber', None)
        page_number = self._get_page_number(page_number_data)
        return {
            'hand_side': leaf_data.get('handSide', None),
            'page_number': page_number,
            'page_type': leaf_data['pageType'],
            'note': leaf_data.get('note', None)
        }

    def get_current_reshoot_paths(self):
        leaf_number = self.get_current_leaf_number()
        image_name = '{:04d}.jpg'.format(leaf_number)
        book_path = self.book['path']
        path = join(book_path, 'reshooting', image_name)
        thumb_path = join(book_path, 'reshooting', 'thumbnails', image_name)
        ensure_dir_exists(join(book_path, 'reshooting'))
        ensure_dir_exists(join(book_path, 'reshooting', 'thumbnails'))
        return path, thumb_path

    def get_current_original_paths(self):
        leaf_number = self.get_current_leaf_number()
        image_name = '{:04d}.jpg'.format(leaf_number)
        book_path = self.book['path']
        path = join(book_path, image_name)
        thumb_path = join(book_path, 'thumbnails', image_name)
        return path, thumb_path

    def _get_page_number(self, page_number_data):
        # TODO: Remove this method when scandata structure becomes the same
        # for reshooting mode and otherwise
        if page_number_data:
            if isinstance(page_number_data, dict):
                page_number = page_number_data.get('num', None)
                return None if page_number is None else int(page_number)
            elif isinstance(page_number_data, str):
                return int(page_number_data)
        return None

    def goto_previous_leaf(self, *args):
        self.set_current_leaf_index(self._current_leaf_index - 1)

    def goto_next_leaf(self, *args):
        self.set_current_leaf_index(self._current_leaf_index + 1)

    def goto_first_leaf(self, *args):
        self.set_current_leaf_index(0)

    def goto_last_leaf(self, *args):
        max_index = max(0, len(self._note_leafs) - 1)
        self.set_current_leaf_index(max_index)

    def goto_rescribe_screen(self, *args):
        self.dispatch(self.EVENT_GO_BACK)

    def show_original_file(self, *args):
        self.dispatch(self.EVENT_SHOW_ORIGINAL_FILE)

    def show_reshoot_file(self, *args):
        if self.is_reshoot_leaf_ready():
            self.dispatch(self.EVENT_SHOW_RESHOOT_FILE)

    def show_page_type_form_popup(self, *args):
        if self.is_reshoot_leaf_ready():
            self.dispatch(self.EVENT_SHOW_PAGE_TYPE_FORM_POPUP)

    def save_leaf_note(self, note):
        scandata = self.scandata
        leaf_number = self.get_current_leaf_number()
        if scandata.get_note(leaf_number) != note:
            scandata.set_note(leaf_number, note)
            scandata.save()
            if note:
                self.logger.info(
                    'ReShootScreenBackend: Updated leaf %d with note: %s'
                    % (leaf_number, '\n%s' % note if '\n' in note else note)
                )
            else:
                self.logger.info(
                    'ReShootScreenBackend: Removed note from leaf {}'
                    .format(leaf_number)
                )

    def update_page_type(self, leaf_number, page_type):
        scandata = self.scandata
        scandata.update_page_type(leaf_number, page_type)
        scandata.save()
        self.dispatch(self.EVENT_PAGE_TYPE, page_type)

    def update_leaf_rotation_if_necessary(self, leaf_number):
        if self._cameras_count == 1:
            self.logger.info(
                'ReShootScreenBackend: Reshooting in single-camera mode, will '
                'rotate by system default of {} degrees'
                .format(self.config.get_integer('default_single_camera_rotation', 180))
            )
            new_degree = self.config.get_integer('default_single_camera_rotation', 180)
            self.scandata.update_rotate_degree(leaf_number, new_degree)
            self.scandata.save()
            self.logger.info(
                'ReShootScreenBackend: Set leaf {} rotation to {} degree(s)'
                .format(leaf_number, new_degree)
            )

    def enable_keyboard_actions(self, *args):
        self._keyboard_action_handler.enable()

    def disable_keyboard_actions(self, *args):
        self._keyboard_action_handler.disable()

    def are_keyboard_actions_enabled(self):
        return self._keyboard_action_handler.is_enabled()

    def switch_cameras(self, *args):
        if not self._capture_running and self.can_switch_cameras():
            self._reverse_cams = not self._reverse_cams
            self.logger.info('ReShootScreen: Switched cameras')
            self.capture_spread()

    def are_cameras_switched(self):
        return self._reverse_cams

    def capture_spread(self, *args):
        if not self.can_capture_spread():
            return
        if not has_free_disk_space(self.book['path']):
            self.logger.info('capture_spread: the disk is full!')
            report = {camera_system.KEY_ERROR: DiskFullError()}
            self.dispatch(self.EVENT_CAPTURE_LEAF, report)
            return
        leaf_number = self.get_current_leaf_number()
        side = self._get_capture_camera_side(leaf_number)
        path, thumb_path = self.get_current_reshoot_paths()
        camera_kwargs = self._create_camera_kwargs(side, leaf_number)
        self.logger.info(
            'ReShootScreen: Capturing new image for leaf {}, camera side {}, '
            '{}using reversed cameras'
            .format(leaf_number, side, '' if self._reverse_cams else 'not ')
        )
        self._capture_running = True
        self.delete_current_spread()
        self.update_leaf_rotation_if_necessary(leaf_number)
        report = {camera_system.KEY_CAPTURE_START: True}
        self.dispatch(self.EVENT_CAPTURE_LEAF, report)
        self.camera_system.left_queue.put(camera_kwargs)

    def _get_capture_camera_side(self, leaf_number):
        if self._cameras_count == 1:
            camera_side = 'foldout'
        else:
            camera_side = 'left' if leaf_number % 2 == 0 else 'right'
            if self._reverse_cams:
                camera_side = 'left' if camera_side == 'right' else 'right'
        return camera_side

    def _capture_spread_end(self, report, *args):
        self._capture_running = False
        report[camera_system.KEY_CAPTURE_END] = True
        if self.is_initialized():
            stats = report[camera_system.KEY_STATS]
            leaf_number = report[camera_system.KEY_EXTRA]['leaf_number']
            self.scandata.set_capture_time(leaf_number, stats['capture_time'])
        self.dispatch(self.EVENT_CAPTURE_LEAF, report)

    def delete_current_spread(self, *args):
        path, thumb_path = self.get_current_reshoot_paths()
        self._delete_file(path)
        self._delete_file(thumb_path)

    def _delete_file(self, path):
        if exists(path):
            os.remove(path)
            self.logger.info('ReShootScreenBackend: Removed: {}'.format(path))

    def rotate_reshoot_leaf(self, *args):
        scandata_rotation_angle = 90
        path, thumb_path = self.get_current_reshoot_paths()
        if not self.is_reshoot_leaf_ready():
            self.logger.error(
                'ReShootScreen: Failed to rotate. Image not found: {}'
                    .format(thumb_path)
            )
            return
        leaf_number = self.get_current_leaf_number()
        leaf_data = self.scandata.get_page_data(leaf_number)
        current_degree = int(leaf_data.get('rotateDegree', 0))

        new_degree = (current_degree + scandata_rotation_angle) % 360
        self.scandata.update_rotate_degree(leaf_number, new_degree)
        self.scandata.save()

        rotate_by = convert_scandata_angle_to_thumbs_rotation(new_degree, scandata_rotation_angle)

        image = Image.open(path)
        size = (1500, 1000)  # (6000,4000)/4
        image.thumbnail(size)
        image = image.rotate(rotate_by, expand=True)
        image.save(thumb_path, 'JPEG', quality=90)

        self.logger.info(
            'ReShootScreenBackend: Set leaf {} rotation to {} degree(s) in scandata ( {} thumbs-equivalent) from {}'
            .format(leaf_number, new_degree, rotate_by, current_degree))
        self.dispatch(self.EVENT_ROTATE_LEAF)

    def _create_camera_kwargs(self, camera_side, leaf_number):
        path, thumb_path = self.get_current_reshoot_paths()
        return {
            camera_system.KEY_CALLBACK: self._capture_spread_end,
            camera_system.KEY_SIDE: camera_side,
            camera_system.KEY_PATH: path,
            camera_system.KEY_THUMB_PATH: thumb_path,
            camera_system.KEY_EXTRA: {'leaf_number': leaf_number}
        }

    def on_capture_leaf(self, report):
        pass

    def on_current_leaf(self, *args):
        pass

    def on_rotate_leaf(self, *args):
        pass

    def on_page_type(self, *args):
        pass

    def on_show_original_file(self, *args):
        pass

    def on_show_reshoot_file(self, *args):
        pass

    def on_show_page_type_form_popup(self, *args):
        pass

    def on_go_back(self, *args):
        pass


class ReShootScreenKeyboardHandler(object):

    def __init__(self, backend, detector=None):
        self.backend = backend
        self.detector = detector
        self._keyboard_actions_enabled = False
        self._keyboard_action_handlers = {
            A_SHOOT: backend.capture_spread,
            A_SWITCH_CAMERAS: backend.switch_cameras,
            A_PREVIOUS_LEAF: backend.goto_previous_leaf,
            A_NEXT_LEAF: backend.goto_next_leaf,
            A_FIRST_LEAF: backend.goto_first_leaf,
            A_LAST_LEAF: backend.goto_last_leaf,
            A_ROTATE_LEAF: backend.rotate_reshoot_leaf,
            A_SHOW_PAGE_TYPE: backend.show_page_type_form_popup,
            A_SHOW_ORIGINAL_FILE: backend.show_original_file,
            A_SHOW_RESHOOT_FILE: backend.show_reshoot_file,
            A_GO_RESCRIBE_SCREEN: backend.goto_rescribe_screen
        }

    def enable(self):
        if not self._keyboard_actions_enabled:
            backend = self.backend
            backend.window.bind(on_key_down=self._on_key_down)
            backend.window.bind(on_key_up=self._on_key_up)
            self.detector.fbind('on_action',
                                self._on_keyboard_action)
            self._keyboard_actions_enabled = True
            backend.logger.debug('ReShootScreenBackend: '
                                 'Enabled keyboard actions')

    def disable(self):
        if self._keyboard_actions_enabled:
            backend = self.backend
            backend.window.unbind(on_key_down=self._on_key_down)
            backend.window.unbind(on_key_up=self._on_key_up)
            self.detector.funbind('on_action',
                                  self._on_keyboard_action)
            self.detector.reset()
            self._keyboard_actions_enabled = False
            backend.logger.debug('ReShootScreenBackend: '
                                 'Disabled keyboard actions')

    def is_enabled(self):
        return self._keyboard_actions_enabled

    def _on_key_down(self, window, keycode, scancode=None, codepoint=None,
                     modifiers=None, **kwargs):
        if self.detector.on_key_down(keycode, scancode, codepoint,
                                     modifiers, **kwargs):
            return True

    def _on_key_up(self, window, keycode, scancode=None, codepoint=None,
                   modifiers=None, **kwargs):
        if self.detector.on_key_up(keycode, scancode, codepoint,
                                   modifiers, **kwargs):
            return True

    def _on_keyboard_action(self, detector, action):
        handler = self._keyboard_action_handlers.get(action.name, None)
        if not handler and action.name in A_PAGE_TYPE_ASSERTIONS:
            handler = self._on_keyboard_assert_action
        debug = self.backend.logger.debug
        if handler:
            debug('ReShootScreenBackend: Handling keyboard action: {}'
                  .format(action.name))
            handler(action)
        else:
            debug('ReShootScreenBackend: No handler found for keyboard '
                  'action {}'.format(action.name))

    def _on_keyboard_assert_action(self, action):
        backend = self.backend
        if backend.is_reshoot_leaf_ready():
            leaf_number = backend.get_current_leaf_number()
            page_type = ASSERT_ACTIONS_TO_PAGE_TYPE[action.name]
            backend.update_page_type(leaf_number, page_type)
