class BaseQuailException(Exception):
    message = None
    status_code = 500

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class AuthenticationError(BaseQuailException):
    status_code = 401
