class ManagementAPIError(Exception):
    def __init__(self, message):
        super(ManagementAPIError, self).__init__(message)


class ManagementAPITimeoutError(ManagementAPIError):
    def __init__(self, message):
        super(ManagementAPITimeoutError, self).__init__(message)


class RESTAuthenticationError(ManagementAPIError):
    def __init__(self, response):
        data = response.json()
        super(RESTAuthenticationError, self).__init__('%s: %s' % (data['error'],
                                                                  data['description']))
        self.data = data
