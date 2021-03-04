from kivy.app import App
from kivy.lang import Builder

kv = '''
FloatLayout:
    LeafMenuBar:
        use_tooltips: True
        orientation: 'right'
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        on_option_select: label.text = 'Selected: ' + args[1]
    Label:
        id: label
        size_hint_y: None
        font_size: '22sp'
'''


class LeafMenuBarApp(App):

    def build(self):
        root = Builder.load_string(kv)
        menu = root.children[1]
        menu.bind(on_option_select=self.on_menu_option_select)
        return root

    def on_menu_option_select(self, menu, option):
        print('Selected', option)


if __name__ == '__main__':
    LeafMenuBarApp().run()
