class FormBehavior(object):

    __events__ = ('on_submit',)

    def collect_data(self):
        return None

    def submit_data(self, data=None):
        if data is None:
            data = self.collect_data()
        self.dispatch('on_submit', data)

    def reset(self):
        pass

    def on_submit(self, data):
        pass
