import datetime


class QuickLog(object):

    def __init__(self, name, log_path):
        self.name = name
        self.log_path = log_path

    def log(self, msg):
        try:
            with open(self.log_path, "a") as f:
                f.write("{}: {} \n".format(str(datetime.datetime.now()), msg))
        except OSError as ose:
            print("Couldn't write to log\nError: {}".format(ose.args))


class ResponseSaved(object):

    def __init__(self, *args, **kwargs):
        super(ResponseSaved, self).__init__(*args, **kwargs)
        self.success = kwargs.get('success', False)
        self.saved_to = kwargs.get('saved_to')
        self.time_taken = kwargs.get('time_taken', -1)
        self.error = kwargs.get('error', False)  # To pass exceptions
        self.error_message = kwargs.get('error_message', '')  # To pass custom error message
        self.not_ok_reason = kwargs.get('not_ok_reason', '')  # response.reason
