from kivy.logger import Logger

from ia_scribe.detectors.capture_action_detector import *
from ia_scribe.detectors.common_actions import *


class CaptureActionHandler(object):

    def __init__(self, capture_screen):
        self.capture_screen = capture_screen
        self._handlers = {
            A_SHOOT: self.on_shoot,
            A_TOGGLE_AUTOSHOOT: self.on_toggle_autoshoot,
            A_RESHOOT: self.on_reshoot,
            A_DELETE_SPREAD: self.on_delete_spread,
            A_DELETE_SPREAD_CONFIRM: self.on_delete_spread_confirm,
            A_DELETE_SPREAD_OR_FOLDOUT: self.on_delete_spread_or_foldout,
            A_PREVIOUS_SPREAD: self.on_previous_spread,
            A_NEXT_SPREAD: self.on_next_spread,
            A_PREVIOUS_FOLDOUT_SPREAD: self.on_previous_foldout_spread,
            A_NEXT_FOLDOUT_SPREAD: self.on_next_foldout_spread,
            A_SHOW_ORIGINAL_FILE: self.on_show_original_file,
            A_GO_MAIN_SCREEN: self.on_go_main_screen,
            A_GO_CAPTURE_COVER: self.on_go_capture_cover,
            A_GO_LAST_SPREAD: self.on_go_last_spread,
            A_SHOW_PAGE_ATTRS: self.on_show_page_attrs,
        }

    def on_action(self, detector, action):
        handler = self._handlers.get(action.name, None)
        if not handler and action.name in A_PAGE_TYPE_ASSERTIONS:
            handler = self.on_assert_action
        if handler:
            handler(action)
            Logger.debug('CaptureActionHandler: Handled action: {}'
                         .format(action.name))

    def on_shoot(self, action):
        self.capture_screen.capture_button()

    def on_toggle_autoshoot(self, action):
        screen = self.capture_screen
        if screen.is_autoshoot_capture_running():
            screen.stop_autoshoot_capture()
        else:
            screen.start_autoshoot_capture()

    def on_reshoot(self, action):
        self.capture_screen.reshoot_spread()

    def on_delete_spread(self, action):
        screen = self.capture_screen
        slider_bar = screen.spread_slider_bar
        if slider_bar.slider_value != slider_bar.slider_min:
            screen.delete_current_spread_and_rename()

    def on_delete_spread_confirm(self, action):
        screen = self.capture_screen
        slider_bar = screen.spread_slider_bar
        if slider_bar.slider_value == slider_bar.slider_min:
            screen.capture_button()
        else:
            screen.capture_spread_box.delete_spread()

    def on_delete_spread_or_foldout(self, action):
        screen = self.capture_screen
        if screen.capture_spread_box:
            screen.capture_spread_box.delete_or_foldout()

    def on_previous_spread(self, action):
        screen = self.capture_screen
        screen.show_spread(screen.spread_slider_bar.slider_value - 1)

    def on_next_spread(self, action):
        screen = self.capture_screen
        screen.show_spread(screen.spread_slider_bar.slider_value + 1)

    def on_previous_foldout_spread(self, action):
        self.capture_screen.show_previous_marked_spread()

    def on_next_foldout_spread(self, action):
        self.capture_screen.show_next_marked_spread()

    def on_assert_action(self, action):
        screen = self.capture_screen
        sides = screen.get_displayed_sides()
        page_side = screen.adjust_side(action.side)
        if page_side not in sides:
            Logger.info('CaptureActionHandler: Ignoring {} action as its side '
                        'is not in displayed sides [{}]'
                        .format(action, ', '.join(sides.keys())))
            return
        slider_bar = screen.spread_slider_bar
        if page_side == 'left' \
                and slider_bar.slider_value == slider_bar.slider_min:
            return
        page_number = sides[page_side]
        page_type = ASSERT_ACTIONS_TO_PAGE_TYPE[action.name]
        page_assertion = screen.scandata.get_page_assertion(page_number)
        screen.set_page_attrs(page_number, page_type, page_side, page_assertion)

    def on_show_original_file(self, action):
        self.capture_screen.show_original_file(None, action.side)

    def on_go_main_screen(self, action):
        screen_manager = self.capture_screen.screen_manager
        screen_manager.transition.direction = 'right'
        screen_manager.current = 'upload_screen'

    def on_go_capture_cover(self, action):
        screen = self.capture_screen
        screen.show_spread(screen.spread_slider_bar.slider_min)

    def on_go_last_spread(self, action):
        screen = self.capture_screen
        screen.show_spread(screen.spread_slider_bar.slider_max)

    def on_show_page_attrs(self, action):
        screen = self.capture_screen
        page_side = screen.adjust_side(action.side)
        slider_bar = screen.spread_slider_bar
        if page_side == 'left' \
                and slider_bar.slider_value == slider_bar.slider_min:
            return
        screen.show_page_attrs(None, page_side)
