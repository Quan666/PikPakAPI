class PikpakException(Exception):
    def __init__(self, message):
        super().__init__(message)


class PikpakRetryException(PikpakException):
    pass
