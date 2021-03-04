from os.path import join, dirname

from kivy.lang import Builder

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanelItem

from ia_scribe.uix.components.poppers.popups import InfoPopup
from ia_scribe.uix.widgets.taskman.task_manager import TaskManager

Builder.load_file(join(dirname(__file__), 'stakhanov_widget.kv'))


class StakhanovTaskList(TabbedPanelItem):
    pass


class StakhanovWidget(BoxLayout):

    def __init__(self, **kwargs):
        super(StakhanovWidget, self).__init__(**kwargs)
        self.new_manager = TaskManager()
        #self.stats = kwargs['stats']
        self.populate_tabs()

    def release_refs(self, *args):
        self.new_manager.detach_scheduler()

    def populate_tabs(self):

        new_manager_tab = TabbedPanelItem(text='Tasks')
        new_manager_tab.add_widget(self.new_manager)
        # self.ids.tp.add_widget(events_tab)
        self.ids.tp.add_widget(new_manager_tab)
        # self.ids.tp.add_widget(stats_tab)

        self.ids.tp.default_tab = new_manager_tab

    def show_task_details_popup(self, payload):
        popup = InfoPopup(
            title='Task details',
            message=str(payload),
            auto_dismiss=False
        )
        popup.bind(on_submit=popup.dismiss)
        popup.open()

    def get_pending_tasks(self, queue):
        tasks_list_size = queue.qsize()
        tlist = []
        for i in range(tasks_list_size):
            tlist.append(queue.queue[i])
        return reversed(tlist), tasks_list_size

    def format_for_simple_list(self, raw_tasks_list, queue_name ):
        formatted_task_list = []
        if queue_name == 'Results':
            img = 'done.png'
        elif queue_name == 'Pending':
            img = 'baseline_av_timer_white_48dp.png'
        else:
            img = 'baseline_navigate_next_white_48dp.png'
        for t in raw_tasks_list:
            task = t[0]
            info = str(t[1])
            if type(t[1]) is Exception:
                img = 'close_x.png'
            funname = task.__name__ if hasattr(task, '__name__') else str(task)
            temp_d = {'key': funname, 'value': info, 'image': img}
            formatted_task_list.append(temp_d)
        return formatted_task_list