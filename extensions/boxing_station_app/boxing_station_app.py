import re, zlib
from datetime import datetime
from os.path import join, dirname, expanduser
from uuid import uuid4

from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.tasks.composite import MakeAndPrintSlipTask
from ia_scribe.tasks.book import BookTask
from ia_scribe.tasks.print_slip import REJECTED_DO_NOT_WANT_SLIP

from ia_scribe.uix.actions.error import ShowErrorAction
from ia_scribe.book.metadata import get_sc_metadata
from ia_scribe.config.config import Scribe3Configuration

from ia_scribe.logger import Logger
from ia_scribe import scribe_globals

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, DictProperty, BooleanProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

import base64, pickle

config = Scribe3Configuration()

class BoxingAppContainer(Popup):

    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        self.library = kwargs.get('library')
        super(BoxingAppContainer, self).__init__(**kwargs)

class BoxingAppScreen(Screen):

    identifier = StringProperty(None)
    task_scheduler = ObjectProperty()
    library = ObjectProperty()
    sc_metadata = DictProperty()
    current_boxid = StringProperty()
    BOXID_VALIDATION_REGEX = config.get('boxid_validation_regex', '^IA\d{6,7}$')
    print_slip = BooleanProperty(False)
    banner_message = StringProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        self.library = kwargs.get('library')
        super(BoxingAppScreen, self).__init__(**kwargs)

    def load_qr_data(self, qrcode_content):
        try:
            qr_bytes = qrcode_content.encode('utf-8')
            base64_decoded = base64.b64decode(qr_bytes)
            decompressed = zlib.decompress(base64_decoded)
            metadata = pickle.loads(decompressed)
            if not self.is_boxid_valid():
                self.action = ShowErrorAction(message='You must insert a valid boxid')
                self.action.display()
            else:
                self._process_book(metadata)
        except Exception as e:
            self.action = ShowErrorAction(message='The following error occured:\n\n[b]{}[/b]'.format(str(e)))
            self.action.display()

    def _process_book(self, metadata):
        generated_uuid = str(uuid4())
        sc_metadata = get_sc_metadata()
        user = sc_metadata.get('operator')
        scanningcenter = sc_metadata.get('scanningcenter')
        scanner = sc_metadata.get('scanner')
        boxid =  self.current_boxid
        Logger.info('Creating dummy book {}'.format(generated_uuid))
        book = self.library.new_book(generated_uuid,
                                             operator=user,
                                             scanner=scanner,
                                             scanningcenter=scanningcenter,
                                             boxid=boxid)
        book.initialze_metaxml()
        slip_metadata = metadata
        slip_metadata['boxid'] = boxid
        slip_metadata['datetime'] = datetime.now()
        slip_metadata['reason'] = 'Duplicate'
        slip_metadata['comment'] = 'BOXED'
        # This is necessary to tell rejection tracker to put this event in a separate itemset
        slip_metadata['boxed'] = True
        slip_metadata['operator'] = book.operator
        book.set_slip_metadata(REJECTED_DO_NOT_WANT_SLIP, slip_metadata.copy())

        # This is mostly a placeholder to demonstrate we can tell the user what to do on screen.
        self.banner_message = 'Put this book in box {}'.format(metadata.get('keep_dupe_status_code'))

        task_handler = self._reject_and_print_slip(book, slip_metadata) \
                            if self.print_slip \
                        else self._reject_without_printing_slip(book)
        task_handler.task.fbind('on_end', self._on_task_end)
        self.task_scheduler.schedule(task_handler.task)

    def _reject_and_print_slip(self, book, slip_metadata):
        task = GenericUIHandler(MakeAndPrintSlipTask,
                                 book=book,
                                 type=REJECTED_DO_NOT_WANT_SLIP,
                                 slip_metadata=slip_metadata,
                                 transition='do_reject',
                                )
        return task

    def _reject_without_printing_slip(self, book):
        task = GenericUIHandler(BookTask,
                                book=book,
                                command='do_reject',
                                )
        return task

    def _on_task_end(self, task):
        book_obj = task.book if hasattr(task, 'book') else task._book
        self.banner_message = 'Done with {}'.format(book_obj)
        self.ids.identifier_input.text = ''
        self.ids.identifier_input.focus = True
        Clock.schedule_once(self._empty_banner_message, 3)

    def _empty_banner_message(self, *args, **kwargs):
        self.banner_message = ''

    def is_boxid_valid(self):
        pattern = self.BOXID_VALIDATION_REGEX
        res = re.match(pattern, self.current_boxid)
        if res:
            if len(self.current_boxid) != res.span()[1]:
                res = False
            else:
                res = True
        return res


# ------------------ Extension API entry points

def load_app(*args, **kwargs):
    app_screen = BoxingAppContainer(*args, **kwargs)
    return app_screen


def get_entry_point(*args, **kwargs):
    return load_app(*args, **kwargs)

# -------------------- Kivy Standalone App entry point

if __name__ == "__main__":

    class Boxing_station_appApp(App):

        def build(self):
            from ia_scribe.tasks.task_scheduler import TaskScheduler
            task_scheduler = TaskScheduler()
            task_scheduler.start()

            from ia_scribe.book.library import Library
            library = Library()

            app_screen = BoxingAppScreen(task_scheduler=task_scheduler,
                                        library=library)
            return app_screen

    Boxing_station_appApp().run()

else:
    # if we're loading the extension from inside
    Builder.load_file(join(dirname(__file__), 'boxing_station_app.kv'))
