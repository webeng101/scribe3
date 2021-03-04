import time
from random import randint

from kivy.app import App

from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.task_scheduler import TaskScheduler
from ia_scribe.uix.widgets.taskman.task_manager import TaskManager


class SimpleTask(TaskBase):

    def create_pipeline(self):
        return [self._step for _ in range(randint(10, 20))]

    def _step(self):
        self.dispatch_progress('Step %s' % self._current_index)
        time.sleep(1)


class TaskManagerApp(App):

    def build(self):
        root = TaskManager(pos_hint={'x': 0.0, 'center_y': 0.5},
                           size_hint=(1.0, 1.0))
        return root

    def on_start(self):
        super(TaskManagerApp, self).on_start()
        self.root_window.size = (1000, 600)
        self.scheduler = TaskScheduler()
        self.scheduler.start()
        for task in self.create_dummy_tasks():
            self.scheduler.schedule(task)
        self.root.attach_scheduler(self.scheduler)

    def on_stop(self):
        self.scheduler.stop()

    def create_dummy_tasks(self):
        out = []
        for index in range(1, 16):
            task = SimpleTask(name='Task%s' % index,
                              periodic=index in {1, 2},
                              interval=5)
            out.append(task)
        return out


if __name__ == '__main__':
    TaskManagerApp().run()
