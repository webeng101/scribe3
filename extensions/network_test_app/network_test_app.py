from datetime import datetime
from os.path import join, dirname, expanduser

from ia_scribe.tasks.system_checks import NetworkCheckTask
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.logger import Logger

from kivy.app import App
from kivy.lang import Builder
from kivy.core.clipboard import Clipboard
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen



class NetworkTestAppContainer(Popup):

    task_scheduler = ObjectProperty()
    library = ObjectProperty()

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        super(NetworkTestAppContainer, self).__init__(**kwargs)


class NetworkTestAppScreen(Screen):

    task_scheduler = ObjectProperty()
    log = StringProperty('Ready to run test.\n')

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.get('task_scheduler')
        super(NetworkTestAppScreen, self).__init__(**kwargs)

    def _log(self, text):
        self.log += str(text) + '\n'

    def _launch_test(self):
        Logger.info('Creating Network Test task')
        task_handler = GenericUIHandler(
            task_type=NetworkCheckTask,
            scheduling_callback=self.task_scheduler.schedule,
            increment_callback=self._test_result_handler,
        )
        self.task_scheduler.schedule(task_handler.task)

    def _test_result_handler(self, exit_code, output, error, task):
        self._log('----------------- {} -----------------'.format(task._command))
        if output:
            self._log(output)
        if error:
            self._log(error)
        self._log('--------------------------------------')

    def start_test(self, *args):
        Logger.info('Starting test')
        self._log('Test started...')
        self._launch_test()

    def copy_results_to_clipboard(self):
        Clipboard.copy(self.log)



# ------------------ Extension API entry points

def load_app(*args, **kwargs):
    app_screen = NetworkTestAppContainer(*args, **kwargs)
    return app_screen


def get_entry_point(*args, **kwargs):
    return load_app(*args, **kwargs)

# -------------------- Kivy Standalone App entry point

if __name__ == "__main__":

    class NetworkTest_appApp(App):

        def build(self):
            from ia_scribe.tasks.task_scheduler import TaskScheduler
            task_scheduler = TaskScheduler()
            task_scheduler.start()

            app_screen = NetworkTestAppScreen(task_scheduler=task_scheduler,)
            return app_screen

    NetworkTest_appApp().run()

else:
    # if we're loading the extension from inside
    Builder.load_file(join(dirname(__file__), 'network_test_app.kv'))
