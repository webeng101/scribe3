import time

from ia_scribe.tasks.task_base import TaskBase
from testapps.task_base_app import TaskApp


class SimpleSubTask(TaskBase):

    def create_pipeline(self):
        return [self._step for _ in range(10)]

    def _step(self):
        time.sleep(1)
        self.dispatch_progress('Step %s' % (self._current_index + 1))


class SimpleTask(TaskBase):

    def create_pipeline(self):
        return [
            self._step,
            SimpleSubTask(),
            SimpleSubTask(),
            self._step
        ]

    def _step(self):
        time.sleep(1)
        self.dispatch_progress('Step %s' % (self._current_index + 1))


class BackgroundTaskApp(TaskApp):

    def create_task(self):
        return SimpleTask()


if __name__ == '__main__':
    BackgroundTaskApp().run()
