'''
Scribe3 uses Kivy to draw the UI and manage workers and threads.

At the moment the main UI component and views are:

    ScribeWidget: the container and screen manager
    UploadWidget: the main view with booklist etc
    CalibrationWidget: the calibration view

the widgets templates and behaviour are in the file scribe.kv
as the screen manager status, and views.

    Screen: upload_screen - managed by the UploadWidget - the main view
    CalibrationScreen: calibration_screen
    CaptureScreen: capture_screen
    SettingsScreen: settings_screen

There are two threads: the 'main thread' and the 'dispatcher thread', plus one
thread per camera (1-3).
'''

import os
import shutil
import sys
import time
from functools import partial
from io import BytesIO
from os.path import exists, join

from kivy import Config

from ia_scribe import scribe_globals

Config.set(
    'kivy', 'window_icon', join(scribe_globals.IMAGES_DIR, 'window_icon.png')
)
Config.set('kivy', 'exit_on_escape', 0)
Config.set('input', 'mouse', 'mouse,disable_multitouch')
Config.set('graphics', 'width', 1450)
Config.set('graphics', 'height', 950)

from PIL import Image as PIL_Image
from kivy.app import App
from kivy.base import EventLoop, ExceptionManager, ExceptionHandler
from kivy.clock import Clock
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
from kivy.logger import Logger
from kivy.properties import DictProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.book.library import Library
from ia_scribe.detectors.capture_action_detector import CaptureActionDetector
from ia_scribe.detectors.reshoot_action_detector import ReShootActionDetector
from ia_scribe.ia_services.tts import raven_client
from ia_scribe.tasks.task_scheduler import TaskScheduler
from ia_scribe.uix.actions.generic import ColoredYesNoActionPopupMixin
from ia_scribe.uix.screens.loading.loading_screen import LoadingScreen
from ia_scribe.update.update import UpdateManager
from ia_scribe.utils import restart_app


class Scribe3App(App):

    _popups = DictProperty()

    def __init__(self, **kwargs):
        self._fullscreen_key_down = False
        self.needs_restart = False
        self.task_scheduler = TaskScheduler()
        super(Scribe3App, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self._books_db = Library()
        self.update_manager = UpdateManager()
        self.update_manager.task_scheduler = self.task_scheduler
        self.update_manager.schedule_update_check()

    def build(self):
        self.title = 'Scribe3 | {}'.format(scribe_globals.BUILD_NUMBER)
        self.setup_files()
        ExceptionManager.add_handler(RuntimeErrorHandler(self))
        return BoxLayout()

    def setup_files(self):
        self.setup_config_dir()
        self.setup_capture_action_config()
        self.setup_reshoot_action_config()
        self.setup_stats_dirs()

    def setup_config_dir(self):
        config_dir = scribe_globals.CONFIG_DIR
        if not exists(config_dir):
            os.makedirs(config_dir)
            Logger.debug('Scribe3App: Created config dir at {}'
                         .format(config_dir))

    def setup_stats_dirs(self):
        stats_dirs = [scribe_globals.STATS_BASE_DIR,
                      scribe_globals.STATS_DIR,
                      scribe_globals.PROCESSED_STATS_DIR,
                      scribe_globals.METRICS_DIR]
        for stats_dir in stats_dirs:
            if not exists(stats_dir):
                os.makedirs(stats_dir)
                Logger.debug('Scribe3App: Created stats dir at {}'
                             .format(stats_dir))

    def setup_capture_action_config(self):
        version = scribe_globals.CAPTURE_ACTION_BINDINGS_VERSION
        current_config = scribe_globals.CAPTURE_ACTION_BINDINGS
        default_config = scribe_globals.DEFAULT_CAPTURE_ACTION_BINDINGS
        self._setup_action_config(version, current_config, default_config,
                                  CaptureActionDetector)

    def setup_reshoot_action_config(self):
        version = scribe_globals.RESHOOT_ACTION_BINDINGS_VERSION
        current_config = scribe_globals.RESHOOT_ACTION_BINDINGS
        default_config = scribe_globals.DEFAULT_RESHOOT_ACTION_BINDINGS
        self._setup_action_config(version, current_config, default_config,
                                  ReShootActionDetector)

    def _setup_action_config(self, version, current_config, default_config,
                             detector_cls):
        info = Logger.info
        if not exists(current_config):
            info('Scribe3App: Config {} does not exist'
                 .format(current_config))
            shutil.copy(default_config, current_config)
            info('Scribe3App: Copied {} -> {}'
                 .format(default_config, current_config))
        else:
            detector = detector_cls(current_config, auto_init=False)
            detected_version = detector.load_version()
            if detected_version != version:
                shutil.copy(default_config, current_config)
                info('Scribe3App: Config version mismatched. Copied {} -> {}'
                     .format(default_config, current_config))
        info('Scribe3App: Using config from {}'.format(current_config))

    def open_settings(self, *largs):
        # Prevent F1 press to open Kivy settings
        pass

    def on_start(self):
        window = self.root_window
        window.fbind('on_key_down', self._on_key_down)
        window.fbind('on_key_up', self._on_key_up)
        window.fbind('on_motion', self._on_motion)
        window.fbind('on_request_close', self._verify_exit_conditions)
        self.root.add_widget(LoadingScreen())
        Clock.schedule_once(self._swap_loading_screen_with_root_widget, 1.5)

    def _swap_loading_screen_with_root_widget(self, *args):
        from ia_scribe.uix.scribe_widget import ScribeWidget
        scribe_widget = ScribeWidget(books_db=self._books_db,
                                     task_scheduler=self.task_scheduler)
        # scribe_widget.show_user_switch_screen()
        self.root.clear_widgets()
        self.root.add_widget(scribe_widget)

    def on_stop(self):
        if EventLoop.status == 'closed':
            return
        window = self.root_window
        window.funbind('on_key_down', self._on_key_down)
        window.funbind('on_key_up', self._on_key_up)
        window.funbind('on_motion', self._on_motion)
        window.funbind('on_request_close', self._verify_exit_conditions)
        self.task_scheduler.stop()

    def _on_motion(self, *args, **kwargs):
        self.root.children[0].refresh_timeout()

    def _on_key_down(self, window, keycode, scancode=None, codepoint=None,
                     modifiers=None, **kwargs):
        if hasattr(self.root.children[0], 'refresh_timeout'):
            self.root.children[0].refresh_timeout()
        if scancode == 68 and not self._fullscreen_key_down:
            # F11 key is pressed
            window.fullscreen = False if window.fullscreen else 'auto'
            self._fullscreen_key_down = True
            return True

    def _on_key_up(self, window, keycode, scancode=None, codepoint=None,
                   modifiers=None, **kwargs):
        if scancode == 68 and self._fullscreen_key_down:
            self._fullscreen_key_down = False
            return True

    def _verify_exit_conditions(self, *args):
        active_book_workers = [
            x for x in self.task_scheduler.get_all_workers()
            if x.get('level_name') == 'low' and x.get('task')
        ]
        if not active_book_workers:
            return False
        self.action = ColoredYesNoActionPopupMixin(
            action_function=partial(self.stop, *args),
            title='Quit Scribe3?',
            message='There are still {} book tasks running.\n'
                    'Exiting now could [b]botch your uploads[/b].\n\n'
                    '[b]Exit anyway?[/b]'.format(len(active_book_workers))
        )
        self.action.display()
        return True

    def get_popup(self, popup_type, **kwargs):
        popup = self._popups.pop(popup_type, None)
        if popup:
            return popup
        else:
            popup_instance = popup_type(**kwargs)
            popup_instance.bind(on_dismiss=self.return_popup)
            return popup_instance

    def return_popup(self, popup):
        self._popups[type(popup)] = popup

    def get_screenshot_as_bytes(self):
        width, height = size = self.root_window.size
        pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        image = PIL_Image.frombytes('RGB', size, pixels, 'raw', 'RGB', 0, -1)
        fp = BytesIO()
        image.save(fp, format='PNG')
        fp.seek(0)
        return fp.read()

    def get_current_screen(self):
        if len(self.root.children) > 0:
            return self.root.children[0].get_current_screen()


class RuntimeErrorHandler(ExceptionHandler):

    def __init__(self, app):
        super(RuntimeErrorHandler, self).__init__()
        self.app = app
        self._exc_info = None

    def handle_exception(self, exception):
        if isinstance(exception, KeyboardInterrupt):
            return ExceptionManager.RAISE
        new_exc_info = sys.exc_info()
        if self._exc_info and self._exc_info[0] == new_exc_info[0]:
            return ExceptionManager.RAISE
        Logger.exception('Scribe3App: Mainthread runtime error')
        self._exc_info = new_exc_info
        root = self.app.root
        root_widget = root.children[0]
        root_window = self.app.root_window
        for widget in root_window.children[:]:
            root_window.remove_widget(widget)
        if type(root_widget).__name__ == 'ScribeWidget':
            try:
                root_widget.ids._capture_screen.disable_capture_actions()
                root_widget.ids._capture_screen.stop_autoshoot_capture()
                root_widget.ids._screen_manager.current_screen.disabled = True
            except Exception:
                pass
        self.show_runtime_error_popup()
        return ExceptionManager.PASS

    def show_runtime_error_popup(self):
        from ia_scribe.uix.components.poppers.popups import RuntimeErrorPopup
        popup = RuntimeErrorPopup()
        popup.bind(on_submit=self._on_runtime_error_popup_submit)
        popup.open()

    def _on_runtime_error_popup_submit(self, popup, data):
        option, message = data['option'], data['message']
        extra = {'user_message': message} if message else None
        if option == popup.OPTION_EXIT:
            self.app.root_window.hide()
            raven_client.captureException(exc_info=self._exc_info, extra=extra)
            time.sleep(3)
            self.app.stop()
        elif option == popup.OPTION_RESTART:
            raven_client.captureException(exc_info=self._exc_info, extra=extra)
            restart_app()
