class BaseQuailException(Exception):
    status_code = 500
    message = "Server error"

    def __init__(self, message=None, status_code=None):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code

    def __str__(self):
        return f"Exception: {self.status_code=} {self.message=}"


class AuthenticationError(BaseQuailException):
    status_code = 401


class PermissionsMissing(BaseQuailException):
    status_code = 400


class UnauthorizedForInstanceError(BaseQuailException):
    status_code = 403
    message = "You're not authorized to modify this instance."


class InstanceUpdateError(BaseQuailException):
    status_code = 400
    message = "Instance update has failed."


class InvalidArgumentsError(BaseQuailException):
    status_code = 400


class StackSetCreationException(BaseQuailException):
    pass


class StackSetExecutionInProgressException(BaseQuailException):
    status_code = 415
    message = "Try again later."


class StackSetUpdateInProgressException(BaseQuailException):
    status_code = 415
    message = "Try again later."


class InvalidApplicationState(BaseQuailException):
    pass
