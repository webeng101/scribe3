class ScribeException(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class DiskFullError(Exception):
    pass

class CredentialsError(ScribeException):
    pass