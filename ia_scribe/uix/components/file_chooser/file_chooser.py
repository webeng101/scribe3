from os.path import join, dirname
from threading import Thread

from kivy.clock import mainthread
from kivy.lang import Builder
from kivy.uix.modalview import ModalView

from ia_scribe.uix.components.file_chooser.backend import LinuxFileChooser

Builder.load_file(join(dirname(__file__), 'file_chooser.kv'))


class FileChooser(ModalView):
    '''Widget to open native file chooser for file or directory selection.

    :Events:
        `on_selection`: Dispatched when user selects file or directory.


    Use following methods will open chooser:

        `open_file`: to select one or multiple files to be opened
        `save_file`: for user to choose directory and file name to save
        `choose_dir`: to select one or multiple directories

    See https://github.com/kivy/plyer/blob/master/plyer/facades/filechooser.py
    for list of arguments that can be passed to these methods.

    Native file chooser window will open in separate thread, so Kivy's main
    loop will continue to run.
    '''

    __events__ = ('on_selection',)

    def __init__(self, **kwargs):
        self._chooser_window = LinuxFileChooser()
        self._selection = None
        super(FileChooser, self).__init__(**kwargs)

    def open_file(self, **kwargs):
        self._start_file_chooser('open_file', **kwargs)

    def save_file(self, **kwargs):
        self._start_file_chooser('save_file', **kwargs)

    def choose_dir(self, **kwargs):
        self._start_file_chooser('choose_dir', **kwargs)

    def dismiss(self, *largs, **kwargs):
        if not self._window:
            return self
        self._chooser_window.cancel()
        selection = self._selection
        self._selection = None
        self.dispatch('on_selection', selection)
        self.dispatch('on_dismiss')
        self._real_remove_widget()
        return self

    def _start_file_chooser(self, mode, **kwargs):
        if self._window:
            return
        thread = Thread(target=self._thread_run,
                        args=(mode,),
                        kwargs=kwargs,
                        name='FileChooserThread')
        thread.daemon = True
        self.open()
        thread.start()

    def _thread_run(self, mode, **kwargs):
        method = getattr(self._chooser_window, mode)
        selection = method(**kwargs)
        if not self._window:
            return
        self._selection = selection
        mainthread(self.dismiss)()

    def on_selection(self, selection):
        pass
