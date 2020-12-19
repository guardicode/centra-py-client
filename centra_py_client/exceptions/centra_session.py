class CentraAPIBaseError(Exception):
    """ Base Exception for Centra API Errors """
    pass


class CentraAPIError(CentraAPIBaseError):
    """ Raised when Centra could not fulfil the request """
    pass


class RedirectionRequiredError(CentraAPIBaseError):
    """ Raised when query redirection is required but could not be performed """


class CentraAPIRequestTimeout(CentraAPIBaseError):
    """ Raised when Centra responds with request timeout (HTTP 504) """
    pass


class CentraAuthError(CentraAPIBaseError):
    """ Raised when authentication related errors occur """
    pass


class BadAPIRequest(CentraAPIBaseError):
    """ Raised when the requested URL could not be found (HTTP 404) or when the HTTP request type is invalid """
    pass


class NoPermissionToAccessResource(CentraAPIBaseError):
    """ Raised when trying to access a resource without sufficient permissions (HTTP 403) """
    pass
