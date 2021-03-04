import os, glob, time, signal, sys, shutil
from ia_scribe.tasks.task_scheduler import TaskScheduler
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.scribe_globals import BOOKS_DIR

class TaskTexual(TaskBase):

    def dispatch_progress(self, message, **kwargs):
        self.logger.info(message)

class ProcessMicrofilmTask(TaskTexual):

    def __init__(self, **kwargs):
        super(ProcessMicrofilmTask, self).__init__(**kwargs)
        self.path = kwargs.get('path')
        self.token = str(os.getpid())

    def create_pipeline(self):
        return [
            self._verify_preconditions,
            self._acquire_lock,
            self._load_files,
            self._remove_lock,
        ]

    def _verify_preconditions(self):
        donefile = os.path.join(self.path, 'done')
        lockfile = os.path.join(self.path, 'task_lock')
        if os.path.isfile(donefile):
            raise Exception('Refusing to run on done folder')
        if os.path.isfile(lockfile):
            raise Exception('Botched upload or resource busy')

    def _acquire_lock(self):
        self.dispatch_progress('Acquiring lock {} for path {}'.format(
            self.token, self.path))
        to_delete = os.path.join(self.path, 'ready_to_upload')
        to_create = os.path.join(self.path, 'task_lock')
        with open(to_create, 'w+') as f:
            f.write(self.token)
        os.remove(to_delete)

    def _load_files(self):
        self.dispatch_progress('Loading files for path {}'.format(self.path))
        for fake_activity in ['identifier generation',
                         'compression',
                         'packaging',
                         'upload']:
            self.logger.info('Running -> {}'.format(fake_activity))
            time.sleep(1)

    def _remove_lock(self):
        self.dispatch_progress('Removing lock {} at path {}'.format(
            self.token, self.path))
        to_delete = os.path.join(self.path, 'task_lock')
        to_create = os.path.join(self.path, 'done')
        with open(to_delete, 'r') as f:
            task_pid = f.read()
            if not task_pid == self.token:
                raise Exception('PID MISMATCH!')

        with open(to_create, 'w+') as f:
            f.write(self.token)
        os.remove(to_delete)

class FolderMonitor(TaskTexual):

    def __init__(self, **kwargs):
        super(FolderMonitor, self).__init__(**kwargs)
        self.queue_task_callback = kwargs.get('queue_task_callback')
        self.dispatch_queue = []
        self.base_path = os.path.expanduser('~/microfilm')

    def create_pipeline(self):
        return [
            self._scan_directory,
            self._queue_new_tasks,
        ]

    def _scan_directory(self):
        self.dispatch_progress('Scanning directory {}'.format(self.base_path))
        for item in self.__load_directories(self.base_path):
            if self.__should_run(item):
                fully_qualified_path = os.path.join(self.base_path, item)
                self.dispatch_queue.append(fully_qualified_path)
        self.dispatch_progress('Found {} new paths'.format(len(self.dispatch_queue)))

    def _queue_new_tasks(self):
        self.dispatch_progress('Queueing new tasks')
        for _ in range(0, len(self.dispatch_queue)):
            path = self.dispatch_queue.pop()
            self.queue_task_callback(task=ProcessMicrofilmTask,
                                     path=path)

    def __load_directories(self, root_dir):
        paths = glob.glob(os.path.join(root_dir, '*'))
        ids = list(map(self.__get_id_from_path, paths))
        return ids

    def __should_run(self, path):
        full_path = os.path.join(self.base_path, path, 'ready_to_upload')
        ret = os.path.isfile(full_path)
        return ret

    def __get_id_from_path(self, path):
        ret = path.split('/')[-1:][0]
        return ret


class HeadlessScribe3(object):

    def __init__(self, *args, **kwargs):
        self.task_scheduler = TaskScheduler()

    def queue_task_callback(self, *args, **kwargs ):
        task = kwargs['task']
        path = kwargs['path']
        concrete_task = task(path=path)
        self.task_scheduler.schedule(concrete_task)

    def termination_handler(self, sig, frame):
        print('Soft termination: stopping task scheduler and waiting '
              'for workers to exit cleanly')
        self.task_scheduler.stop()
        print('Workers stopped, now exiting')
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.termination_handler)
        self.task_scheduler.start()
        check_folder_task = FolderMonitor(periodic=True,
                          interval=5.0,
                          queue_task_callback=self.queue_task_callback,)
        self.task_scheduler.schedule(check_folder_task)
        while True:
            pass

