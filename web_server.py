import argparse
import json
import os
import sys
import time

try:
    # Python3
    from http.server import SimpleHTTPRequestHandler
    import http.server as BaseHTTPServer
    import socketserver as SocketServer
except ImportError:
    # Python 2
    import BaseHTTPServer
    import SocketServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

import simplesync

_ROOT = os.path.abspath(os.path.dirname(__file__))


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler, SimpleHTTPRequestHandler):
    """
    Basic HTTP webserver request handler with custom request REQSYNC method handling.
    https://stackoverflow.com/questions/31371166/reading-json-from-simplehttpserver-post-data

    BaseHTTPRequestHandler - for implementing custom request method handler.
    SimpleHTTPRequestHandler - for using its default GET handler which is well polished.
    """

    # def _set_headers(self):
    #     self.send_response(200)
    #     self.send_header('Content-type', 'text/html')
    #     self.end_headers()

    # def do_GET(self, *args, **kwargs):
    #     SimpleHTTPRequestHandler.base_path = self.base_path
    #     SimpleHTTPRequestHandler.do_GET(self, *args, **kwargs)
    # self._set_headers()
    # f = open("index.html", "r")
    # self.wfile.write(f.read())

    # def do_HEAD(self):
    #     self._set_headers()

    # def do_POST(self):
    def do_REQSYNC(self):
        # self._set_headers()
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(self.data_string)

        # Now here we take action on the sync notification
        # We call the syncer's action method which will decide
        # whether to fetch the sync file (create/update) or just do local mod (delete/moved)

        print "POST: {}".format(data)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if self.server.send_ack:
            ack = dict(ack=time.time())  # to notify notifier when the notification was processed.
            self.wfile.write(json.dumps(ack))
        else:
            # Return the data received
            self.wfile.write(json.dumps(data))


class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

    def __init__(self, server_address, RequestHandlerClass, *args, **kwargs):
        self.send_ack = kwargs['send_ack']
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)


def run_server(serve_on=('0.0.0.0', 8000), serve_dir='.', send_ack=True,
               transporter=None, accountant=None):
    os.chdir(serve_dir)  # https://stackoverflow.com/a/39801780/1114457
    server = ThreadedHTTPServer(
        serve_on,
        RequestHandler,
        send_ack=send_ack,
        transporter=transporter,
        accountant=accountant
    )
    print 'Starting server, use <Ctrl-C> to stop'
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down... Good bye!\n")
        server.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', default=8000, type=int)
    parser.add_argument('--dir', '-d', default=os.getcwd(), type=str)
    args = parser.parse_args()

    server_address = ('0.0.0.0', args.port)
    run_server(server_address, args.dir)
