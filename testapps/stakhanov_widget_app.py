from pprint import pprint
from queue import Queue

from kivy.config import Config

Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App

from ia_scribe.uix.widgets.taskman.stakhanov_widget import StakhanovWidget


class WorkingClass(App):

    def build(self):
        tqueue = Queue()
        tqueue.put({'test_task1':'yes'})
        tqueue.put({'key':'test', 'value':'antani'})

        root = StakhanovWidget(size_hint=(0.9, 0.9),
                           pos_hint={'center_x': 0.5, 'center_y': 0.5},

                               tasks_queue=tqueue,
                               pending_queue=tqueue,
                               results_queue=tqueue,
                               )

        #root.bind(on_book_select=self.on_book_select)
        return root


    def on_book_select(self, library_view, book):
        print('Selected book:')
        pprint(book)
        print('')


if __name__ == '__main__':
    WorkingClass().run()
