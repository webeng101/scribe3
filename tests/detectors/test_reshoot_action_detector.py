from unittest import TestCase

from ia_scribe.detectors.common_actions import *
from ia_scribe.detectors.reshoot_action_detector import *
from ia_scribe.scribe_globals import (
    DEFAULT_RESHOOT_ACTION_BINDINGS,
    RESHOOT_ACTION_BINDINGS_VERSION
)
from tests.dummies import DummyWindow


class TestReShootActionDetector(TestCase):

    def setUp(self):
        self.window = DummyWindow()
        self.detector = ReShootActionDetector(DEFAULT_RESHOOT_ACTION_BINDINGS)
        self.detector.fbind('on_action', self.on_action_detected)
        self.window.fbind('on_key_down', self.on_key_down)
        self.window.fbind('on_key_up', self.on_key_up)
        self.detected_action = None

    def tearDown(self):
        self.window = None
        self.detector = None
        self.detected_action = None

    def on_action_detected(self, detector, action):
        self.detected_action = action

    def on_key_down(self, window, keycode, scancode, codepoint=None,
                    modifiers=None, **kwargs):
        return self.detector.on_key_down(keycode, scancode, codepoint,
                                         modifiers, **kwargs)

    def on_key_up(self, window, keycode, scancode, codepoint=None,
                  modifiers=None, **kwargs):
        return self.detector.on_key_up(keycode, scancode, codepoint,
                                       modifiers, **kwargs)

    def keyboard_dispatch(self, scancode):
        keycode = None
        self.window.dispatch('on_key_down', keycode, scancode)
        self.window.dispatch('on_key_up', keycode, scancode)

    def test_loaded_version(self):
        self.assertEqual(self.detector.load_version(),
                         RESHOOT_ACTION_BINDINGS_VERSION)

    def test_non_existing_action(self):
        self.window.dispatch('on_key_down', -1, -1)
        self.window.dispatch('on_key_up', -1, -1)
        self.assertEqual(None, self.detected_action)

    def test_action_str(self):
        shoot_action = self.detector.find_actions_by_name(A_SHOOT)[0]
        rotate_action = self.detector.find_actions_by_name(A_ROTATE_LEAF)[0]
        self.assertNotEqual(str(shoot_action), str(rotate_action))

    def test_action_repr(self):
        shoot_action = self.detector.find_actions_by_name(A_SHOOT)[0]
        rotate_action = self.detector.find_actions_by_name(A_ROTATE_LEAF)[0]
        self.assertNotEqual(repr(shoot_action), repr(rotate_action))

    def test_shoot_action(self):
        for action in self.detector.find_actions_by_name(A_SHOOT):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_SHOOT, self.detected_action.name)
            self.detected_action = None

    def test_switch_cameras_action(self):
        for action in self.detector.find_actions_by_name(A_SWITCH_CAMERAS):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_SWITCH_CAMERAS, self.detected_action.name)
            self.detected_action = None

    def test_previous_leaf_action(self):
        for action in self.detector.find_actions_by_name(A_PREVIOUS_LEAF):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_PREVIOUS_LEAF, self.detected_action.name)
            self.detected_action = None

    def test_next_leaf_action(self):
        for action in self.detector.find_actions_by_name(A_NEXT_LEAF):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_NEXT_LEAF, self.detected_action.name)
            self.detected_action = None

    def test_first_leaf_action(self):
        for action in self.detector.find_actions_by_name(A_FIRST_LEAF):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_FIRST_LEAF, self.detected_action.name)
            self.detected_action = None

    def test_last_leaf_action(self):
        for action in self.detector.find_actions_by_name(A_LAST_LEAF):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_LAST_LEAF, self.detected_action.name)
            self.detected_action = None

    def test_rotate_leaf_action(self):
        for action in self.detector.find_actions_by_name(A_ROTATE_LEAF):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ROTATE_LEAF, self.detected_action.name)
            self.detected_action = None

    def test_show_page_type_action(self):
        for action in self.detector.find_actions_by_name(A_SHOW_PAGE_TYPE):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_SHOW_PAGE_TYPE, self.detected_action.name)
            self.detected_action = None

    def test_show_original_file(self):
        for action in self.detector.find_actions_by_name(A_SHOW_ORIGINAL_FILE):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_SHOW_ORIGINAL_FILE, self.detected_action.name)
            self.detected_action = None

    def test_show_reshoot_file(self):
        for action in self.detector.find_actions_by_name(A_SHOW_RESHOOT_FILE):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_SHOW_RESHOOT_FILE, self.detected_action.name)
            self.detected_action = None

    def test_go_rescribe_screen_action(self):
        for action in self.detector.find_actions_by_name(A_GO_RESCRIBE_SCREEN):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_GO_RESCRIBE_SCREEN, self.detected_action.name)
            self.detected_action = None

    def test_assert_chapter_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_CHAPTER):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_CHAPTER, self.detected_action.name)
            self.detected_action = None

    def test_assert_normal_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_NORMAL):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_NORMAL, self.detected_action.name)
            self.detected_action = None

    def test_assert_title_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_TITLE):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_TITLE, self.detected_action.name)
            self.detected_action = None

    def test_assert_copyright_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_COPYRIGHT):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_COPYRIGHT, self.detected_action.name)
            self.detected_action = None

    def test_assert_cover_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_COVER):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_COVER, self.detected_action.name)
            self.detected_action = None

    def test_assert_contents_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_CONTENTS):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_CONTENTS, self.detected_action.name)
            self.detected_action = None

    def test_assert_white_card_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_WHITE_CARD):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_WHITE_CARD, self.detected_action.name)
            self.detected_action = None

    def test_assert_foldout_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_FOLDOUT):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_FOLDOUT, self.detected_action.name)
            self.detected_action = None

    def test_assert_color_card_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_COLOR_CARD):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_COLOR_CARD, self.detected_action.name)
            self.detected_action = None

    def test_assert_index_action(self):
        for action in self.detector.find_actions_by_name(A_ASSERT_INDEX):
            self.keyboard_dispatch(action.scancode)
            self.assertEqual(A_ASSERT_INDEX, self.detected_action.name)
            self.detected_action = None
