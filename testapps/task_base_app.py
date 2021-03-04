import ia_scribe # noqa

from kivy.app import App
from kivy.lang import Builder

from ia_scribe.tasks.task_scheduler import TaskScheduler

kv = '''
BoxLayout:
    orientation: 'vertical'
    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
    size_hint: (0.6, None)
    height: self.minimum_height
    Label:
        id: label
        size_hint_y: None
        height: '50dp'
        font_size: '20sp'
    ProgressBar:
        id: bar
        max: 1.0
        size_hint_y: None
        height: '40dp'
    BoxLayout:
        id: buttons
        size_hint_y: None
        height: '50dp'
        spacing: '5dp'
        ColorButton:
            text: 'Pause'
            on_release: app._task_pause_or_resume(self)
        ColorButton:
            text: 'Cancel'
            on_release: app._task_cancel(self)
'''


class TaskApp(App):

    def __init__(self, **kwargs):
        super(TaskApp, self).__init__(**kwargs)
        self.scheduler = TaskScheduler()
        self.task = self.create_task()
        self.task.fbind('on_progress', self._on_task_progress)
        self.task.fbind('on_end', self._on_task_end)

    def create_task(self):
        raise NotImplementedError()

    def build(self):
        return Builder.load_string(kv)

    def on_start(self):
        super(TaskApp, self).on_start()
        self.scheduler.start()
        self.scheduler.schedule(self.task)

    def _task_pause_or_resume(self, button):
        if button.text == 'Pause':
            if self.task.pause():
                button.text = 'Resume'
        elif button.text == 'Resume':
            if self.task.resume():
                button.text = 'Pause'

    def _task_cancel(self, button):
        self.task.cancel()
        self.root.ids.buttons.disabled = True

    def _on_task_progress(self, task, data):
        text = u'{:.0f}% {}'.format(data['progress'] * 100, data['message'])
        self.root.ids.label.text = text
        self.root.ids.bar.value = data['progress']

    def _on_task_end(self, task):
        self.root.ids.buttons.disabled = True

    def on_stop(self):
        super(TaskApp, self).on_stop()
        self.task.cancel()
