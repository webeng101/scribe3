from functools import partial
from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (StringProperty,
                             DictProperty,
                             ObjectProperty)
from kivy.uix.boxlayout import BoxLayout

from kivy.uix.popup import Popup

from ia_scribe.uix_backends.catalogs_backend import CatalogsBackend
from ia_scribe.uix_backends.marc_search_backend import MARCSearchBackend
from ia_scribe.uix.widgets.marc.config import CONTEXTS

Builder.load_file(join(dirname(__file__), 'MARC.kv'))


class MARCPopup(Popup):

    EVENT_RECORD_SELECTED = 'on_record_selected'

    __events__ = (EVENT_RECORD_SELECTED, )

    def __init__(self, **kwargs):
        super(MARCPopup, self).__init__(**kwargs)
        self.content = MARCWidget()
        self.title = 'Marc search tool'
        self.content.bind(on_button_closed_pressed=self.close)
        self.content.bind(on_record_selected=self.record_selected)

    def close(self, *args):
        self.dismiss()

    def record_selected(self, widget, query, data):
        self.dispatch(self.EVENT_RECORD_SELECTED, query, data)

    def on_record_selected(self, *args):
        pass


class MARCWidget(BoxLayout):

    catalogs_backend = ObjectProperty()
    search_backend = ObjectProperty()
    contexts = DictProperty()
    home_button_text = StringProperty('Hidden')
    action_button_1_text = StringProperty('Hidden')
    action_button_2_text = StringProperty('Disabled')
    action_buttons = DictProperty(
        {
            1: {
                'text': 'Disabled',
                'on_release': None,
                'text_property': 'action_button_1_text',
        },
            2: {
                'text': 'Disabled',
                'on_release': None,
                'text_property': 'action_button_2_text',
            },
        }

    )

    EVENT_BUTTON_HOME_PRESSED = 'on_button_home_pressed'
    EVENT_BUTTON_CLOSED_PRESSED = 'on_button_closed_pressed'
    EVENT_BUTTON_ACTION_1_PRESSED = 'on_button_action_1_pressed'
    EVENT_BUTTON_ACTION_2_PRESSED = 'on_button_action_2_pressed'
    EVENT_RECORD_SELECTED = 'on_record_selected'

    active_widget = ObjectProperty()

    __events__ = (EVENT_BUTTON_CLOSED_PRESSED,
                  EVENT_BUTTON_HOME_PRESSED,
                  EVENT_BUTTON_ACTION_1_PRESSED,
                  EVENT_BUTTON_ACTION_2_PRESSED,
                  EVENT_RECORD_SELECTED
                  )

    def __init__(self, **kwargs):
        super(MARCWidget, self).__init__(**kwargs)
        self.catalogs_backend = CatalogsBackend()
        self.search_backend = MARCSearchBackend()
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self.load_all_contexts()
        self.set_context(self.get_home_context())

    def get_home_context(self):
        home_context = [x for x, y in CONTEXTS.items() if y.get('home')][0]
        return home_context

    def load_all_contexts(self):
        for context_name in CONTEXTS:
            self.contexts[context_name] = self.load_context(context_name)

    def load_context(self, context):
        context = CONTEXTS[context]

        # Instantiate widget
        widget = context['widget']()

        if 'properties' in context:
            for property_source, property_target in context.get('properties').items():
                self_property = getattr(self, property_source)
                setattr(widget, property_target, self_property)

        # Set bindings
        if 'bindings' in context:
            for event, binding in context.get('bindings').items():
                widget_event = getattr(widget, event)
                func = getattr(self, binding[0])
                dispatch_function = partial(func, *binding[1:])
                widget.fbind(widget_event, dispatch_function)

        if hasattr(widget, 'postponed_init'):
            widget.postponed_init()
        return widget

    def set_context(self, context, *args, **kwargs):
        context_metadata = CONTEXTS[context]
        # Set widget
        widget = self.contexts[context]

        # Set home buttons
        if context_metadata.get('home'):
            self.home_button_text = 'Hidden'
        else:
            self.home_button_text = 'Back to {}'.format(self.get_home_context())

        # Set actionbuttons
        if 'action_buttons' in context_metadata:
            for button_number, button_config in context_metadata.get('action_buttons').items():
                self.set_action_button(button_number,
                                       widget,
                                       button_config.get('function', None),
                                       button_config.get('text', 'Hidden'))

        # Set context bar title
        self.ids.context_text.text = context_metadata['title']
        # Attach widget
        self.active_widget = widget

    def set_action_button(self, number, widget, function_name, default_string):
        if function_name:
            func = getattr(widget, function_name)
            self.action_buttons[number]['on_release'] = func
        setattr(self, self.action_buttons[number]['text_property'], default_string)

    def on_active_widget(self, source, target):
        self.ids.content_canvas.clear_widgets()
        self.ids.content_canvas.add_widget(target)

    def on_button_closed_pressed(self, *args):
        pass

    def on_button_home_pressed(self, *args):
        self.set_context(self.get_home_context())

    def on_button_action_1_pressed(self, *args, **kwargs):
        if self.action_buttons[1]['on_release']:
            res = self.action_buttons[1]['on_release']()
            if res:
                setattr(self, self.action_buttons[1]['text_property'], res)

    def on_button_action_2_pressed(self):
        if self.action_buttons[2]['on_release']:
            res = self.action_buttons[2]['on_release']()
            if res:
                setattr(self, self.action_buttons[2]['text_property'], res)

    def change_title_callback(self, text):
        self.ids.context_text.text = text

    def on_record_selected(self, *args):
        pass

    def receive_upstream_event_selected(self, widget, query, data):
        self.dispatch(self.EVENT_RECORD_SELECTED, query, data)