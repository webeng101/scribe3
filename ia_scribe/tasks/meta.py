from ia_scribe.tasks.generic import CallbackTask


class MetaSchedulerTask(CallbackTask):

    def __init__(self, **kwargs):
        self._scheduling_callback = kwargs.pop('scheduling_callback')
        self._tasks_list = []
        super(MetaSchedulerTask, self).__init__(**kwargs)


    def create_pipeline(self):
        return [
            self._prepare,
            self._fill_list,
            self._schedule_tasks,
            self._do_call_back
        ]

    def _prepare(self):
        del self._tasks_list[:]

    def _fill_list(self):
        raise NotImplementedError()

    def _schedule_tasks(self):
        for task in self._tasks_list:
            self._scheduling_callback(task)


class LinearSchedulerTask(CallbackTask):

    def __init__(self, **kwargs):
        super(LinearSchedulerTask, self).__init__(**kwargs)
        self._scheduling_callback = kwargs['scheduling_callback']
        self._tasks_list = []

    def create_pipeline(self):
        pipeline = self._build_pipeline_steps()
        pipeline.append(self._do_call_back)
        return pipeline

    def _build_pipeline_steps(self):
        raise NotImplementedError()