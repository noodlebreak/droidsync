"""
This is faster than chunked response saving.
    Credit: https://stackoverflow.com/a/39217788/1114457
100MB takes ~58s on 7Mbps connection.

BUT keep this in mind:
    http://docs.python-requests.org/en/master/user/quickstart/#raw-response-content
"""

import sys
import shutil
import time

import requests
from utils import ResponseSaved


def download(file_path, url="https://speed.hetzner.de/100MB.bin", silent=False, headers={}):
    if not (url or silent):
        raise Exception("File URL not given")
    elif silent and not url:
        result = ResponseSaved(error_message="URL is empty")

    local_filename = file_path if file_path else url.split('/')[-1]
    start = time.time()
    r = requests.get(url, headers=headers, stream=True)

    if not r.ok:
        result = ResponseSaved(not_ok_reason=r.reason)
    import os; print("Current dir: {}".format(os.getcwd()))
    with open(local_filename, 'wb') as local_file:
        shutil.copyfileobj(r.raw, local_file)

    time_taken = time.time() - start
    print("URL:{}; Time taken: {}".format(url, time_taken))

    result = ResponseSaved(saved_to=local_filename, time_taken=time_taken)
    return result

if __name__ == '__main__':
    file_path = sys.argv[1]
    if file_path:
        download(file_path)
    else:
        download()
