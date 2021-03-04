from kivy.properties import ObjectProperty, NumericProperty, BooleanProperty, StringProperty

import os
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen


Builder.load_file(os.path.join(os.path.dirname(__file__), 'kv', 'base.kv'))


class BaseSection(Screen):

    root_widget = ObjectProperty(None)

    en_previous_button = BooleanProperty(True)
    en_next_button = BooleanProperty(True)

    def __init__(self, **kwargs):
        super(BaseSection, self).__init__(**kwargs)

    def on_enter(self, *args):
        super(BaseSection, self).on_enter(*args)
        self.root_widget.disable_btn('next', not self.en_next_button)
        self.root_widget.disable_btn('previous', not self.en_previous_button)

    def get_val(self, widget):
        if widget.__class__.__name__ in ['MetadataTextInput', 'EmailTextInput']:
            return widget.text
        return None

    def set_val(self, widget, val):
        if val is None:
            return
        if widget.__class__.__name__ in ['MetadataTextInput', 'EmailTextInput']:
            widget.text = val

    def before_next(self):
        """
        This function will be called before moving to the next screen
        :return: If True, screen will be move to the next screen, otherwise, it will stop moving.
        """
        return True

    def before_previous(self):
        """
        This function will be called before moving to the previous screen
        :return: If True, screen will be move to the previous screen, otherwise, it will stop moving.
        """
        return True
