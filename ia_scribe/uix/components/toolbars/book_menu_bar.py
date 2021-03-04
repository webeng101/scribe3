from os.path import dirname
from os.path import join

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

Builder.load_file(join(dirname(__file__), 'book_menu_bar.kv'))


class BookMenuBar(TooltipControl, BoxLayout):
    """Widget which displays book's identifier, title and menu options.

    :Events:
        `on_option_select`: option
            Dispatched when menu option is selected by releasing
            option's button. Options are: 'edit', 'reset', 'delete', 'export',
            'notes', 'upload', 'send_to_station', 'previous_foldout',
            'next_foldout', 'page_type'.

    .. note::

        If widget's layout is changed, method _update_children_width must be
        updated to enable proper scaling of child widgets.
    """

    identifier = StringProperty()
    title = StringProperty()
    current_marker_key = StringProperty()
    next_marker_key = StringProperty()
    use_foldout_buttons = BooleanProperty(True)
    downloaded_book = BooleanProperty(False)

    container = ObjectProperty()

    __events__ = ('on_option_select',)

    def __init__(self, **kwargs):
        self._temp_label = CoreLabel()
        self._trigger_children_update = \
            trigger = Clock.create_trigger(self._update_children_width)
        fbind = self.fbind
        fbind('width', trigger)
        fbind('identifier', trigger)
        fbind('title', trigger)
        fbind('use_foldout_buttons', trigger)
        super(BookMenuBar, self).__init__(**kwargs)
        trigger()

    def _update_children_width(self, *args):
        buttons, title_box, id_label = self.container.children
        if not buttons.width:
            self._trigger_children_update()
            return
        edit_button, title_label = title_box.children
        id_width = self._get_label_width(self.identifier, id_label)
        title_width = self._get_label_width(self.title, title_label)
        side_width = max(id_width, buttons.width)
        spacing = dp(26)
        bar_width = self.width
        temp_width = edit_button.width + 2 * spacing + title_box.spacing[0]
        if 2 * side_width + title_width + temp_width > bar_width:
            avail_title_width = bar_width - 2 * buttons.width - temp_width
            width = min(avail_title_width, title_width)
            title_label.width = width
            if title_width < avail_title_width:
                title_label.text_size = (None, None)
            else:
                title_label.text_size = title_label.size
            id_label.width = max(buttons.width,
                                 (bar_width - title_box.width) / 2.0 - spacing)
            id_label.text_size = id_label.size
        else:
            id_label.width = id_width
            id_label.text_size = (None, None)
            title_label.width = title_width
            title_label.text_size = (None, None)

    def _get_label_width(self, text, label):
        temp_label = self._temp_label
        temp_label.options['font_size'] = label.font_size
        temp_label.options['font_name'] = label.font_name
        temp_label.text = text
        temp_label.refresh()
        return temp_label.texture.width

    def on_option_select(self, option):
        pass
