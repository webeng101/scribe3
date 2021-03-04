import os

from kivy.lang import Builder
from kivy.properties import ObjectProperty
from ia_scribe.uix.screens.wizard.sections.base import BaseSection

Builder.load_file(os.path.join(os.path.dirname(__file__), 'kv', 'welcome.kv'))


class WelcomeSection(BaseSection):
    task_scheduler = ObjectProperty()
    en_previous_button = False

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.pop('task_scheduler')
        super(WelcomeSection, self).__init__(**kwargs)

    def on_enter(self):
        super(WelcomeSection, self).on_enter()

    def before_next(self):
        self.start_scheduler()
        return True

    def start_scheduler(self):
        self.task_scheduler.cancel_all()
        self.task_scheduler.start()
