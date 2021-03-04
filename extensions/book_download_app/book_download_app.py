'''
Label printing extension

This app allows the user to:
- re-print the label for an identifier that's already been uploaded to. The typical case here is that the metadata for that item has been changed (e.g. boxid)
- modify said metadata (boxid)

'''


from datetime import datetime
from os.path import join, dirname, expanduser
from uuid import uuid4

from ia_scribe.tasks.book_tasks.download import DownloadBookTask
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.logger import Logger

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

class BookDownloadAppContainer(Popup):

    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        self.library = kwargs.get('library')
        super(BookDownloadAppContainer, self).__init__(**kwargs)

class BookDownloadAppScreen(Screen):

    identifier = StringProperty(None)
    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        self.library = kwargs.get('library')
        super(BookDownloadAppScreen, self).__init__(**kwargs)

    def _load_book(self, identifier):
        Logger.info('Creating Load task')
        task_handler = GenericUIHandler(
            task_type=DownloadBookTask,
            library=self.library,
            identifier=identifier)
        self.task_scheduler.schedule(task_handler.task)

    def load_identifier(self, identifier):
        Logger.info('User wants to load {}'.format(identifier))
        self._load_book(identifier)


# ------------------ Extension API entry points

def load_app(*args, **kwargs):
    app_screen = BookDownloadAppContainer(*args, **kwargs)
    return app_screen


def get_entry_point(*args, **kwargs):
    return load_app(*args, **kwargs)

# -------------------- Kivy Standalone App entry point

if __name__ == "__main__":

    class Book_dowload_appApp(App):

        def build(self):
            from ia_scribe.tasks.task_scheduler import TaskScheduler
            task_scheduler = TaskScheduler()
            task_scheduler.start()

            from ia_scribe.book.library import Library
            library = Library()

            app_screen = BookDownloadAppScreen(task_scheduler=task_scheduler,
                                        library=library)
            return app_screen

    Book_dowload_appApp().run()

else:
    # if we're loading the extension from inside
    Builder.load_file(join(dirname(__file__), 'book_download_app.kv'))
