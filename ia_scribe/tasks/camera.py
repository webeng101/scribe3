from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.meta import MetaSchedulerTask

class FetchCameraPropertiesTask(TaskBase):

    def __init__(self, **kwargs):
        super(FetchCameraPropertiesTask, self).__init__(**kwargs)
        self._camera_system = kwargs['camera_system']
        self._side = kwargs['side']
        self._update_callback = kwargs.get('update_callback')
        self._all_properties = []
        self._properties = []

    def create_pipeline(self):
        return [
            self._list_properties,
            self._filter_properties,
            self._fetch_properties,
        ]

    def _list_properties(self):
        self._all_properties = self._camera_system.list_camera_properties(self._side)

    def _filter_properties(self):
        self._properties = [x for x in self._all_properties
                            if 'other' not in x
                            and x not in ['', ' ', None]]

    def _fetch_properties(self):
        for prop in self._properties:
            property_value = self._camera_system.get_camera_property(self._side, prop)
            self._camera_system.add_camera_property(self._side, prop, property_value)
            if self._update_callback:
                self._update_callback(self._side, prop, property_value)


class PopulateCamerasPropertiesTask(MetaSchedulerTask):

    def __init__(self, **kwargs):
        super(PopulateCamerasPropertiesTask, self).__init__(**kwargs)
        self._priority = 'medium'
        self._camera_system = kwargs['camera_system']
        self._update_callback = kwargs.get('update_callback', None)

    def _fill_list(self):
        for side in self._camera_system.get_active_cameras():
            task = FetchCameraPropertiesTask(camera_system=self._camera_system,
                                             side=side,
                                             update_callback=self._update_callback
                                             )
            self._tasks_list.append(task)