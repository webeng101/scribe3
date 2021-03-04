import time

from ia_scribe.tasks.task_base import TaskBase, CANCELLED
from ia_scribe.uix.components.poppers.popups import NumberPopup
from testapps.task_base_app import TaskApp


class SimpleTask(TaskBase):

    def __init__(self, **kwargs):
        super(SimpleTask, self).__init__(**kwargs)
        self.user_input = None

    def create_pipeline(self):
        pipeline = [self._step for _ in range(5)]
        pipeline.append(self._user_request_step)
        pipeline.extend([self._step for _ in range(4)])
        return pipeline

    def _step(self):
        time.sleep(2)
        self.dispatch_progress('Step %s' % self._current_index)

    def _user_request_step(self):
        if not self.user_input:
            self.pause()
            # Flag progress report that user input is need for task to
            # continue. Keyword `input_needed` is arbitrary
            self.dispatch_progress('Step %s' % self._current_index,
                                   input_needed=True)
            self._stay_on_current_step = True
        else:
            self.dispatch_progress('Step %s: User input: %s'
                                   % (self._current_index, self.user_input))
            self._stay_on_current_step = False


class BackgroundTaskApp(TaskApp):

    def __init__(self, **kwargs):
        super(BackgroundTaskApp, self).__init__(**kwargs)
        self.title = 'Background task with user request'

    def create_task(self):
        return SimpleTask()

    def _on_task_progress(self, task, data):
        super(BackgroundTaskApp, self)._on_task_progress(task, data)
        if data.get('input_needed', False):
            popup = NumberPopup()
            popup.extra = {'task': task}
            popup.bind(on_submit=self._on_popup_submit)
            popup.open()

    def _on_popup_submit(self, popup, value):
        task = popup.extra['task']
        if task.state == CANCELLED:
            # In general, task can get cancelled by another UI
            return
        else:
            task.user_input = value
            task.resume()


if __name__ == '__main__':
    BackgroundTaskApp().run()
