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
import time
from multiprocessing import Process, Queue

import click
import requests
from expiringdict import ExpiringDict
from watchdog import events

# import accountant
import conf
import observer
import shutil_dl
import web_server
from utils import logger

MAX_RECENTLY_SYNCED_IGNORE_TIME = 5

__author__ = "Ashish Kumar (ashish26kr91@gmail.com)"
__version__ = "0.0.1"


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

    def __init__(self, *args, **kwargs):
        # self.sync_dir = kwargs.pop('sync_dir')
        self.local_sync_dir = kwargs.get('local_sync_dir', conf.DEFAULT_LOCAL_SYNC_DIR)
        self.remote_ip = kwargs.get('remote_ip', conf.DEFAULT_SYNC_MACHINE_IP)
        self.remote_port = kwargs.get('remote_port', conf.DEFAULT_SYNC_MACHINE_PORT)
        self.auth_headers = kwargs.get('auth_headers', {})
        self.remote_endpoint = "http://{ip}:{port}".format(ip=self.remote_ip, port=self.remote_port)
        self.recently_saved = ExpiringDict(max_len=1000, max_age_seconds=10)
        self.ip_queue = kwargs.get('ip_queue')
        assert isinstance(self.auth_headers, dict)

    def _is_path_in_sync_dir(self, save_path):
        return save_path.startswith(self.local_sync_dir)

    def _get_local_save_path(self, relative_file_path):
        # return os.path.join(self.local_sync_dir, relative_file_path)
        return os.path.join(os.getcwd(), relative_file_path)

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
        logger.info("SYNCER notifying remote")
        while not notif_posted and retry_ctr < 3:
            req = requests.Request(
                method='REQSYNC',
                url=self.remote_endpoint,
                json=sync_data,
                headers=self.auth_headers
            )
            resp = requests.session().send(req.prepare())
            notif_posted = resp.ok
            retry_ctr += 1
            time.sleep(retry_ctr)
            if notif_posted:
                logger.info("Notified; REQSYNC response: \n{}".format(resp.text))
        return notif_posted

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
        if errors:
            return False
        return True

    def _write_to_IPQ(self, data):
        q_data = {data['src_path']: time.time() + MAX_RECENTLY_SYNCED_IGNORE_TIME}
        self.ip_queue.put(
            q_data
        )

    def remote_action(self, data):
        """
        Fetch and write a remote file to local filesystem.
        """
        url = os.path.join(self.remote_endpoint, data['src_path'][1:])

        result = shutil_dl.download(
            self._get_local_save_path(data['src_path'][1:]),
            url,
            headers=self.auth_headers
        )

        if result.success:
            self.recently_saved[data['src_path']] = data
            # TODO call accountant to mark pull notif as succeeded.
            logger.info("Synced file: {}".format(data))
            pass
        else:
            logger.warning("Sync failed: {}; Error: {}".format(data, result.error_message or result.not_ok_reason))

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
                logger.error("\nlocal_action: Error in deleting {};\nexception: {}".format(src_path, ose.args))
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
                logger.error("\nlocal_action: Error in moving {};\nexception: {}".format(
                    (src_path, dest_path), ose.args))
                pass

    def local_action(self, data):
        """
        No need to contact remote machine. Only do modifications in
        local filesystem - when even type is `deleted` or `moved`
        """
        src = data['src_path'][1:]
        dst = data['dest_path'][1:]
        if data['change_type'] == events.EVENT_TYPE_DELETED:
            self._delete(src, data['is_dir'])
        elif data['change_type'] == events.EVENT_TYPE_MOVED:
            self._move(src, dst, data['is_dir'])
        else:
            logger.warning("\nlocal_action NOT CAUGHT type:'{}'".format(data['change_type']))

    def handle_sync_push(self, notif_data):
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

        self._write_to_IPQ(notif_data)

        if self._needs_fetch(notif_data['change_type']):
            self.remote_action(notif_data)  # Need to fetch file system objects from other machine
        else:
            self.local_action(notif_data)  # Need to only modify local filesystem
        return []


@click.command()
@click.option('--syncdir', '-d', type=click.Path(exists=True, file_okay=False, writable=True),
              help='Directory to watch.')
@click.option('--recursive', '-r', is_flag=True, help='Watch directories recursively.')
@click.option('--server_port', '-p', type=click.INT, help='Server port.')
@click.option('--remote_ip', '-ri', help='Remote machine IP.')
@click.option('--remote_port', '-rp', type=click.INT, help='Remote machine port.')
def run(syncdir, recursive, server_port, remote_ip, remote_port):
    if not (syncdir or recursive or server_port or remote_ip or remote_port):
        print(click.get_current_context().get_help())
        sys.exit()

    ip_queue = Queue()  # inter process queue for skipping just synced objects
    # getting reported by observers on both sides in an infinite loop.

    server_port = server_port or conf.WEBSERVER_PORT
    serve_on = ('0.0.0.0', server_port)
    recursive = recursive or conf.WATCH_RECURSIVE
    syncer = Syncer(
        ip_queue=ip_queue,
        local_sync_dir=syncdir,
        remote_ip=remote_ip or conf.DEFAULT_SYNC_MACHINE_IP,
        remote_port=remote_port or conf.DEFAULT_SYNC_MACHINE_PORT,
        auth_headers={},  # TODO - when work flow is finalized, add auth here
                          # and its check in transporter module
    )
    print("Using configuration: \n")
    print("Remote: {}".format(syncer.remote_endpoint))
    print("Sync dir: {}".format(syncer.local_sync_dir))
    print("Watch recursive: {}".format(recursive))
    print("Server PORT: {}".format(server_port))

    # accountant = accountant.TheAccountant()
    observer_process = Process(
        target=observer.watch_filesystem,
        args=(),
        kwargs=dict(
            ip_queue=ip_queue,
            watch_dir=syncdir,
            notify=True,
            recursive=recursive,
            syncer=syncer,
            daemon=True,
            # accountant=accountant,
        )
    )
    observer_process.start()

    webserver_process = Process(
        target=web_server.run_server,
        args=(),
        kwargs=dict(
            ip_queue=ip_queue,
            serve_on=serve_on,
            serve_dir=syncdir,
            send_ack=True,
            syncer=syncer,
            # accountant=accountant,
        )
    )
    webserver_process.start()

    observer_process.join()
    webserver_process.join()

if __name__ == "__main__":
    run()
