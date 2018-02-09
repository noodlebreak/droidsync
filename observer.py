import datetime
import sys
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog import events

from utils import logger


class FSChangesHandler(FileSystemEventHandler):
    """
    Notifies of any changes in the file system in the specified
    sync directory.
    """

    def __init__(self, *args, **kwargs):
        self.ip_queue = kwargs.pop('ip_queue', None)
        self.notify = kwargs.pop('notify', False)
        self.syncer = kwargs.pop('syncer', None)
        self.accountant = kwargs.pop('accountant', False)
        self.skip = {}  # events with same timestamp and file path
        # will be skipped if already in this
        super(FSChangesHandler, self).__init__(*args, **kwargs)

    def _is_just_synced(self, event, current_time):
        """
        just_synced: {"dir/file_or_dir": 14404440}
                     Dict of event event.src_path and expiry-timestamp
                     If current time is less than expiry time stamp (set in future)
                     then skip firing the event.
        """
        logger.info("In _is_just_synced; IPQ-empty: {}, event: {}, current_time:{}".format(
            self.ip_queue.empty(), event.key, current_time))
        just_synced = self.ip_queue.get(timeout=1) if not self.ip_queue.empty() else None
        logger.info("just_synced: {}".format(just_synced))

        event_src_path = event.src_path.replace(self.syncer.local_sync_dir, '')
        # If timestamp of the latest entry of the file in observer's
        # just_synced is more than current time skip it
        if just_synced and (event_src_path in just_synced) and (current_time < just_synced[event_src_path]):
            return True
        return False

    def push_event(self, data):
        # Call syncer to push this event's notification to remote
        new_push_thread = threading.Thread(target=self.syncer.notify_remotes, args=(data, ))
        new_push_thread.start()
        new_push_thread.join()

        # Record this event in local DB for syn-ack
        # new_accountant_thread = threading.Thread(target=self.accountant.add_push_event, args=(data, ))
        # new_accountant_thread.start()

    def _dupe_event(self, event, cur_time):
        # Skip if not more than 5s ago the latest event on same file/dir was fired
        if (event.src_path in self.skip and self.skip[event.src_path][-1] >= cur_time - 5):
            return True
        return False

    def on_any_event(self, event):
        cur_time = int(time.time())

        if self._dupe_event(event, cur_time):
            return
        elif event.is_directory and event.event_type == events.EVENT_TYPE_MODIFIED:
            return
        else:
            if self._is_just_synced(event, cur_time):
                return
            else:
                src_path = event.dest_path if event.event_type == events.EVENT_TYPE_MOVED else event.src_path
                if src_path in self.skip:
                    self.skip[src_path].append(cur_time)
                else:
                    self.skip[src_path] = [cur_time]
        if self.notify:
            src_path = event.src_path.replace(self.syncer.local_sync_dir, '')
            dest_path = getattr(event, 'dest_path', '').replace(self.syncer.local_sync_dir, '')
            event_detail = {
                'change_type': event.event_type,
                'src_path': src_path,
                'dest_path': dest_path,
                'is_dir': event.is_directory,
                'time': cur_time,
                # 'file_hash': '',
            }
            # print "Event: {}".format(event.key)
            self.push_event(event_detail)
            logger.info("OBSERVER: Pushed event: {}".format(event_detail))
        else:
            print "Event: {}".format(event.key)

    def del_old_skip_keys(self):
        pass
        # delete old keys so that self.skip doesn't bloat up
        # for key in self.skip:
        #     if cur_time - key > 60:
        #         self.skip.pop(key)


def watch_filesystem(ip_queue=None, watch_dir='', notify=False, recursive=False, syncer=None,
                     accountant=None, daemon=False):
    """
    Start off a watchdog oberver thread to watch filesystem event
    changes. Also take actions accordingly.

    watch_dir: Directory to watch
    notify: Whether or not any action should be taken if an event occurs.
    """
    event_handler = FSChangesHandler(
        ip_queue=ip_queue,
        notify=notify,
        syncer=syncer,
        accountant=accountant
    )
    observer = Observer()
    observer.schedule(event_handler, path=watch_dir, recursive=recursive)

    # If run from simplesync, this will be inside the observer_process process
    observer.daemon = daemon
    observer.start()
    print("\n>> Started observer\n>> Watching dir: {}".format(watch_dir))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    # observer.join()


if __name__ == "__main__":
    watch_dir = '.'
    if len(sys.argv) > 1:
        watch_dir = sys.argv[1]
    logger.info("Watching: {}".format(watch_dir))
    watch_filesystem(watch_dir)
