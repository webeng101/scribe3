import os

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.uix.screenmanager import Screen, SlideTransition, NoTransition

from ia_scribe.uix.screens.wizard.sections.login import LoginSection
from ia_scribe.uix.screens.wizard.sections.metadata_collection import \
    MetadataCollectionSection
from ia_scribe.uix.screens.wizard.sections.metadata import MetadataSection
from ia_scribe.uix.screens.wizard.sections.welcome import WelcomeSection

Builder.load_file(os.path.join(os.path.dirname(__file__), 'wizard.kv'))


class WizardScreen(Screen):
    index = NumericProperty(0)
    sections = ListProperty()
    scribe_widget = ObjectProperty()

    def __init__(self, **kwargs):
        super(WizardScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self.sections = [WelcomeSection(root_widget=self,
                                        task_scheduler=self.scribe_widget.task_scheduler),
                         LoginSection(root_widget=self,
                                      task_scheduler=self.scribe_widget.task_scheduler),
                         MetadataSection(root_widget=self),
                         MetadataCollectionSection(root_widget=self)]
        Clock.schedule_once(self.show_welcome)

    def show_welcome(self, *args):
        self.ids.sm.transition = NoTransition()
        self.ids.sm.switch_to(self.sections[0])

    def disable_btn(self, _id, val):
        self.ids['btn_{}'.format(_id)].disabled = val

    def go_next(self):
        """
        Move to the next section
        :return:
        """
        if not self.sections[self.index].before_next():
            return
        if self.index < len(self.sections) - 1:
            self.index += 1
            self.ids.sm.transition = SlideTransition()
            self.ids.sm.switch_to(self.sections[self.index], direction='left')
            self.check_next_btn_label()

    def check_next_btn_label(self):
        if self.index == len(self.sections) - 1:
            self.ids.btn_next.text = 'Finish and Restart'
        else:
            self.ids.btn_next.text = 'Next'

    def go_previous(self):
        """
        Move to the next section
        :return:
        """
        if not self.sections[self.index].before_previous():
            return
        if self.index > 0:
            self.index -= 1
            self.ids.sm.transition = SlideTransition()
            self.ids.sm.switch_to(self.sections[self.index], direction='right')
            self.check_next_btn_label()
