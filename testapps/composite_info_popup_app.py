from pprint import pprint

from kivy.app import App

from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.components.plots.path_visualization import \
    PathVisualizationWidget
from ia_scribe.uix.components.poppers.popups import CompositeInfoPopup

DATA = ['scribing', 'identifier_assigned', 'packaging_in_progress',
        'upload_queued', 'upload_in_progress', 'uploaded']


class PageTypeFormPopupApp(App):

    def build(self):
        additional_content = PathVisualizationWidget()
        additional_content.make_data(DATA)
        self.popup = popup = CompositeInfoPopup(
            message='Aliquam voluptates vero et delectus. '
                    'Qui consequuntur perferendis incidunt consequatur aut '
                    'doloremque. Mollitia explicabo nisi magni iure. Amet et '
                    'corporis et quas qui quia. Officia qui officiis qui '
                    'voluptas ut et maiores voluptatem. Magni et doloremque '
                    'assumenda dolores ',
            additional_content=additional_content)
        popup.bind(on_submit=self.on_data_submit)
        button = ColorButton(text='Open popup', size_hint=(None, None),
                             pos_hint={'center_x': 0.5, 'center_y': 0.9})
        button.bind(on_release=popup.open)
        popup.target_widget = button
        return button

    def on_data_submit(self, popup, data):
        print('Submitted:')
        pprint(data)


if __name__ == '__main__':
    PageTypeFormPopupApp().run()
