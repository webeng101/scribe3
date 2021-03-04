from os.path import join, dirname

import regex as re
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    BooleanProperty,
    StringProperty,
    ObjectProperty,
    NumericProperty,
    ListProperty,
    OptionProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import SpinnerOption, Spinner
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput

from ia_scribe.uix.behaviors.form import FormBehavior
from ia_scribe.uix.behaviors.tooltip import TooltipBehavior

Builder.load_file(join(dirname(__file__), 'form_inputs.kv'))


class MetadataTextInput(TextInput):

    multiline = BooleanProperty(False)
    write_tab = BooleanProperty(False)
    metadata_key = StringProperty(None)
    key_input = ObjectProperty(None)

    def mark_as_error(self):
        self.background_color = (.5, 0, 0, .5)

    def mark_as_normal(self):
        self.background_color = (1, 1, 1, 1)

    def on_touch_down(self, touch):
        if super(MetadataTextInput, self).on_touch_down(touch):
            self.mark_as_normal()
            return True


class MetadataSwitch(Switch):

    metadata_key = StringProperty(None)


class RegexTextInput(MetadataTextInput):

    regex = StringProperty()
    is_valid = BooleanProperty(False)
    max_length = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._temp_text = ''
        if 'regex' in kwargs:
            self.regex = kwargs['regex']
        if 'max_length' in kwargs:
            self.max_length = kwargs['max_length']
        self._trigger_validate = Clock.create_trigger(self._validate)
        super(RegexTextInput, self).__init__(**kwargs)

    def on__lines(self, text_input, lines):
        text = self._get_text() if self.multiline else lines[0]
        if self._temp_text != text and not self._trigger_validate.is_triggered:
            self._temp_text = text
            self._trigger_validate()

    def _validate(self, *args):
        text = self._get_text() if self.multiline else self._lines[0]
        if len(text) == 0:
            self.background_color = (1, 1, 1, 1)
            return
        if self._temp_text != text:
            self._temp_text = text
            self._trigger_validate()
            return
        match = re.match(self.regex, text)
        if match:
            if self.max_length and len(text) != match.span()[1]:
                self.mark_as_error()
            else:
                self.background_color = (0, 1, 0, .2)
                self.is_valid = True
        else:
            self.is_valid = False
            if text != '':
                self.mark_as_error()

    def mark_as_error(self):
        self.background_color = (.5, 0, 0, .2)


class EmailTextInput(RegexTextInput):

    regex = '\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,6})+$'

class ScannerTextInput(RegexTextInput):
    regex = '[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.archive.org'

class KeyInput(TextInput):

    write_tab = BooleanProperty(False)

    def validate(self, instance):
        if not self.is_valid():
            label = Label(text="A custom metadata field's key is empty or contains illegal characters.\n\n"
                               "The first character must be a lower case ASCII letter\n"
                               "Lower case ASCII letters, digits, hyphens and underscores can follow.")
            popup = Popup(title='Custom Metadata Field Error', content=label,
                          size_hint=(None, None), size=(500, 200))
            popup.open()
            return False
        else:
            return True

    def is_valid(self):
        return re.match(r'^[a-z][a-z\d_-]*$', self.text) is not None


class NumberInput(TooltipBehavior, TextInput):
    '''Input which accepts number input, but prevent entering if number is not
    within `min_value` - `max_value` range. Use `value` to get latest value
    parsed from `text`.


    .. note::
        Values `min_value` and `max_value` are not validated and widget
        assumes that they are correct.
    '''

    value = NumericProperty(0, allownone=True)
    '''Value which is parsed when text is entered and widget de-focused. Value 
    can be set outside of class, but then it won't be validated until before 
    next frame is drawn.
    '''

    value_type = ObjectProperty(int)
    '''Callable which will be used to cast text to number.
    
    Defaults to `int`. 
    '''

    min_value = NumericProperty(-float('inf'))
    '''Minimum value allowed for `value` attribute.
    
    Defaults to `-float('inf')`.
    '''

    max_value = NumericProperty(float('inf'))
    '''Maximum value allowed for `value` attribute.

    Defaults to `float('inf')`.
    '''

    none_value_allowed = BooleanProperty(False)
    '''Allow `None` for attribute `value`. 
    
    Defaults to `False`.
    '''

    def __init__(self, **kwargs):
        self._valid_re = \
            re.compile(r'^(-?[1-9]+\.\d*|-?0\.\d*|-?[1-9]\d*|0|-)$')
        trigger = Clock.create_trigger(self._update_value_and_text, -1)
        fbind = self.fbind
        fbind('value', trigger)
        fbind('value_type', trigger)
        fbind('min_value', trigger)
        fbind('max_value', trigger)
        fbind('none_value_allowed', trigger)
        kwargs['text'] = self._value_to_string(self.value)
        super(NumberInput, self).__init__(**kwargs)

    def _update_value_and_text(self, *args):
        value = self.value
        if not self._is_valid_value(value):
            if value is None and not self.none_value_allowed:
                message = 'None is not allowed as value'
            else:
                message = ('Value {} is not within range [{}, {}]'
                           .format(value, self.min_value, self.max_value))
            raise ValueError(message)
        if value is not None:
            self.value = self.value_type(value)
        self.text = self._value_to_string(value)

    def _value_to_string(self, value):
        return '' if value is None else str(self.value_type(value))

    def _is_valid_text(self, text):
        if not (text and self._valid_re.match(text)):
            return False
        if text == '-':
            # Check if negative numbers are allowed
            return self.min_value < 0 or self.max_value < 0
        try:
            value = self.value_type(text)
        except ValueError:
            return False
        return self._is_valid_value(value)

    def _is_valid_value(self, value):
        if value is None:
            return self.none_value_allowed
        return self.min_value <= value <= self.max_value

    def insert_text(self, substring, from_undo=False):
        text, cursor_col = self.text, self.cursor_col
        new_text = text[:cursor_col] + substring + text[cursor_col:]
        if self._is_valid_text(new_text):
            return super(NumberInput, self).insert_text(substring, from_undo)

    def on_focus(self, number_input, focus):
        if focus:
            return
        text = self.text
        if text == '-' or not (text or self.none_value_allowed):
            self.text = self._value_to_string(self.value)
        elif self.none_value_allowed and not text:
            self.value = None
        else:
            self.value = value = self.value_type(text)
            self.text = str(value)
        self.cursor = [0, 0]


class SettingsSwitch(BoxLayout):

    label = StringProperty()
    metadata_key = StringProperty()

    __events__ = ('on_switch',)

    def _on_label(self, *args):
        self.ids.label.text = self.label

    def get_value(self):
        return self.ids.switch.active

    def set_value(self, value):
        value_type = type(value)
        if value_type == str:
            value = value == 'True'
        elif value_type != bool:
            value = False
        elif value_type == bool:
            pass
        else:
            raise ValueError('Invalid type {} of value {}'
                             .format(value_type, value))
        self.ids.switch.active = value

    def dispatch_on_switch(self, *args):
        self.dispatch('on_switch', *args)

    def on_switch(self, *args):
        pass


class SettingsInputBox(BoxLayout):

    label = StringProperty()
    metadata_key = StringProperty()
    focus_previous = ObjectProperty(None, allownone=True)
    focus_next = ObjectProperty(None, allownone=True)
    hint_text = StringProperty()
    description = StringProperty()

    def get_value(self):
        val = self.ids.text_input.text
        if val == '':
            val = None
        return val

    def set_value(self, value):
        if not value:
            value = ''
        self.ids.text_input.text = str(value)

    def set_validator(self, validator):
        self.ids.text_input.regex = validator

    def on_focus_next(self, *args):
        self._set_focus_next('focus_next')

    def on_focus_previous(self, *args):
        self._set_focus_next('focus_previous')

    def _set_focus_next(self, focus_direction):
        focus_next = getattr(self, focus_direction)
        if isinstance(focus_next, SettingsInputBox):
            setattr(self.ids.text_input,
                    focus_direction,
                    focus_next.ids.text_input)
        else:
            setattr(self.ids.text_input, focus_direction, focus_next)


class TooltipTextInput(TooltipBehavior, TextInput):

    def _reposition_tooltip_label(self, *args):
        label = self._tooltip_label
        x, top = self._to_label_parent(self.x, self.y, self)
        label.x = x
        if top - label.height < 0:
            top += self.height + label.height
        label.top = top


class ShortenSpinnerOption(SpinnerOption):
    pass


class SpinnerWithLabel(BoxLayout):
    orientation = StringProperty('vertical')
    label_text = StringProperty()
    spinner_text = StringProperty()
    spinner_values = ListProperty()


class LeftAlignedSpinner(Spinner):
    pass


class LeafNoteInput(FormBehavior, BoxLayout):

    default_note = StringProperty(None, allownone=True)
    note_input_displayed = BooleanProperty(False)
    note_input_target_height = NumericProperty('200dp')
    note_input_min_height = NumericProperty('200dp')
    anchor_edit_button = OptionProperty('left', options=['left', 'right'])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._defocus_trigger = \
            Clock.create_trigger(self._defocus_note_input, -1)

    def on_kv_post(self, base_widget):
        super(LeafNoteInput, self).on_kv_post(base_widget)
        self.ids.note_input.fbind('focus', self._defocus_trigger)

    def _defocus_note_input(self, *args):
        if not self.ids.note_input.focus:
            self.note_input_displayed = False
