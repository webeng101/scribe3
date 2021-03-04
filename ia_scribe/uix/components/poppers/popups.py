# import timeago
import itertools
import webbrowser
from os.path import join, dirname

import regex
from isbnlib import notisbn
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    ObjectProperty,
    StringProperty,
    OptionProperty,
    BooleanProperty,
    ListProperty,
    NumericProperty,
    VariableListProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as rgb

from ia_scribe.book.metadata import (
    MD_CUSTOM_KEY_OPTIONS,
    MD_ACRONYMS,
    is_valid_issn
)
from ia_scribe.book.scandata import VALID_PAGE_TYPES
from ia_scribe.libraries.graph import Graph, BarPlot
from ia_scribe.uix.behaviors.form import FormBehavior
from ia_scribe.uix.components.buttons.buttons import ColorToggleButton, \
    RadioButton
from ia_scribe.uix.components.labels.labels import Label
from ia_scribe.uix.components.overlay.overlay_view import OverlayView

Builder.load_file(join(dirname(__file__), 'popups.kv'))


class FormPopup(FormBehavior, Popup):

    extra = ObjectProperty(allownone=True)

    def __init__(self, **kwargs):
        super(FormPopup, self).__init__(**kwargs)

    def collect_data(self):
        return None

    def submit_data(self, data=None):
        super(FormPopup, self).submit_data(data)
        if self.auto_dismiss:
            self.dismiss()


class EditPPIPopup(FormPopup):

    default_ppi = NumericProperty(300)

    def on_open(self):
        super(EditPPIPopup, self).on_open()
        ppi_input = self.ids.ppi_input
        ppi_input.do_cursor_movement('cursor_end')
        ppi_input.focus = True
        ppi_input.select_all()


class NumberPopup(FormPopup):

    value = NumericProperty(allownone=True)

    def on_open(self):
        super(NumberPopup, self).on_open()
        ppi_input = self.ids.ppi_input
        ppi_input.do_cursor_movement('cursor_end')
        ppi_input.focus = True
        ppi_input.select_all()


class InputPopup(FormPopup):

    title = StringProperty('Input')
    message = StringProperty('Insert desired value below')
    input_value = StringProperty()
    text_ok = StringProperty('OK')


class BookNotesPopup(FormPopup):

    notes = StringProperty()


class RuntimeErrorPopup(FormPopup):

    OPTION_EXIT = 'exit'
    OPTION_RESTART = 'restart'

    def submit_data(self, data=None):
        new_data = {'option': data, 'message': self.ids.text_input.text}
        super(RuntimeErrorPopup, self).submit_data(new_data)


class PageTypeFormPopup(FormPopup):

    default_page_number = NumericProperty(None, allownone=True)
    default_page_type = StringProperty('Normal')

    target_widget = ObjectProperty(None, allownone=True, baseclass=Widget)
    target_anchor_x = OptionProperty('center',
                                     options=['left', 'center', 'right'])
    target_padding_x = NumericProperty('6dp')
    page_number_input_disabled = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._selected_page_type = None
        super(PageTypeFormPopup, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init)

    def _postponed_init(self, *args):
        container = self.ids.buttons_container
        group = '{}|{}'.format(self.__class__.__name__, hash(self))
        sorted_page_types = sorted(VALID_PAGE_TYPES, reverse=True)
        normal_page_index = sorted_page_types.index('Normal')
        normal = sorted_page_types.pop(normal_page_index)
        sorted_page_types.append(normal)
        size_hint = (0.5, None)
        color_normal = (40.0/255, 40.0/255, 40.0/255, 1.0)
        for page_type in reversed(sorted_page_types):
            button = ColorToggleButton(
                text=page_type, group=group,
                size_hint=size_hint, height='40dp',
                allow_no_selection=False,
                color_normal=color_normal
            )
            button.fbind('state', self._on_page_type_button_state)
            container.add_widget(button)

    def _on_page_type_button_state(self, button, state):
        self._selected_page_type = button.text

    def _align_center(self, *l):
        target_widget = self.target_widget
        if target_widget:
            tx, ty = target_widget.to_window(target_widget.x, target_widget.y)
            if self.target_anchor_x == 'left':
                self.x = tx - self.target_padding_x
            elif self.target_anchor_x == 'right':
                self.right = tx + self.target_padding_x + target_widget.width
            else:
                self.center_x = tx + target_widget.width / 2.0
            self.y = ty - self.height
        else:
            self.center = self._window.center

    def open(self, *largs):
        # Select the button that corresponds to the active PageType
        for button in self.ids.buttons_container.children:
            if button.text == self.default_page_type:
                button._do_press()
                break
        # Populate the page_number field if asserted,
        # make blank otherwise (without this, the previous value will stick)
        self.ids.page_number_input.value   = self.default_page_number
        target_widget = self.target_widget
        if target_widget:
            target_widget.bind(center=self._align_center)
        super(PageTypeFormPopup, self).open(*largs)
        self._align_center()

    def _real_remove_widget(self):
        super(PageTypeFormPopup, self)._real_remove_widget()
        target_widget = self.target_widget
        if target_widget:
            target_widget.unbind(center=self._align_center)

    def collect_data(self):
        return {
            'page_type': self._selected_page_type,
            'page_number': self.ids.page_number_input.value
        }

    def _handle_keyboard(self, window, key, *largs):
        if key == 13 or key == 32:
            self.submit_data()
            return True
        return super(PageTypeFormPopup, self)._handle_keyboard(window, key, *largs)

class CaptureFailurePopup(FormPopup):

    OPTION_RETRY_CAPTURE = 'retry_capture'
    OPTION_GOTO_CALIBRATION = 'goto_calibration'

    message = StringProperty()


class CalibrateCamerasPopup(FormPopup):

    OPTION_GOTO_CALIBRATION = 'goto_calibration'
    OPTION_CONTINUE = 'continue'


class QuestionPopup(FormPopup):

    OPTION_YES = 'yes'
    OPTION_NO = 'no'

    message = StringProperty()
    message_halign = OptionProperty(
        'center', options=['left', 'center', 'right', 'justify']
    )
    message_padding_x = NumericProperty()
    text_yes = StringProperty('Yes')
    text_no = StringProperty('No')

    def set_option_attrs(self, option, **kwargs):
        button = None
        if option == self.OPTION_YES:
            button = self.ids.yes_button
        elif option == self.OPTION_NO:
            button = self.ids.no_button
        if button:
            for key, value in kwargs.items():
                setattr(button, key, value)

    def _handle_keyboard(self, window, key, *largs):
        if key == 13 or key == 32:
            # Keys "enter" and "spacebar" are used to confirm
            # Key "esc" will dismiss popup by default
            self.submit_data(self.OPTION_YES)
            return True
        return super(QuestionPopup, self)._handle_keyboard(window, key, *largs)


class ThreeOptionsQuestionPopup(Popup):

    OPTION_YES = 'yes'
    OPTION_NO = 'no'
    OPTION_ELSE = 'else'

    message = StringProperty()
    text_yes = StringProperty('Yes')
    text_no = StringProperty('No')
    text_else = StringProperty('Else')
    extra = ObjectProperty(allownone=True)

    __events__ = ('on_submit',)

    def set_option_attrs(self, option, **kwargs):
        button = None
        if option == self.OPTION_YES:
            button = self.ids.yes_button
        elif option == self.OPTION_NO:
            button = self.ids.no_button
        elif option == self.OPTION_ELSE:
            button = self.ids.else_button
        if button:
            for key, value in kwargs.items():
                setattr(button, key, value)

    def submit_data(self, option):
        self.dispatch('on_submit', option)
        if self.auto_dismiss:
            self.dismiss()

    def on_submit(self, option):
        pass

class CheckBoxPopup(FormPopup):
    active = BooleanProperty(False)
    allow_no_selection = BooleanProperty(True)
    checkbox_text = StringProperty()
    text_color = ListProperty([1, 1, 1, 1])
    OPTION_YES = 'Yes'
    OPTION_NO = 'No'

    message = StringProperty()
    message_halign = OptionProperty(
        'center', options=['left', 'center', 'right', 'justify']
    )
    message_padding_x = NumericProperty()
    text_yes = StringProperty('Yes')
    text_no = StringProperty('No')

    def set_option_attrs(self, option, **kwargs):
        button = None
        if option == self.OPTION_YES:
            button = self.ids.yes_button
        elif option == self.OPTION_NO:
            button = self.ids.no_button
        if button:
            for key, value in kwargs.items():
                setattr(button, key, value)

    def _handle_keyboard(self, window, key, *largs):
        if key == 13 or key == 32:
            # Keys "enter" and "spacebar" are used to confirm
            # Key "esc" will dismiss popup by default
            self.submit_data(self.OPTION_YES)
            return True
        return super(CheckBoxPopup, self)._handle_keyboard(window, key, *largs)

class InfoPopup(FormPopup):

    OPTION_OK = 'ok'

    message = StringProperty()
    text_ok = StringProperty('Ok')

    def _handle_keyboard(self, window, key, *largs):
        if key == 13 or key == 32:
            # Keys "enter" and "spacebar" are used to confirm
            # Key "esc" will dismiss popup by default
            self.submit_data(self.OPTION_OK)
            return True
        return super(InfoPopup, self)._handle_keyboard(window, key, *largs)


class DeleteSpreadPopup(QuestionPopup):
    pass


class ScribeLearnMorePopup(QuestionPopup):

    LINK = ('https://internetarchivebooks.zendesk.com/hc/en-us/articles/'
            '204584071-Calibrating-your-cameras-after-a-hard-reset')
    INSTRUCTIONS = ('1. Check focus and white balance.\n\n'
                    '2. Recalibrate if necessary, then click "Reshoot".\n\n'
                    '3. If pages are upside down, click "Flip".\n\n'
                    '4. If everything above is correct, click "Done".')

    def on_submit(self, option):
        super(ScribeLearnMorePopup, self).on_submit(option)
        if option == self.OPTION_YES:
            webbrowser.open(self.LINK)


class FoldoutsModePopup(FormPopup):

    OPTION_CAPTURE = 'capture'
    OPTION_UPLOAD = 'upload'
    OPTION_CANCEL = 'cancel'
    OPTION_DELETE = 'delete'

    message = StringProperty()
    upload_disabled = BooleanProperty(True)


class ReshootInsertSpreadPopup(FormPopup):

    OPTION_RESHOOT = 'reshoot'
    OPTION_INSERT = 'insert'
    OPTION_CANCEL = 'cancel'

    message = StringProperty()


class NewMetadataFieldPopup(FormPopup):

    background_color = ListProperty([0, 0, 0, 0, 0])
    _anim_duration = NumericProperty(0)
    target_widget = ObjectProperty(None, allownone=True, baseclass=Widget)

    keys = ObjectProperty(MD_CUSTOM_KEY_OPTIONS, baseclass=list)
    skip_keys = ObjectProperty(set(), baseclass=set)
    _re_key = regex.compile(r'[a-z]+[a-z\-]*')
    _invalid_key_message = 'Valid key should consist of lowercase letters'

    def _create_spinner_values(self):
        out = []
        for key in self.keys:
            if key not in self.skip_keys:
                if key in MD_ACRONYMS:
                    out.append(key.upper())
                else:
                    out.append(key.capitalize())
        return out

    def _align_center(self, *l):
        target_widget = self.target_widget
        if target_widget:
            self.center = target_widget.to_window(*target_widget.center)
            self.width = target_widget.width * 0.95
        else:
            self.center = self._window.center
            self.width = '500dp'

    def open(self, *largs):
        self.reset()
        if self.target_widget:
            self.target_widget.bind(center=self._align_center)
        super(NewMetadataFieldPopup, self).open(*largs)
        self._align_center()

    def _real_remove_widget(self):
        super(NewMetadataFieldPopup, self)._real_remove_widget()
        if self.target_widget:
            self.target_widget.unbind(center=self._align_center)

    def _on_key_spinner_value(self, spinner, value):
        self._reset_message_labels()

    def reset(self):
        self.ids.key_spinner.values = values = self._create_spinner_values()
        self.ids.key_spinner.text = values[0] if values else ''
        self.ids.value_input.text = ''
        self.ids.key_input.text = ''
        self._reset_message_labels()

    def _reset_message_labels(self):
        self.ids.key_message_label.text = ''
        self.ids.value_message_label.text = ''

    def collect_data(self):
        key = self.ids.key_spinner.text
        if key == 'Custom':
            key = self.ids.key_input.text
        return {
            'key': key.lower().strip(),
            'value': self.ids.value_input.text.strip()
        }

    def submit_data(self, data=None):
        data = self.collect_data()
        if self._validate(data):
            super(NewMetadataFieldPopup, self).submit_data(data)

    def _validate(self, data):
        valid = True
        self._reset_message_labels()
        if self._re_key.match(data['key']):
            self.ids.key_message_label.text = ''
        else:
            valid = False
            self.ids.key_message_label.text = self._invalid_key_message
        if valid and data['key'] in self.skip_keys:
            self.ids.key_message_label.text = 'Cannot use this key'
            valid = False
        if self._is_valid_value(data):
            self.ids.value_message_label.text = ''
        else:
            valid = False
            self.ids.value_message_label.text = 'Invalid value'
        return valid

    def _is_valid_value(self, data):
        value = data['value']
        if not value:
            return False
        key = data['key']
        if key == 'isbn':
            return not notisbn(value)
        if key == 'issn':
            return is_valid_issn(value)
        if key == 'page-progression':
            return value in ['lr', 'rl']
        return True


class UniversalIDPopup(FormPopup):

    identifiers = ObjectProperty([], baseclass=list)

    def __init__(self, **kwargs):
        trigger_update_identifiers_list = \
            Clock.create_trigger(self._update_identifiers_list, -1)
        self.fbind('identifiers', trigger_update_identifiers_list)
        super(UniversalIDPopup, self).__init__(**kwargs)

    def _update_identifiers_list(self, *args):
        self.ids.rv.data = ({'identifier': x} for x in self.identifiers)

    def collect_data(self):
        rv = self.ids.rv
        selected = rv.layout_manager.selected_nodes
        if selected:
            return rv.data[selected[0]]['identifier']
        return None

    def reset(self):
        rv = self.ids.rv
        rv.layout_manager.clear_selection()

    def open(self, *largs):
        self.reset()
        return super(UniversalIDPopup, self).open(*largs)


class ProgressPopup(Popup):

    message = StringProperty()
    progress = NumericProperty()


class BookMetadataPopup(OverlayView):

    book_path = StringProperty()
    md_panel = ObjectProperty()

    def open(self, *largs):
        super(BookMetadataPopup, self).open(*largs)
        if self._window:
            self.md_panel.backend.book_path = self.book_path
            self.md_panel.backend.init()

    def on_dismiss(self):
        super(BookMetadataPopup, self).on_dismiss()
        if self._window:
            self.md_panel.backend.reset()

    def on_md_panel(self, popup, md_panel):
        md_panel.fbind('on_cancel', self.dismiss)
        md_panel.fbind('on_done', self.dismiss)


class RejectBookPopup(FormPopup):
    message = StringProperty()

    def show_error(self, message):
        popup = InfoPopup(title='Rejection error',
                          message=message)
        popup.open()

    def submit_data(self, data=None):
        data = self.collect_data()
        if not data['error']:
            super(RejectBookPopup, self).submit_data(data)
        else:
            self.show_error(data['error'])

    def collect_data(self):
        ret = {'reason': None, 'comment': None, 'error': None}

        # look at buttons in root level
        for button in self.ids.options_container.children:
            if isinstance(button, RadioButton) and button.active:
                ret['reason'] = button.text

        # if no button is selected, either "other" or none is selected
        if not ret['reason']:
            ret['error'] = 'No rejection reason selected'

        # finally add the optional comment section
        ret['comment'] = self.ids.comments_input.text

        return ret


class LogBox(BoxLayout):
    log = StringProperty()

    def __init__(self, log, **kwargs):
        self.log = log
        super(LogBox, self).__init__(**kwargs)


class StatGraphPanel(BoxLayout):
    message = StringProperty()
    message_cursive = StringProperty()
    xmax = NumericProperty(100)
    xmin = NumericProperty(0)
    ymax = NumericProperty(100)
    ymin = NumericProperty(0)
    xlabel = StringProperty('x axis')
    ylabel = StringProperty('y axis')
    points = ListProperty([])
    data = ListProperty()

    def __init__(self, **kwargs):
        super(StatGraphPanel, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args,  **kwargs):
        self.populate_table()
        self.render_graph()

    def populate_table(self):
        for entry in self.data:
            row = BoxLayout(orientation='horizontal')
            for value in entry:
                l = Label(text=str(value), border= [1, 1,1,1])
                row.add_widget(l)
            self.ids['table'].add_widget(row)

    def render_graph(self):
        colors = itertools.cycle([
            rgb('7dac9f'), rgb('dc7062'), rgb('66a8d4'), rgb('e5b060')])
        graph_theme = {
            'label_options': {
                'color': rgb('444444'),  # color of tick labels and titles
                'bold': True},
            'background_color': [0,0, 0, 0.2],  # back ground color of canvas
            'tick_color': rgb('808080'),  # ticks and grid
            'border_color': rgb('808080')}  # border drawn around each graph

        graph = Graph(
            xlabel=self.xlabel,
            ylabel=self.ylabel,
            x_ticks_minor=5,
            x_ticks_major=25,
            y_ticks_major=1,
            y_grid_label=True,
            x_grid_label=True,
            padding=5,
            xlog=False,
            ylog=False,
            x_grid=False,
            y_grid=False,
            xmin=self.xmin,
            xmax=self.xmax,
            ymin=self.ymin,
            ymax=self.ymax,
            **graph_theme)

        root_graph_layout = self.ids['root_graph']

        plot = BarPlot(color=next(colors), bar_spacing=.72)
        graph.add_plot(plot)
        plot.bind_to_graph(graph)
        plot.points = self.points
        root_graph_layout.add_widget(graph)


class GraphPopup(Popup):
    text_ok = StringProperty('Close')

    def __init__(self, **kwargs):
        super(GraphPopup, self).__init__(**kwargs)
        graph_widget = StatGraphPanel(**kwargs)
        self.ids['stats_panel'].add_widget(graph_widget)

    def submit_data(self):
        self.dismiss()


class StatsPanel(TabbedPanelItem):
    metric = StringProperty()
    range = StringProperty()

    def __init__(self, **kwargs):
        super(StatsPanel, self).__init__(**kwargs)
        self.populate()

    def populate(self):
        query_result = self.retrieve_data()
        if query_result['result_set'] == [(None, '0')]:
            stats_panel_widget = Label(text='No data')
        else:
            processed_result_set = [(int(k[0].replace('-', '')), float(k[1]))
                                    for k in query_result['result_set']]
            xmin = min([x[0] for x in processed_result_set])
            xmax = max([x[0] for x in processed_result_set])
            ymax = max([x[1] for x in processed_result_set])
            stats_panel_widget = StatGraphPanel(title=query_result['title'],
                           data = query_result['result_set'],
                           points=processed_result_set,
                           xmin=xmin,
                           xmax=xmax,
                           ymax=ymax)
        self.ids['stats_panel'].add_widget(stats_panel_widget)

    def retrieve_data(self):
        from ia_scribe.breadcrumbs.api import get_data
        interval = self.range
        slice = 'monthly' if self.range == 'yearly' else 'daily' if self.range not in ['today', 'yesterday'] else 'hourly'
        res = get_data(self.metric, interval, slice)
        return res


class TabbedStatPopup(BoxLayout):
    metric_name = StringProperty(allownone=False)
    metric_array = ObjectProperty()
    description = StringProperty('')

    def __init__(self, **kwargs):
        super(TabbedStatPopup, self).__init__(**kwargs)
        self.get_metric_info()
        self.populate_tabs()

    def get_metric_info(self):
        from ia_scribe.breadcrumbs.config import AGGREGATIONS
        if self.metric_name not in list(AGGREGATIONS.keys()):
            raise Exception('No aggregation with this name')
        self.metric_array = AGGREGATIONS[self.metric_name]
        self.description = self.metric_array['description']

    def populate_tabs(self):
        from ia_scribe.breadcrumbs.config import AVAILABLE_RANGES
        for range in list(AVAILABLE_RANGES.keys()):
            tab = StatsPanel(metric=self.metric_name,
                             range=range,
                             text=range)
            self.ids.tp.add_widget(tab)
            if range == 'today':
                self.ids.tp.default_tab = tab


class CompositeInfoPopup(FormPopup):
    additional_content = ObjectProperty()

    OPTION_OK = 'ok'

    message = StringProperty()
    text_ok = StringProperty('OK')

    title_bar_height = NumericProperty(0)
    '''Height of title bar which includes label, separator, padding and 
    spacing. Property is readonly.
    '''

    container_padding = VariableListProperty([0, 0, 0, 0])
    '''Padding of popup container. Property is readonly.
    '''

    def __init__(self, **kwargs):
        self.additional_content = kwargs.pop('additional_content', None)
        if self.additional_content and not isinstance(self.additional_content, Widget):
            raise Exception('Additional content must be a widget')
        self._title_height_trigger = \
            trigger = Clock.create_trigger(self._update_title_height, -1)
        self.fbind('children', trigger)
        self.fbind('children',
                   Clock.create_trigger(self._update_container_padding))
        super(CompositeInfoPopup, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args, **kwargs):
        title_label = self.children[0].children[-1]
        title_label.fbind('height', self._title_height_trigger)
        self._update_title_height()
        if self.additional_content:
            self.ids.additional_content_container.add_widget(self.additional_content)

    def _update_title_height(self, *args):
        if not self.children:
            self.title_bar_height = 0
            return
        first_child = self.children[0]
        height = first_child.padding[1] + first_child.padding[3]
        index = 0
        for index, child in enumerate(first_child.children[1:]):
            height += child.height
        height += index * first_child.spacing[1]
        self.title_bar_height = height

    def _update_container_padding(self, *args):
        if not self.children:
            self.container_padding = [0] * 4
            return
        self.container_padding = self.children[0].padding

    def _handle_keyboard(self, window, key, *largs):
        if key == 13 or key == 32:
            # Keys "enter" and "spacebar" are used to confirm
            # Key "esc" will dismiss popup by default
            self.submit_data(self.OPTION_OK)
            return True
        return super(CompositeInfoPopup, self)._handle_keyboard(window, key, *largs)


# an overlay that is supposed to just wholly contain a widget
class WidgetPopup(Popup):
    screen_manager = ObjectProperty(allownone=True)

    def __init__(self, content_class, title='', **kwargs):
        super(WidgetPopup, self).__init__(**kwargs)
        self.title = title
        self.content = content_class()
        self.screen_manager = kwargs.get('screen_manager')
        self.__class__.__name__ = '{}WidgetPopup'.format(content_class.__name__)

    def on_open(self, *args):
        pass

    def on_dismiss(self, *args):
        pass

    def bind_events(self, events_mapping):
        for event_name, binding in list(events_mapping.items()):
            concrete_event = getattr(self.content, event_name)
            self.content.fbind(concrete_event, binding)

