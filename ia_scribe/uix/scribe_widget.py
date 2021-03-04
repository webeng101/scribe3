import os
import webbrowser
from os.path import join, dirname
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import ObjectProperty, StringProperty
from kivy.support import install_twisted_reactor
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.exceptions import ScribeException, CredentialsError
from ia_scribe.book.metadata import get_sc_metadata, set_sc_metadata
from ia_scribe.cameras.optics import Cameras
from ia_scribe.cameras.camera_threads import _setup_camera_threads
from ia_scribe.uix.widgets.taskman.stakhanov_widget import StakhanovWidget
from ia_scribe.tasks.generic import GenericFunctionTask
from ia_scribe.tasks.notifications_recurring import NotificationsCleanerTask

from ia_scribe.ia_services.rcs import RCS
from ia_scribe.uix.screens.help.help import Help
from ia_scribe.uix.components.poppers.popups import InfoPopup
from ia_scribe.uix.components.toolbars.top_bar import TopBar
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.notifications.adapters import book_adapter as notifications_book_adapter
from ia_scribe.notifications.adapters import book_error_adapter as notifications_book_error_adapter
from ia_scribe.uix.widgets.notification_center.notification_center import NotificationCenterWidget
from ia_scribe.uix.widgets.cli.cli_widget import CLIWidgetPopup

Builder.load_file(join(dirname(__file__), 'scribe_widget.kv'))

IGNORE_LOGOUT_SCREENS = ['wizard_screen', 'user_switch_screen',]


class ScribeWidget(BoxLayout):

    books_db = ObjectProperty()
    task_scheduler = ObjectProperty()
    config = ObjectProperty()
    notifications_manager = ObjectProperty()
    rcs = ObjectProperty()

    top_bar = ObjectProperty()

    _cameras_status = StringProperty()

    def __init__(self, **kwargs):
        self._help_opened = False
        self._help_key_down = False
        self.timeout_event = None
        super(ScribeWidget, self).__init__(**kwargs)

        try:
            self.config = Scribe3Configuration()
            self.config.validate()
            self.init_pid_file()

        except CredentialsError as e:
            # if this is raised, we show the wizard
            msg = '[b]It looks like there is an issue with your credentials[/b].\n' \
                  '\n{}\nClick the button to begin the wizard.'.format(e.msg)
            popup = InfoPopup(title='Logged out', message=msg, auto_dismiss=False)
            popup.bind(on_submit=self.begin_wizard)
            popup.open()
            return

        except ScribeException as e:
            # if this is raised, the app can no longer continue
            msg = 'Scribe3 could not initialize\nbecause of the following error:' \
                  '\n\n[b]{}[/b].\n\nClick the button to close.'.format(str(e))
            popup = InfoPopup(title='Initialization error', message=msg, auto_dismiss=False)
            app = App.get_running_app()
            popup.bind(on_submit=app.stop)
            popup.open()
            return

        #self.config.subscribe(get_adapter('config'))

        md_version = {'tts_version': scribe_globals.BUILD_NUMBER}
        set_sc_metadata(md_version)

        screen_manager = self.ids._screen_manager
        screen_manager.bind(current=self._on_current_screen)

        self._init_top_bar(self.config)
        self.help = Help()

        self.help.fbind('on_open', self._on_help_open)
        self.help.fbind('on_dismiss', self._on_help_dismiss)

        self.notifications_manager = NotificationManager()

        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self.cameras = Cameras()
        self.cameras.fbind('camera_ports', self.on_camera_ports)
        self.on_camera_ports(self.cameras, self.cameras.camera_ports)
        self.cameras.initialize()

        self.left_queue, \
        self.right_queue, \
        self.foldout_queue = _setup_camera_threads(self.cameras)

        manager = self.ids._screen_manager
        if manager.current == 'upload_screen':
            self.ids._upload_screen.use_tooltips = True
        self.help.target_widget = manager
        md_screen = self.ids._book_metadata_screen

        md_screen.camera_system = self.cameras
        md_screen.bind(on_done=self._on_book_metadata_screen_done,
                       on_cancel=self._on_book_metadata_screen_cancel)
        md_screen.backend.bind(on_new_book_created=self._on_new_book_created)
        capture_screen = self.ids._capture_screen
        capture_screen.bind(on_book_reset=self._on_book_reset,
                            on_start_new_book=self._on_start_new_book,
                            on_edit_metadata=self._on_book_edit_metadata)
        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_key_up=self._on_key_up)

        self.task_scheduler.start()

        self.setup_rcs()

        extensions_screen = self.ids['_extensions_screen']
        extensions_screen.task_scheduler = self.task_scheduler
        extensions_screen.library = self.books_db

        user_switch_screen = self.ids['_user_switch_screen']
        user_switch_screen.task_scheduler = self.task_scheduler

        if not self.config.is_true('stats_disabled'):
            self.setup_stats_backend()

        self.setup_notification_center()

        if self.config.is_true('enable_c2'):
            self.setup_command_and_control()

        if self.config.is_true('enable_webapi'):
            self.setup_webapi()

        logout_timeout = self.config.get_numeric_or_none('logout_timeout')
        if logout_timeout:
            Logger.info('Detected logout timeout of {} seconds; initializing scheduler'.format(logout_timeout))
            self.timeout_event = Clock.schedule_interval(self.do_timeout, logout_timeout)

    def refresh_timeout(self):
        timeout = self.config.get_numeric_or_none('logout_timeout')
        if self.timeout_event:
            self.timeout_event.cancel()
            if timeout:
                self.timeout_event = Clock.schedule_interval(self.do_timeout, timeout)

    def do_timeout(self, dt):
        current = self.get_current_screen()
        if self.config.is_true('do_not_logout_from_capture_screens'):
            IGNORE_LOGOUT_SCREENS.extend(['capture_screen', 'reshoot_screen'])
        if current not in IGNORE_LOGOUT_SCREENS:
            self.show_user_switch_screen()

    def setup_rcs(self):
        self.rcs = RCS()
        self.rcs.attach_scheduler(self.task_scheduler)
        self.rcs.schedule_sync()

    def setup_stats_backend(self):
        from ia_scribe.breadcrumbs.api import get_adapter, log_event, process_stats
        self.books_db.subscribe(get_adapter('library'))
        self.ids._screen_manager.bind(current=get_adapter('screen_manager'))
        self.top_bar.bind(on_option_select=get_adapter('top_bar'))
        self.cameras.fbind('camera_ports', get_adapter('cameras'))
        log_event('app', 'started', None, None)

        stats_processor = GenericFunctionTask(
            name='Stats cruncher',
            function=process_stats,
            periodic=False
        )
        self.task_scheduler.schedule(stats_processor)

    def setup_notification_center(self):
        self.books_db.subscribe(notifications_book_adapter)
        self.books_db.subscribe(notifications_book_error_adapter, topic='errors')
        self.notifications_manager.bind(on_notification_added=self.top_bar.highlight_notification)
        interval = self.config.get_numeric_or_none('notification_cleanup_interval')
        if interval:
            task = NotificationsCleanerTask(periodic=True,
                                        interval=interval)
            self.task_scheduler.schedule(task)

    def setup_command_and_control(self):
        # fix for pyinstaller packages app to avoid ReactorAlreadyInstalledError
        import sys
        if 'twisted.internet.reactor' in sys.modules:
            del sys.modules['twisted.internet.reactor']

        # install twisted reactor
        install_twisted_reactor()
        from ia_scribe.ia_services import command_and_control

        self.c2 = command_and_control.S3C2()
        # Attach settings screen widget to c2
        self.ids._screen_manager.get_screen('settings_screen').screens['c2'].ids['c2_widget'].attach(self.c2)

        if not command_and_control.registration_ok:
            self.notifications_manager.add_notification(title='C2 error',
                                                        message='Command and control service failed to load. '
                                                        'The error was: [b]{}[/b] | Contact an admin to resolve.'.format(
                                                            command_and_control.registration_error),
                                                        is_sticky=True,
                                                        is_error=True,
                                                        notification_type='system', )
            return

        self.c2.callback = partial(self.notifications_manager.add_notification,
                              title='Command and Control', notification_type='system')
        self.c2.connect_to_server()



    def setup_webapi(self):
        from ia_scribe.services.webserver import start_webserver
        start_webserver()

    def toggle_worker(self):
        self.ids._upload_widget.toggle_worker(self.ids.button_toggle_worker, self.ids.button_task_manager)

    def show_task_status(self):
        root = StakhanovWidget()
        root.new_manager.attach_scheduler(self.task_scheduler)
        popup = Popup(
            title='Tasks list', content=root, size_hint=(None, None),
            size=('1040dp', '800dp')
        )
        popup.bind(on_dismiss=root.release_refs)
        popup.open()

    def show_notification_center(self):
        root = NotificationCenterWidget()
        root.attach(self.notifications_manager, self.ids._upload_widget._book_handler)
        popup = Popup(
            title='Notifications', content=root, size_hint=(None, None),
            size=('1080dp', '880dp')
        )
        popup.bind(on_dismiss=root.detach)
        popup.open()
        self.top_bar.remove_highlight_notification()

    def show_help_center(self):
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = 'help_center_screen'

    def show_cameras_status(self):
        self.show_camera_screen()

    def init_pid_file(self):
        Logger.info('PID Init: Begin')
        config_dir = scribe_globals.CONFIG_DIR
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        if not os.access(config_dir, os.W_OK | os.X_OK):
            raise ScribeException('Config dir "{}" not writable'
                                  .format(config_dir))
        # Check to see if another copy of the app is running
        # and if needed, remove stale pidfiles
        path = os.path.join(config_dir, 'scribe_pid')
        Logger.info('PID Init: Looking for pidfile at {}'.format(path))
        if os.path.exists(path):
            f = open(path)
            old_pid = f.read().strip()
            f.close()
            pid_dir = os.path.join('/proc', old_pid)
            if os.path.exists(pid_dir):
                Logger.error('There seems to be a pid file at {}. Try '
                             'removing it and relaunching '
                             'the application.'.format(str(pid_dir)))
                raise ScribeException('Another copy of the Scribe application '
                                      'is running!')
            else:
                os.unlink(path)

        pid = os.getpid()
        f = open(path, 'w')
        f.write(str(pid))
        f.close()
        Logger.info('PID Init: End')

    def begin_wizard(self, *args, **kwargs):
        if len(args) >1:
            try:
                args[0].dismiss()
            except:
                pass

        self.ids._screen_manager.transition.direction = 'right'
        self.ids._screen_manager.current = 'wizard_screen'

    def back_to_library(self):
        '''Set the screen_manager go back to the library UI view.'''
        manager = self.ids._screen_manager
        if manager.current != 'upload_screen':
            manager.transition.direction = 'right'
            manager.current = 'upload_screen'

    def _init_top_bar(self, config):
        self.top_bar = top_bar = TopBar()
        meta = get_sc_metadata()
        top_bar.username = meta.get('operator', None) or ''
        top_bar.machine_id = meta.get('scanner', None) or ''
        top_bar.bind(on_option_select=self._on_top_bar_option_select)
        self.config.subscribe(self._on_config_change)
        # TODO: Better way to check if user is logged in
        if 's3' in self.config:
            self.add_widget(top_bar, len(self.children))

    def _on_config_change(self, event_type, payload):
        key, value = payload
        # though we read this value from metadata.xml, we use the shadow
        # value in configuration to get a change notification
        if event_type=='key_set' and key == 'operator':
            meta = get_sc_metadata()
            self.top_bar.username = meta.get('operator', None) or ''

    def _on_top_bar_option_select(self, top_bar, option):
        # TODO: Don't hardcode top bar options
        if option == 'home':
            self.back_to_library()
        elif option == 'change_user':
            self.show_user_switch_screen()
        elif option == 'settings':
            self.show_settings_screen()
        elif option == 'logout':
            self.show_logout_screen()
        elif option == 'calibrate_cameras':
            self.show_calibration_screen(target_screen='upload_screen')
        elif option == 'help':
            link = 'https://wiki.archive.org/twiki/bin/view/BooksDigitization/WebHome'
            webbrowser.open(link)
        elif option == 'visit':
            link = 'https://archive.org'
            webbrowser.open(link)
        elif option == 'extensions':
            self.show_extensions_screen()
        elif option == 'cli':
            self.show_cli_popup()
        elif option == 'stats':
            self.show_stats_screen()
        elif option == 'notification_center':
            self.show_notification_center()
        elif option == 'help_center':
            self.show_help_center()
        elif option == 'exit':
            self.exit_app()

    def _on_current_screen(self, screen_manager, current):
        self.top_bar.use_back_button = current not in ['upload_screen', 'user_switch_screen']

    def _on_book_metadata_screen_done(self, md_screen):
        capture_screen = self.ids._capture_screen
        capture_screen.target_extra = md_screen.target_extra
        capture_screen.book_dir = md_screen.backend.book_path
        manager = self.ids._screen_manager
        manager.transition.direction = 'up'
        manager.current = capture_screen.name

    def _on_book_metadata_screen_cancel(self, md_screen):
        manager = self.ids._screen_manager
        if md_screen.target_extra:
            manager.transition.direction = 'up'
            self.ids._capture_screen.target_extra = md_screen.target_extra
            manager.current = self.ids._capture_screen.name
        else:
            manager.transition.direction = 'left'
            manager.current = self.ids._upload_screen.name

    def _on_book_reset(self, capture_screen):
        self.back_to_library()

    def _on_start_new_book(self, capture_screen):
        md_screen = self.ids._book_metadata_screen
        md_screen.backend.create_new_book()
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = md_screen.name

    def _on_book_edit_metadata(self, capture_screen):
        md_screen = self.ids._book_metadata_screen
        md_screen.target_extra = capture_screen.create_state()
        md_screen.backend.book_path = capture_screen.book_dir
        manager = self.ids._screen_manager
        manager.transition.direction = 'down'
        manager.current = md_screen.name

    def _on_new_book_created(self, md_screen_backend, book):
        pass

    def _on_key_down(self, window, keycode, scancode, codepoint=None,
                     modifiers=None, **kwargs):
        if scancode == 58 and not self._help_key_down:
            self._help_key_down = True
            self.help.dismiss() if self._help_opened else self.help.open()
            return True

    def _on_key_up(self, window, keycode, scancode, codepoint=None,
                   modifiers=None, **kwargs):
        if scancode == 58 and self._help_key_down:
            self._help_key_down = False
            return True

    def _on_help_open(self, help):
        manager = self.ids._screen_manager
        manager.current_screen.disabled = True
        self._help_key_down = False
        self._help_opened = True

    def _on_help_dismiss(self, help):
        manager = self.ids._screen_manager
        manager.current_screen.disabled = False
        self._help_key_down = False
        self._help_opened = False

    def on_camera_ports(self, cameras, camera_ports):
        num_cams = cameras.get_num_cameras()
        temp = ['| {} camera(s)'.format(num_cams)]
        if num_cams != 0:
            for side, metadata in cameras.get_active_cameras().items():
                temp.append('{}: {}'.format(side, metadata['model']))
        self._cameras_status = ' | '.join(temp)

    def show_user_switch_screen(self):
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = 'user_switch_screen'

    def show_upload_screen(self):
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = 'upload_screen'

    def show_metadata_screen(self):
        manager = self.ids._screen_manager
        manager.get_screen('settings_screen').setup_manager(manager)
        manager.get_screen('settings_screen').go_screen('metadata')
        manager.transition.direction = 'left'
        manager.current = 'settings_screen'

    def show_camera_screen(self):
        manager = self.ids._screen_manager
        manager.get_screen('settings_screen').setup_manager(manager)
        manager.get_screen('settings_screen').go_screen('camera')
        manager.transition.direction = 'left'
        manager.current = 'settings_screen'

    def show_settings_screen(self):
        manager = self.ids._screen_manager
        manager.get_screen('settings_screen').setup_manager(manager)
        manager.transition.direction = 'left'
        manager.current = 'settings_screen'

    def show_logout_screen(self):
        # Only using logout screen method `archive_logout`
        # which logouts the user and restarts the app
        manager = self.ids._screen_manager
        login_screen = manager.get_screen('login_screen')
        login_screen.archive_logout()

    def show_calibration_screen(self, target_screen='capture_screen',
                                extra=None):
        calibration_screen = self.ids['_calibration_screen']
        calibration_screen.target_screen = target_screen
        calibration_screen.target_extra = extra
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = 'calibration_screen'

    def show_extensions_screen(self):
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = 'extensions_screen'

    def show_stats_screen(self):
        manager = self.ids._screen_manager
        manager.transition.direction = 'left'
        manager.current = 'stats_screen'

    def show_cli_popup(self):
        app = App.get_running_app()
        root = app.get_popup(CLIWidgetPopup,
                             size_hint=(.90, .90))
        root.screen_manager = self.ids._screen_manager
        root.open()

    def get_current_screen(self):
        return self.ids._screen_manager.current

    def get_current_user(self):
        return self.top_bar.username

    def exit_app(self):
        app = App.get_running_app()
        app.stop()
