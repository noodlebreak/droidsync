import sys
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog import events


class FSChangesHandler(FileSystemEventHandler):
    """
    Notifies of any changes in the file system in the specified
    sync directory.
    """
    skip = {}  # events with same timestamp and file path
    # will be skipped if already in this

    def __init__(self, *args, **kwargs):
        self.notify = kwargs.pop('notify')
        self.transporter = kwargs.pop('transporter')
        super(FSChangesHandler, self).__init__(*args, **kwargs)

    def push_event(self, data):
        new_push_thread = threading.Thread(target=self.transporter.notify_remotes, args=(data, ))
        new_accountant_thread = threading.Thread(target=self.accountant.add_push_event, args=(data, ))
        new_push_thread.start()
        new_accountant_thread.start()

    def on_any_event(self, event):
        cur_time = int(time.time())
        if cur_time in self.skip and event.src_path in self.skip.get(cur_time):
            return
        elif event.is_directory and event.event_type == events.EVENT_TYPE_MODIFIED:
            return
        else:
            src_path = event.dest_path if event.event_type == events.EVENT_TYPE_MOVED else event.src_path
            if cur_time in self.skip:
                self.skip[cur_time].append(src_path)
            else:
                self.skip[cur_time] = [src_path]
        if self.notify:
            event_detail = {
                'change_type': event.event_type,
                'source_path': event.src_path,
                'dest_path': getattr(event, 'dest_path'),
                'is_dir': event.is_directory,
                'time': cur_time,
                # 'file_hash': '',
            }
            self.push_event(event_detail)
        else:
            print "Event: {}".format(event.key)
        # delete old keys so that self.skip doesn't bloat up
        # for key in self.skip:
        #     if cur_time - key > 60:
        #         self.skip.pop(key)


def watch_filesystem(watch_dir, notify=False, transporter=None, accountant=None):
    """
    Start off a watchdog oberver thread to watch filesystem event
    changes. Also take actions accordingly.

    watch_dir: Directory to watch
    notify: Whether or not any action should be taken if an event occurs.
    """
    event_handler = FSChangesHandler(notify=notify, transporter=transporter, accountant=accountant)
    observer = Observer()
    observer.schedule(event_handler, path=watch_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    watch_dir = '.'
    if len(sys.argv) > 1:
        watch_dir = sys.argv[1]
    print("Watching: {}".format(watch_dir))
    watch_filesystem(watch_dir)
