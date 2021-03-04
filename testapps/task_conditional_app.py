import time

from ia_scribe.tasks.task_base import TaskBase
from testapps.task_base_app import TaskApp


class SimpleSubTask(TaskBase):

    def create_pipeline(self):
        return [self._step, self._step_with_error, self._step]

    def _step(self):
        self.dispatch_progress('Step %s' % (self._current_index + 1))
        time.sleep(1)

    def _step_with_error(self):
        self.dispatch_progress('Step %s; Raising an error'
                               % (self._current_index + 1))
        time.sleep(1)
        raise Exception('Step raising an error')


class SimpleTask(TaskBase):

    def create_pipeline(self):
        pipeline = [self._step for _ in range(5)]
        pipeline.append(SimpleSubTask())
        pipeline.extend(self._step for _ in range(6))
        return pipeline

    def _handle_sub_task_error(self, sub_task, index, error):
        # Jump to index + 2
        self._target_index = index + 2
        return True

    def _step(self):
        self.dispatch_progress('Step %s' % (self._current_index + 1))
        time.sleep(1)


class BackgroundConditionalTaskApp(TaskApp):

    def create_task(self):
        return SimpleTask()


if __name__ == '__main__':
    BackgroundConditionalTaskApp().run()
