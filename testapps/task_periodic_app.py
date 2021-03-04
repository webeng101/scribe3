import time

from ia_scribe.tasks.task_base import TaskBase
from testapps.task_base_app import TaskApp


class SimpleTask(TaskBase):

    def create_pipeline(self):
        return [self._step for _ in range(10)]

    def _step(self):
        time.sleep(1)
        self.dispatch_progress('Step %s' % (self._current_index + 1))


class BackgroundPeriodicTaskApp(TaskApp):

    def create_task(self):
        return SimpleTask(periodic=True, interval=5.0)


if __name__ == '__main__':
    BackgroundPeriodicTaskApp().run()
