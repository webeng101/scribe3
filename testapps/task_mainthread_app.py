import time

from ia_scribe.tasks.task_base import TaskBase
from testapps.task_base_app import TaskApp


class SimpleTask(TaskBase):

    def create_pipeline(self):
        return [self._step for _ in range(500)]

    def _step(self):
        time.sleep(1/30.0)
        self.dispatch_progress('Step %s' % (self._current_index + 1))


class MainthreadTaskApp(TaskApp):

    def create_task(self):
        return SimpleTask(dispatch_on_main_thread=False,
                          run_in_thread=False)


if __name__ == '__main__':
    MainthreadTaskApp().run()
