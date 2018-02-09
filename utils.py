import datetime
import logging

logger = logging.getLogger('simplesync')
hdlr = logging.FileHandler('/tmp/simplesync.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


class QuickLog(object):

    def __init__(self, name, log_path):
        self.name = name
        self.log_path = log_path

    def log(self, msg):
        logger.info(msg)
        # try:
        #     with open(self.log_path, "a") as f:
        #         f.write("{}: {} \n".format(str(datetime.datetime.now()), msg))
        # except OSError as ose:
        #     print("Couldn't write to log\nError: {}".format(ose.args))


class ResponseSaved(object):

    def __init__(self, *args, **kwargs):
        self.success = kwargs.get('success', False)
        self.saved_to = kwargs.get('saved_to')
        self.time_taken = kwargs.get('time_taken', -1)
        self.error = kwargs.get('error', False)  # To pass exceptions
        self.error_message = kwargs.get('error_message', '')  # To pass custom error message
        self.not_ok_reason = kwargs.get('not_ok_reason', '')  # response.reason

    def __unicode__(self):
        return "{}-{}-{}-{}-{}".format(self.success, self.saved_to, self.time_taken,
                                       self.error, self.error_message, self.not_ok_reason)
