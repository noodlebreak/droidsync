"""
SimpleSync - Simple file/dir sync app
for syncing across different machines.

Two main components:
    * Observer:  Watches filesystem events in the directory specified in config,
                 pushes them to remote machine.
    * Webserver: Serves fetch requests, and handles sync requests to pull files
                 from notifying machine.

"""
import datetime
import os
import shutil
import sys

from watchdog import events

import observer
import transporter
from utils import QuickLog

__author__ = "Ashish Kumar (ashish26kr91@gmail.com)"
__version__ = "0.0.1"

logger = QuickLog(name='simplesync_main', log_path='simplesync_{}.log'.format(datetime.date.today()))


class Syncer(object):
    VALID_CHANGE_TYPES = [
        events.EVENT_TYPE_CREATED,
        events.EVENT_TYPE_MODIFIED,
        events.EVENT_TYPE_DELETED,
        events.EVENT_TYPE_MOVED,
    ]

    NEEDS_FETCH_TYPE_EVENTS = [
        events.EVENT_TYPE_CREATED,
        events.EVENT_TYPE_MODIFIED,
    ]

    def _is_created(self, change_type):
        return change_type == events.EVENT_TYPE_CREATED

    def _is_modified(self, change_type):
        return change_type == events.EVENT_TYPE_MODIFIED

    def _is_deleted(self, change_type):
        return change_type == events.EVENT_TYPE_DELETED

    def _is_moved(self, change_type):
        return change_type == events.EVENT_TYPE_MOVED

    def _needs_fetch(self, change_type):
        return change_type in self.NEEDS_FETCH_TYPE_EVENTS

    def is_valid_change_data(self, notif_data):
        errors = []
        if not isinstance(notif_data, dict):
            errors.append("Not a dict")
        if 'change_type' not in notif_data:
            errors.append("change_type key not found")
        if 'src_path' not in notif_data:
            errors.append("src_path key not found")
        if 'is_dir' not in notif_data:
            errors.append("is_dir key not found")
        if 'time' not in notif_data:
            errors.append("time key not found")
        if notif_data.get('change_type') not in self.VALID_CHANGE_TYPES:
            errors.append("change_type value is invalid. Valid choices: {}".format(
                ", ".join(self.VALID_CHANGE_TYPES)))
        self.errors = errors

    def remote_fetch(self, data):
        transporter.TheTransporter()
        pass

    def _delete(self, src_path, is_dir):
        if is_dir:
            remove_func = os.rmdir
        else:
            remove_func = os.remove
        try:
            remove_func(src_path)
        except OSError as ose:
            if ose.args[0] == 2:
                # Doesn't exist
                pass
            else:
                # TODO Some other error. Permissions or something perhaps. Handle this
                logger.log("Error in deleting {}: {}".format(src_path, ose.args))
                pass

    def _move(self, src_path, dest_path, is_dir):
        try:
            shutil.move(src_path, dest_path)
        except OSError as ose:
            if ose.args[0] == 2:
                # Doesn't exist
                pass
            else:
                # TODO Some other error. Permissions or something perhaps. Handle this
                logger.log("Error in moving {}: {}".format(src_path, ose.args))
                pass

    def modify_local(self, data):
        if data['change_type'] is events.EVENT_TYPE_DELETED:
            self._delete(data['src_path'], data['is_dir'])
        elif data['change_type'] is events.EVENT_TYPE_MOVED:
            """
            Types:
                Directories
                    RENAME: dirA to dirB
                        shutil.move('dirA', 'dirB')
                    MOVE INSIDE: dirA to dirB
                        shutil.move('dirA', 'dirB')
                Files:
                    RENAME:
                        shutil.move('x', 'y')
                    MOVE
                        shutil.move('x', 'dir')


            """
            self._move(data['src_path'], data['dest_path'], data['is_dir'])

    def notification_handler(self, notif_data):
        """
        notif_data = {
            'change_type': 'created',
            'src_path': '/tmp/abc',  # source path on remote
            'dest_path': '/tmp/xyz',  # in case change_type is `moved`
            'is_dir': True/False,
            # 'file_hash': 'ddfdf', # present if is_dir is False and change_type is created/modified
            'time': 144414141, # unix time stamp upto
        }
        """
        if not self.is_valid_change_data(notif_data):
            return self.errors
        if self._needs_fetch(notif_data['change_type']):
            self.remote_fetch(notif_data)  # Need to fetch file system objects from other machine
        else:
            self.modify_local(notif_data)  # Need to only modify local filesystem

        pass


if __name__ == "__main__":
    watch_dir = '.'
    if len(sys.argv) > 1:
        watch_dir = sys.argv[1]
    # Create an observer process, initialize with syncer, transporter, and accountant (keep None for now)
    # Create a webserver process, initialize with syncer, transporter, and accountant (keep None for now)
    observer.watch_filesystem(watch_dir, notify=True)
