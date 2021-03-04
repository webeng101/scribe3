'''
Label printing extension

This app allows the user to:
- re-print the label for an identifier that's already been uploaded to. The typical case here is that the metadata for that item has been changed (e.g. boxid)
- modify said metadata (boxid)

'''


from datetime import datetime
from os.path import join, dirname, expanduser
from uuid import uuid4

from ia_scribe.tasks.ui_handlers.book import GenerateAndPrintSlipUIHandler, \
    LiteMetadataViaIdentifierTaskUIHandler
from ia_scribe.tasks.print_slip import SCANNED_SLIP, SCANNED_NO_MARC_SLIP
from ia_scribe.logger import Logger

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

class LabelAppContainer(Popup):

    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        self.library = kwargs.get('library')
        super(LabelAppContainer, self).__init__(**kwargs)

class LabelAppScreen(Screen):

    identifier = StringProperty(None)
    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        self.library = kwargs.get('library')
        super(LabelAppScreen, self).__init__(**kwargs)

    def _load_task_result_handler(self, ui_handler, task):
        Logger.info('LOAD TASK: Was task completed successfully? {}'.format(task.error))
        if not task.error:
            book = ui_handler.book
            book.reload_metadata()
            Logger.info('Now printing slip for {}'.format(book))
            task_handler = self._prepare_slip_print_task(book)
            self.task_scheduler.schedule(task_handler.task)

    def _load_book(self, identifier):
        Logger.info('Creating dummy book {}'.format(identifier))
        generated_uuid = str(uuid4())
        book = self.library.new_book(generated_uuid)
        Logger.info('Creating Load task')
        task_handler = LiteMetadataViaIdentifierTaskUIHandler(
            identifier = identifier,
            book = book,
            end_handler=self._load_task_result_handler,
        )
        self.task_scheduler.schedule(task_handler.task)

    def _print_task_result_handler(self, ui_handler, task):
        Logger.info('PRINT TASK: Was task completed successfully? {}'.format(task.error))
        Logger.info('Deleting dummy book {}'.format(task._book))
        task._book.do_move_to_trash()
        task._book.do_delete_anyway()


    def _prepare_slip_print_task(self, book):
        Logger.info('Now printing slip for {}'.format(book))
        slip_metadata = {}
        slip_type = SCANNED_SLIP if ('title' in book.metadata
                                     and 'creator' in book.metadata) \
            else SCANNED_NO_MARC_SLIP
        slip_metadata['identifier'] = book.identifier
        slip_metadata['datetime'] = datetime.now()
        task = GenerateAndPrintSlipUIHandler(
                                 type=slip_type,
                                 book=book,
                                 slip_metadata=slip_metadata,
                                 end_handler= self._print_task_result_handler)
        return task


    def load_identifier(self, identifier):
        Logger.info('User wants to load {}'.format(identifier))
        self._load_book(identifier)


# ------------------ Extension API entry points

def load_app(*args, **kwargs):
    app_screen = LabelAppContainer(*args, **kwargs)
    return app_screen


def get_entry_point(*args, **kwargs):
    return load_app(*args, **kwargs)

# -------------------- Kivy Standalone App entry point

if __name__ == "__main__":

    class Label_appApp(App):

        def build(self):
            from ia_scribe.tasks.task_scheduler import TaskScheduler
            task_scheduler = TaskScheduler()
            task_scheduler.start()

            from ia_scribe.book.library import Library
            library = Library()

            app_screen = LabelAppScreen(task_scheduler=task_scheduler,
                                        library=library)
            return app_screen

    Label_appApp().run()

else:
    # if we're loading the extension from inside
    Builder.load_file(join(dirname(__file__), 'label_app.kv'))
