import copy
import logging
import os, sys
import threading
from datetime import datetime
from functools import partial
from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from ia_scribe.uix.components.file_chooser import FileChooser

from ia_scribe import scribe_globals

from ia_scribe.uix.widgets.book.book_handler import BookHandler

from ia_scribe.uix.components.poppers.popups import (
    CalibrateCamerasPopup,
)

from ia_scribe.tasks.heartbeat import HeartbeatTask
from ia_scribe.tasks.book_tasks.download import SyncDownloadsTask
from ia_scribe.tasks.cd_tasks.download import DownloadCDTask
from ia_scribe.tasks.generic import GenericFunctionTask
from ia_scribe.tasks.book import MoveAlongSchedulerTask, MoveAlongBookTask
from ia_scribe.tasks.importer import ImportFolderTask
from ia_scribe.tasks.system_checks import SystemChecksTask
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.uix.actions.input import InputActionPopupMixin

from ia_scribe.ia_services.tts import check_metadata_registration

Builder.load_file(join(dirname(__file__), 'upload_widget.kv'))


def setup_worker_logger():
    LOG_FILENAME = 'upload_widget_{}.log'.format(datetime.now().strftime('%Y%m%d%H%M%S'))
    log_file_location = os.path.expanduser(os.path.join('~/.kivy/logs/', LOG_FILENAME))
    log = logging.getLogger('UploadWidget')
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(scribe_globals.LOGGING_FORMAT)
    handler.setFormatter(formatter)
    fh = logging.FileHandler(log_file_location)
    fh.setFormatter(formatter)
    log.addHandler(handler)
    log.addHandler(fh)
    log.propagate = 0
    return log


Logger = setup_worker_logger()


class UploadWidget(BoxLayout):
    '''UploadWidget

    This class initialize the main UI widget view::

        - with the book list and the dispatcher
        - the dispatcher is launched as a thead
        - all the dispatcher's functions are defined here
        - all the main interactions with the cluster republisher happens here
    '''

    num_books = NumericProperty()
    status_txt = StringProperty()
    num_results_tasks = StringProperty()
    num_waiting_tasks = StringProperty()
    num_pending_hiprio_tasks = StringProperty()
    num_pending_tasks = StringProperty()
    num_long_ops_tasks = StringProperty()
    scribe_widget = ObjectProperty()
    screen_manager = ObjectProperty()
    ia_session = ObjectProperty()
    book_metadata = ObjectProperty()
    library_view = ObjectProperty()
    books_db = ObjectProperty()
    task_scheduler = ObjectProperty()
    config = ObjectProperty()

    def __init__(self, **kwargs):
        self._book_list_lock = threading.Lock()
        self._worker_stop_event = threading.Event()
        self._worker_pause_event = threading.Event()
        super(UploadWidget, self).__init__(**kwargs)
        self.logger = Logger
        self.book_list = []
        self.book_metadata = None
        # We're optimists
        self.configuration_ok = True
        self._book_handler = None
        self._capture_screen = None
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, dt):
        self._capture_screen = self.scribe_widget.ids._capture_screen
        self._book_handler = BookHandler(self)
        library_view = self.library_view
        library_view.fbind(library_view.EVENT_BOOK_SELECT,
                           self._book_handler.on_select)

        library_header = library_view.ids.library_header
        library_header.fbind(library_header.EVENT_OPTION_SELECT,
                             self._on_library_option_select)
        self.book_list = self.books_db.library_list

        self.scribe_widget.books_db.subscribe(self._update_library_view_book)
        self.scribe_widget.books_db.subscribe(self._update_library_view_book, 'errors')

        books = self.create_library_view_books(self.book_list, [])
        Clock.schedule_once(partial(self.reload_book_list, books))

        self._bind_to_scheduler_events()
        self._schedule_one_off_tasks()
        self._schedule_periodic_tasks()

        if self.config.is_true('move_along_at_startup'):
            Logger.info('move_along_at_startup is enabled. Running book engine on every book.')
            books_sync = MoveAlongSchedulerTask(library=self.books_db,
                                                scheduling_callback=self.task_scheduler.schedule)
            self.task_scheduler.schedule(books_sync)

    def _scheduler_event_handler(self, scheduler, task):
        if not task or not task['task']:
            self.set_status_label('')
            return
        task_type = task['task'].name
        task_state = task['task'].state
        task_level = task['level_name']
        extra = '({})'.format(task['task']._book) if hasattr(task['task'], '_book') else ''
        logline = "[{task_state}] {task_level} | [b]{task_type}[/b]  {extra}".format(task_type=task_type,
                                                                                     task_level=task_level,
                                                                                     task_state=task_state,
                                                                                     extra=extra)
        self.set_status_label(logline)
        self.set_num_tasks_message()

    def _bind_to_scheduler_events(self):
        self.task_scheduler.fbind('on_task_item_add', self._scheduler_event_handler)
        self.task_scheduler.fbind('on_task_item_remove', self._scheduler_event_handler)
        self.task_scheduler.fbind('on_task_item_change', self._scheduler_event_handler)
        self.task_scheduler.fbind('on_worker_item_change', self._scheduler_event_handler)

    def _schedule_one_off_tasks(self):
        system_checks = SystemChecksTask()
        self.task_scheduler.schedule(system_checks)

    def _schedule_periodic_tasks(self):
        scheduler_interval = self.config.get_numeric_or_none('scheduler_interval')
        if scheduler_interval:
            heartbeat = HeartbeatTask(periodic=True,
                                      interval=scheduler_interval,
                                      library=self.books_db)
            self.task_scheduler.schedule(heartbeat)

            books_sync = SyncDownloadsTask(periodic=True,
                                           interval=scheduler_interval,
                                           library=self.books_db,
                                           scheduling_callback=self.task_scheduler.schedule)
            self.task_scheduler.schedule(books_sync)

            md_check = GenericFunctionTask(
                name='Btserver Metadata sync',
                function=check_metadata_registration,
                periodic=True,
                interval=scheduler_interval,
                args=[Logger]
            )
            self.task_scheduler.schedule(md_check)

        periodic_move_along_interval = self.config.get_numeric_or_none('periodic_move_along_interval')
        if periodic_move_along_interval:
            move_along = MoveAlongSchedulerTask(periodic=True,
                                                library=self.books_db,
                                                scheduling_callback=self.task_scheduler.schedule,
                                                interval=periodic_move_along_interval,
                                                )
            self.task_scheduler.schedule(move_along)

    def log(self, m):
        self.logger.debug(m)
        Clock.schedule_once(partial(self.set_status_callback, m))

    def _on_library_option_select(self, library_header, option):
        if option == library_header.OPTION_NEW_BOOK:
            self.create_new_book()
        elif option == library_header.OPTION_IMPORT_BOOK:
            self.import_book()
        elif option == library_header.OPTION_NEW_CD:
            self.new_cd()

    def toggle_worker(self, button, button_task_manager):
        if not self.task_scheduler.is_running():
            self.task_scheduler.start()
            button.source_normal = 'icon_mark_check_32.png'
            button_task_manager.disabled = False
            self.set_num_tasks_message()
            self._schedule_periodic_tasks()
        else:
            self.task_scheduler.stop()
            button.source_normal = 'button_spread_delete_red.png'
            button_task_manager.disabled = True

    def create_new_book(self):
        if not self.scribe_widget.cameras.are_calibrated():
            self.show_calibration_popup()
        else:
            screen = self.scribe_widget.ids._book_metadata_screen
            screen.backend.create_new_book()
            self.screen_manager.current = screen.name

    def import_book(self):
        filechooser = FileChooser()
        callback = partial(self.on_import_popup_submit)
        filechooser.bind(on_selection=callback)
        filechooser.choose_dir(title='Select folder',
                               icon='./images/window_icon.png',
                               filters=[],
                               multiple=False,
                               path='~')

    def new_cd(self):
        self.action = InputActionPopupMixin(
            title='Load CD',
            message='Insert here the identifier you would like to load',
            action_function=self.load_cd,
        )
        self.action.display()

    def load_cd(self, action, popup, identifier):
        task_handler = GenericUIHandler(
            task_type=DownloadCDTask,
            library=self.books_db,
            identifier=identifier
        )
        self.task_scheduler.schedule(task_handler.task)

    def on_import_popup_submit(self, file_chooser, directory):
        if not directory:
            return
        import_task_handler = GenericUIHandler(task_type=ImportFolderTask,
                                               path=directory[0],
                                               library=self.books_db)
        self.task_scheduler.schedule(import_task_handler.task)

    def show_calibration_popup(self):
        popup = CalibrateCamerasPopup()
        popup.bind(on_submit=self.on_calibration_popup_submit)
        popup.open()

    def on_calibration_popup_submit(self, popup, option):
        if option == popup.OPTION_GOTO_CALIBRATION:
            self.scribe_widget.show_calibration_screen(
                target_screen='book_metadata_screen',
                extra={'should_create_new_book': True}
            )
        elif option == popup.OPTION_CONTINUE:
            self.scribe_widget.cameras.set_calibrated()
            screen = self.scribe_widget.ids._book_metadata_screen
            screen.backend.create_new_book()
            self.screen_manager.current = screen.name

    def set_status_label(self, message):
        self.status_txt = message

    def reload_book_list(self, books, *args):
        self.num_books = len(books)
        Logger.debug('Reloaded book_list: Total books = {}'
                     .format(len(books)))
        self.library_view.books[:] = books

    def create_library_view_books(self, book_list, processed_books):
        books = []
        for book in book_list:
            copied = copy.deepcopy(book.as_dict())
            books.append(copied)
        return books

    def set_status_callback(self, value, *args):
        self.status_txt = value

    def set_num_tasks_message(self):
        task_items = self.task_scheduler.get_all_tasks()
        self.num_pending_tasks = str(len([x for x in task_items if x['task'].state == 'pending']))
        self.num_pending_hiprio_tasks = str(
            len([x for x in task_items if x['level_name'] == 'high' and x['task'].state == 'pending']))
        self.num_long_ops_tasks = str(
            len([x for x in task_items if x['level_name'] == 'low' and x['task'].state == 'pending']))
        self.num_results_tasks = str(len([x for x in task_items if x['task'].state == 'done']))
        self.num_waiting_tasks = str(len([x for x in task_items if x['task'].state == 'running']))

    def _update_library_view_book(self, book, message, *args):

        if message == 'book_created' or message == 'item_deleted' or message == 'cd_created':
            books = self.create_library_view_books(self.book_list, [])
            Clock.schedule_once(partial(self.reload_book_list, books))
        elif message == 'state_change':
            book_engine_task = MoveAlongBookTask(book=book)
            self.task_scheduler.schedule(book_engine_task)
            self.library_view.update_book(book['uuid'], book.as_dict())
        else:
            self.library_view.update_book(book['uuid'], book.as_dict())
