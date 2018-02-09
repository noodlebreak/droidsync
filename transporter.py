import datetime
import os
import time

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
        self.notif_endpoint = "http://{ip}:{port}".format(self.remote_ip, self.remote_port)
        assert isinstance(self.auth_headers, dict)

    def _is_path_in_sync_dir(self, save_path):
        return save_path.startswith(self.local_sync_dir)

    def _get_local_save_path(self, path, file_name):
        return os.path.join(self.local_sync_dir, path, file_name)

    def fetch_remote(self, data):
        """
        Fetch and write a remote file to local filesystem.
        """
        url = os.path.join(self.notif_endpoint, data['src_path'])
        result = shutil_dl.download(
            data['src_path'],
            url,
            headers=self.auth_headers
        )
        if result.success:
            # TODO call accountant to mark pull notif as succeeded.
            logger.log("Synced file: {}".format(data))
            pass
        else:
            logger.log("Sync failed: {}; Error: {}".format(data, result.error_message or result.not_ok_reason))

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
        notif_posted = False
        retry_ctr = 0
        while not notif_posted and retry_ctr < 3:
            req = requests.Request(
                method='REQSYNC',
                url=self.notif_endpoint,
                json=sync_data,
                headers=self.auth_headers
            )
            resp = requests.session().send(req.prepare())
            notif_posted = resp.ok
            retry_ctr += 1
            time.sleep(retry_ctr)
        return notif_posted
