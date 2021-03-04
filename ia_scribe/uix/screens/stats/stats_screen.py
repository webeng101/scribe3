from os.path import join, dirname

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.properties import BooleanProperty
from kivy.uix.recycleview import RecycleView
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior

from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.uix.components.poppers.popups import TabbedStatPopup
from ia_scribe.breadcrumbs.api import get_data, get_data_for_operator, \
    get_available_aggregations_and_metadata

Builder.load_file(join(dirname(__file__), 'stats_screen.kv'))

config = Scribe3Configuration()

AVAILABLE_SCREENS = [
    {
        'text': 'Operator',
        'icon': 'user.png',
        'key': 'user_stats',
        'color': 'transparent',
        'text_color': [0, 0, 0, 1],
        'group': 'stats_menu_view_control',
    },
    {
        'text': 'Dashboard',
        'icon':'chart_outlined_black.png',
        'key': 'dashboard',
        'color': 'transparent',
        'text_color': [0,0,0,1],
        'group': 'stats_menu_view_control',
     },
    {
        'text': 'Metrics',
         'icon':'list_view_icon.png',
         'key': 'metrics',
         'color': 'transparent',
         'text_color': [0,0,0,1],
         'group': 'stats_menu_view_control',
     },

]


class StatEntry(BoxLayout, RecycleDataViewBehavior):
    index = None
    name = StringProperty()
    title = StringProperty()
    interval = StringProperty()
    slice = StringProperty()
    description = StringProperty()
    value = StringProperty()
    icon = StringProperty('stats.png')
    graphable = BooleanProperty(False)
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def set_width(self, width):
        self.size_hint_x = None
        self.width = width

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(StatEntry, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        if super(StatEntry, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            self.show_popup()

    def show_popup(self):
        ts = TabbedStatPopup(metric_name=self.name)
        p = Popup(
            title=self.title, content=ts, size_hint=(None, None),
            size=('1040dp', '800dp')
        )
        p.open()


class StatsRecycleView(RecycleGridLayout):
    def __init__(self, **kwargs):
        super(StatsRecycleView, self).__init__(**kwargs)


class AllStatsView(RecycleView):
    def __init__(self, **kwargs):
        super(AllStatsView, self).__init__(**kwargs)
        items = get_available_aggregations_and_metadata()
        self._update_rv(items)

    def _update_rv(self, items, scroll_to_top=False):
        self.data = items
        if scroll_to_top:
            self.scroll_y = 1.0


class StatsDisabledView(BoxLayout):
    message = StringProperty('Stats are disabled.\nGo to Options ->'
                             ' General and toggle "Disable stats" to re-enable.')


class UserStatsView(BoxLayout):
    available_users = ListProperty()
    selected_user = StringProperty()

    def __init__(self, **kwargs):
        super(UserStatsView, self).__init__(**kwargs)
        self._load_users()
        self._select_current_user()

    def _load_users(self):
        active_users = get_data('operators','past_week', 'weekly')
        if not active_users['result_set'] == [(None, '0')]:
            self.available_users = active_users['result_set']

    def _select_current_user(self):
        current_operator = config.get('operator', )
        if current_operator in self.available_users:
            self.ids.user_spinner.spinner_text = current_operator

    def select_user(self, spinner, value):
        self.selected_user = value


class UserDashboardView(AllStatsView):
    user = StringProperty()
    stats_to_be_displayed = [
        ('pages_per_hour_by_operator', 'today', 'daily'),
        ('pages_per_hour_by_operator', 'past_week', 'weekly'),
        ('captures_by_operator', 'today', 'daily'),
        ('uploads_by_operator', 'today', 'daily'),
        ('captures_by_operator', 'past_week', 'weekly'),
        ('uploads_by_operator', 'past_week', 'weekly'),
        ('captures_by_operator', 'past_month', 'monthly'),
        ('uploads_by_operator', 'past_month', 'monthly'),
        ('books_created_by_operator', 'today', 'daily'),
        ('books_created_by_operator', 'past_month', 'monthly'),
        ]

    def __init__(self, **kwargs):
        super(UserDashboardView, self).__init__(**kwargs)

    def on_user(self, *args, **kwargs   ):
        if self.user not in [None, '']:
            self.data = self.get_data()

    def get_data(self):
        ret = []
        for entry in self.stats_to_be_displayed:
            res = get_data_for_operator(self.user, *entry)
            ret.append(res)
        return ret


class DashboardView(AllStatsView):
    stats_to_be_displayed = [
        ('active_operators', 'past_week', 'weekly'),
        ('total_captures', 'today', 'daily'),
        ('total_captures', 'past_week', 'weekly'),
        ('average_capture_speed', 'today', 'daily'),
        ('total_books_uploaded', 'past_week', 'weekly'),
        ('total_books_downloaded', 'past_week', 'weekly'),
        ('app_sessions', 'past_week', 'weekly'),
        ('app_sessions', 'today', 'daily'),
        #('tasks_ran', 'past_week', 'hourly'),

    ]

    def __init__(self, **kwargs):
        super(DashboardView, self).__init__(**kwargs)
        items = self.get_data()
        self._update_rv(items)

    def get_data(self):
        res = []
        for entry in self.stats_to_be_displayed:
            res.append(get_data(*entry))
        return res


class StatsScreen(Screen):
    loading_image = StringProperty(LOADING_IMAGE)
    active_screen = StringProperty()

    def __init__(self, **kwargs):
        super(StatsScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        if not config.is_true('stats_disabled'):
            self._update_buttons_menu(AVAILABLE_SCREENS)
            self.ids.rv_menu.fbind('on_selection', self._on_menu_option_selection)
            self.display_user_view()
        else:
            self.display_disabled_view()

    def _update_buttons_menu(self, items):
        self.ids.rv_menu.data = items

    def _on_menu_option_selection(self,  menu, selection):
        selected = selection[0]
        self.active_screen = selected['key']
        if selected['key'] == 'metrics':
            self.display_all_stats()
        elif selected['key'] == 'dashboard':
            self.display_dashboard()
        elif selected['key'] == 'user_stats':
            self.display_user_view()

    def display_all_stats(self):
        self.ids.content_canvas.clear_widgets()
        view = AllStatsView()
        self.ids.content_canvas.add_widget(view)

    def display_dashboard(self):
        self.ids.content_canvas.clear_widgets()
        view = DashboardView()
        self.ids.content_canvas.add_widget(view)

    def display_user_view(self):
        self.ids.content_canvas.clear_widgets()
        view = UserStatsView()
        self.ids.content_canvas.add_widget(view)

    def display_disabled_view(self):
        self.clear_widgets()
        view = StatsDisabledView()
        self.add_widget(view)