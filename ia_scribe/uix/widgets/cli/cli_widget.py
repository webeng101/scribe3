from os.path import join, dirname
from pprint import pformat
from functools import partial

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    StringProperty,
    NumericProperty,
    ObjectProperty,
    BooleanProperty,
    ListProperty,
)
from kivy.uix.popup import Popup

from cli.cli import evaluate, tokenize, lex


Builder.load_file(join(dirname(__file__), 'cli_widget.kv'))

class CLIWidgetPopup(Popup):
    screen_manager = ObjectProperty(allownone=True)

    def __init__(self, **kwargs):
        super(CLIWidgetPopup, self).__init__(**kwargs)
        self.content = CLIWidget()
        self.title = 'Scribe3 Command Line Interface'
        self.screen_manager = kwargs.get('screen_manager')

    def disable_screen_actions_if_bound(self):
        if not self.screen_manager:
            return
        if self.screen_manager.current == 'rescribe_screen':
            self.screen_manager.get_screen('rescribe_screen').disable_keyboard_actions()
        elif self.screen_manager.current == 'capture_screen':
            self.screen_manager.get_screen('capture_screen').disable_capture_actions()

    def enable_screen_actions_if_bound(self):
        if not self.screen_manager:
            return
        if self.screen_manager.current == 'rescribe_screen':
            self.screen_manager.get_screen('rescribe_screen').enable_keyboard_actions()
        elif self.screen_manager.current == 'capture_screen':
            self.screen_manager.get_screen('capture_screen').enable_capture_actions()

    def on_open(self, *args):
        self.disable_screen_actions_if_bound()
        self.content.bind_to_keyboard_actions()

    def on_dismiss(self, *args):
        self.content.unbind_to_keyboard_actions()
        self.enable_screen_actions_if_bound()

class CLIWidget(BoxLayout):
    log = StringProperty('')
    commands_history = ListProperty()
    commands_history_cursor = NumericProperty(0)


    def __init__(self, **kwargs):
        super(CLIWidget, self).__init__(**kwargs)
        self.ids.command_box.bind(on_text_validate=self.issue_command)
        self.ids.command_box.focus = True

    def bind_to_keyboard_actions(self, *args):
        Window.fbind('on_key_down', self.on_key_down)
        Window.fbind('on_key_up', self.on_key_up)

    def unbind_to_keyboard_actions(self, *args):
        Window.funbind('on_key_down', self.on_key_down)
        Window.funbind('on_key_up', self.on_key_up)

    def issue_command(self, text_input):
        try:
            expression = text_input.text
            self.commands_history.append(expression)
            tokens = tokenize(expression)
            command, args = lex(tokens)
            if command:
                result = evaluate(command, args)
            else:
                result = args
        except Exception as e:
            result = str(e)
        res = '{} -> {}\n'.format(expression, pformat(result))
        self.print_message(res)
        self.ids.command_box.text = ''

    def print_message(self, msg):
        self.log += "{}\n".format(msg)

    def set_focus(self, *args, **kwargs):
        self.ids.command_box.focus = True

    def on_log(self, *args, **kwargs):
        Clock.schedule_once(self.set_focus)

    def on_commands_history(self, *args):
        if len(self.commands_history) == 0:
            self.commands_history_cursor = 0
            return
        self.commands_history_cursor = len(self.commands_history)

    def on_key_down(self, window, keycode, scancode, codepoint=None,
                    modifiers=None, **kwargs):
        if scancode == 81:
            self.ids.command_box.text = self.get_next_command()
        elif scancode == 82:
            self.ids.command_box.text = self.get_previous_command()
        elif scancode == 43:
            # This is the TAB button. May want to plug in autocomplete here
            pass

    def get_previous_command(self):
        if len(self.commands_history) == 0:
            return ''
        if self.commands_history_cursor == 0:
            return self.get_history_by_index()
        self.commands_history_cursor -= 1
        return self.get_history_by_index()

    def get_next_command(self):
        if len(self.commands_history) == 0:
            return ''
        if self.commands_history_cursor >= len(self.commands_history):
            return ''
        self.commands_history_cursor += 1
        return self.get_history_by_index()

    def get_history_by_index(self):
        reverse_history = self.commands_history
        if self.commands_history_cursor >= len(self.commands_history):
            return ''

        return self.commands_history[self.commands_history_cursor] or ' '

    def on_key_up(self, window, keycode, scancode, codepoint=None,
                  modifiers=None, **kwargs):
        pass

    def do_scroll(self, text_input, *args):
        text_input.cursor = (text_input.cursor_col, len(text_input._lines) - 1)

    def _on_text(self, text_input):
        function = partial(self.do_scroll, text_input)
        Clock.schedule_once(function)

