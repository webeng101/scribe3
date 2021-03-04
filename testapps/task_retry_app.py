import time

from ia_scribe.tasks.task_base import TaskBase
from testapps.task_base_app import TaskApp


class SimpleTask(TaskBase):

    def create_pipeline(self):
        pipeline = [self._step for _ in range(5)]
        pipeline.append(self._error_step)
        pipeline.extend([self._step for _ in range(4)])
        return pipeline

    def _error_step(self):
        raise Exception('Error on step %s' % self._current_index)

    def _step(self):
        self.dispatch_progress('Step %s' % (self._current_index + 1))
        time.sleep(1)


class RetryTaskApp(TaskApp):

    def create_task(self):
        return SimpleTask(retry_on_error=True, retry_interval=10.0)


if __name__ == '__main__':
    RetryTaskApp().run()
