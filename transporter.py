import datetime
import os

import requests

import conf
import shutil_dl
from utils import QuickLog

logger = QuickLog(name='transporter', log_path='ss_transporter_{}.log'.format(datetime.date.today()))


class TheTransporter(object):

    def __init__(self, *args, **kwargs):
        self.local_sync_dir = kwargs.get('local_sync_dir', conf.DEFAULT_LOCAL_SYNC_DIR)
        self.remote_ip = kwargs.get('remote_ip', conf.DEFAULT_SYNC_MACHINE_IP)
        self.remote_port = kwargs.get('remote_port', conf.DEFAULT_SYNC_MACHINE_PORT)
        self.auth_headers = kwargs.get('auth_headers', {})
        assert isinstance(self.auth_headers, dict)

    def _is_path_in_sync_dir(self, save_path):
        return save_path.startswith(self.local_sync_dir)

    def _get_local_save_path(self, path, file_name):
        return os.path.join(self.local_sync_dir, path, file_name)

    def _write_to_fs(self, sync_object):
        """
        Fetch and write a remote file to local filesystem.
        """
        result = shutil_dl.download(
            sync_object['write_path'],
            sync_object['file_url'],
            headers=self.auth_headers
        )
        if result.success:
            # mark pull notif as succeeded.
            logger.log("Synced file: {}".format(sync_object))
            pass
        else:
            logger.log("Sync failed: {}; Error: {}".format(sync_object, result.error_message or result.not_ok_reason))

    def sync_to_local(self, fsobject_name, fsobject_url, dir_path, is_dir=False):
        """
        fsobject_name - filesystem object (file/dir) name
        fsobject_url - url of object to get from other device
        dir_path - path of file/dir relative to sync dir
            Eg.: If sync dir is /tmp/abc
                * In case object is directly under the sync dir,
                  then dir_path will be ''
                * If in a sub dir, say '/tmp/abc/xyz/myfile.txt', then it will be 'xyz'
                * If in sub dir nested under other dirs like: /tmp/abc/xyz/pqr/mno/myfile.txt
                    then it will be 'xyz/pqr/mno'
                Basically relative path convention, considering sync dir to be root.
        """
        if not self._is_path_in_sync_dir(dir_path):
            raise Exception("save_path outside sync dir")

        write_path = self._get_local_save_path(fsobject_name, dir_path)
        if not os.path.exists(write_path):
            # Create local dir if save path doesn't exist.
            os.makedirs(write_path)
        if not is_dir:
            # If sync object is a dir, then work here is done above.
            self._write_to_fs(write_path, fsobject_url)
        print("Synced {} {}/{}".format(['file', 'folder'][is_dir], dir_path, fsobject_name))

    def notify_remotes(self, sync_data):
        """
        To notify the other machine that they need to pull the FS changes on this machine.

        This simply POSTs the details of the filesystem event that needs to be synced
        to the other machine, so that it can call its TheTransporter.sync_to_local to fetch
        that file from this machine. Little hacky for the short amount of time I have
        available, but this struck me as good usage of requests module.. Sockets transfer
        implementation might be added if I have enough time.

        Notification will be tried 3 times

        sync_data: {
                'change_type': event.event_type,
                'source_path': event.src_path,
                'dest_path': getattr(event, 'dest_path'),
                'is_dir': event.is_directory,
                'time': cur_time,
                # 'file_hash': '',
            }
        """
        notif_endpoint = "http://{ip}:{port}".format(self.remote_ip, self.remote_port)
        notif_posted = False
        retry_ctr = 0
        while not notif_posted and retry_ctr < 3:
            notif_resp = requests.post(notif_endpoint, json=sync_data, headers=self.auth_headers)
            notif_posted = notif_resp.ok
            retry_ctr += 1
        return notif_posted
