import subprocess
import types

from ia_scribe.tasks.task_base import TaskBase


class CallbackTask(TaskBase):

    def __init__(self, **kwargs):
        self._callback = kwargs.pop('callback', None)
        super(CallbackTask, self).__init__(**kwargs)

    # TODO: Find a way to add callback call at the end of pipeline
    # After overriding create_pipeline is done.
    # For now, just rely on the child class to add it

    def _do_call_back(self):
        if self._callback:
            self._callback(self)


class GenericFunctionTask(TaskBase):

    def __init__(self, **kwargs):
        self._function = kwargs.pop('function')
        self._name = kwargs.pop('name', str(self._function.__name__))
        self._args = kwargs.pop('args', None)
        super(GenericFunctionTask, self).__init__(**kwargs)
        self._kwargs = kwargs.get('kwargs', None)

    def create_pipeline(self):
        return [
            self._run,
        ]

    def _run(self):
        self.dispatch_progress('Running {}'.format(self._name))
        if self._args:
            if self._kwargs:
                self._function(*self._args, **self._kwargs)
            else:
                self._function(*self._args)
        elif self._kwargs:
            self._function( **self._kwargs)
        else:
            self._function()


class SubprocessTask(CallbackTask):

    def __init__(self, **kwargs):
        self._command = kwargs['command']
        self._output = None
        self._error = None
        self._exit_code = None
        super(SubprocessTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [
            self._run,
            self._do_call_back
        ]

    def _run(self):
        self.dispatch_progress('Running {}'.format(self._command))
        process = subprocess.Popen(
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        output, error = process.communicate()
        self._output, self._error = output.decode(), error.decode()
        self._exit_code = process.returncode

    def _do_call_back(self):
        if self._callback:
            self._callback(self._exit_code, self._output, self._error, self)


def taskify(target_function, args=None, kwargs=None, name=None,):
    if type(target_function) is not types.FunctionType:
        return None
    task = GenericFunctionTask(
        function=target_function,
        name=name if name else target_function.__name__,
        args=args if args else [],
        kwargs=kwargs if kwargs else {},
    )
    return task

