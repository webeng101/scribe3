import argparse, sys, inspect
from ia_scribe import tasks

def validate(target_task_type, args):
    clsmembers = inspect.getmembers(sys.modules[tasks], inspect.isclass)
    print(clsmembers)
    return target_task_type in clsmembers

def load():
    from ia_scribe.tasks.task_scheduler import TaskScheduler
    task_scheduler = TaskScheduler()
    task_scheduler.start()
    return True

def run(*args, **kwargs):
    print(args, kwargs)

if __name__ == '__main__':
    # Configure argparser

    parser = argparse.ArgumentParser(description='BeepBeep')
    parser.add_argument('--task', '-t', default=None, type=str,
                        help="Task Class to run")

    named_args, unnamed_args = parser.parse_known_args()
    sys.argv[1:] = unnamed_args
    downstream_args = sys.argv[1:]
    if named_args.task:
        print('Named arg is present: {}'.format(named_args.task))
        if validate(named_args.task, unnamed_args):
            print('Named arg is valid')
            if load():
                print('Loaded runtime successfully')
                run(named_args.task, unnamed_args)
