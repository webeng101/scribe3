from kivy.app import App
from kivy.lang import Builder

import ia_scribe

kv = '''
NumberInput:
    pos_hint: {'center_x': 0.5, 'center_y': 0.5}
    value: None
    none_value_allowed: True
    min_value: 1
    max_value: 100
    value_type: float
    width: '100dp'
'''


class NumberInputApp(App):

    def build(self):
        root = Builder.load_string(kv)
        root.bind(value=self.on_autoshoot_value)
        return root

    def on_autoshoot_value(self, autoshoot_input, value):
        print('New value', value)


if __name__ == '__main__':
    NumberInputApp().run()
