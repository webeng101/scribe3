import threading

def singleton(target_class):
    classInstances = {}

    def getInstance(*args, **kwargs):
        key = (target_class, args, str(kwargs))
        if key not in classInstances:
            classInstances[key] = target_class(*args, **kwargs)
        return classInstances[key]

    return getInstance


def mixin_factory(name, base, mixin, namespace={}):
    return type(name, (base, mixin), namespace)


def thread_safe(f):
    def wrapper(*args):
        # if this is a fysom-wrapped call, the object is passed as e
        if len(args)>1:
            if type(args[1]) == dict:
                # this is a patch (thread_safe called on update())
                book = args[0]
            elif type(args[1]).__name__ == '_e_obj':
                book = args[1].obj
            else:
                raise Exception('Unhandled thread_safe argument')
        else: # if this is any other class method calling with self
            book = args[0]

        if book.set_lock():
            res = f(*args)
            book.release_lock()
            return res
        else:
            raise Exception('Could not acquire lock | Args: {}'.format(args))
    return wrapper


class Observable(object):
    #observers = set([])
    # This property must be defined in the inheriting class

    def __init__(self):
        self.id = id(self)
        self.observers = set()
        super(Observable, self).__init__()

    def subscribe(self, observer):
        self.observers.add(observer)

    def unsubscribe(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify(self, event):
        for observer in self.observers:
            observer(event, self)

class Singleton(object):
    # use special name mangling for private class-level lock
    # we don't want a global lock for all the classes that use Singleton
    # each class should have its own lock to reduce locking contention
    __lock = threading.Lock()

    # private class instance may not necessarily need name-mangling
    __instance = None

    @classmethod
    def instance(cls):
        if not cls.__instance:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = cls()
        return cls.__instance