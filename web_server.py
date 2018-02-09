import argparse
import datetime
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

from utils import logger


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler, SimpleHTTPRequestHandler):
    """
    Basic HTTP webserver request handler with custom request REQSYNC method handling.
    https://stackoverflow.com/questions/31371166/reading-json-from-simplehttpserver-post-data

    BaseHTTPRequestHandler - for implementing custom request method handler.
    SimpleHTTPRequestHandler - for using its default GET handler which is well polished.
    """

    def _process_sync_request(self, data):
        """For processing a remote sync request.
        >> Trigger sync
        >> Record transaction in DB
        >> sync-ack for confirming a successful sync or log failure
        """
        # Call transporter to push this event's notification to remote
        # Also, not creating a new thread, because this webserver handles each
        # client request in a separate thread already, so no worries of blocking other requests.
        # TODO Record this event in local DB for syn-ack

        return self.server.syncer.handle_sync_push(data)

    def do_REQSYNC(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(self.data_string)

        # Now here we take action on the sync notification
        # We call the syncer's action method which will decide
        # whether to fetch the sync file (create/update) or just do local mod (delete/moved)

        logger.info("WEBSERVER: RECEIVED REQSYNC: {}\n".format(data))
        errors = self._process_sync_request(data)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        resp_data = {'errors': errors}
        logger.info("WEBSERVER: PROCESSED REQSYNC; errors: {}\n##############################\n".format(errors))
        if self.server.send_ack:
            # to notify notifier when the notification was processed.
            resp_data['ack'] = time.time()
        else:
            # Return the data received
            resp_data['data'] = data
        self.wfile.write(json.dumps(resp_data))


class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

    def __init__(self, server_address, RequestHandlerClass, *args, **kwargs):
        self.ip_queue = kwargs.pop('ip_queue', None)
        self.send_ack = kwargs.pop('send_ack', None)
        self.syncer = kwargs.pop('syncer', None)
        self.accountant = kwargs.pop('accountant')
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)


def run_server(ip_queue=None, serve_on=('0.0.0.0', 8000), serve_dir='.', send_ack=True,
               syncer=None, accountant=None):
    os.chdir(serve_dir)  # https://stackoverflow.com/a/39801780/1114457
    server = ThreadedHTTPServer(
        serve_on,
        RequestHandler,
        ip_queue=ip_queue,
        send_ack=send_ack,
        syncer=syncer,
        accountant=accountant
    )
    logger.info("\n>> Started web server; Use <Ctrl-C> to stop \n>> Serving on : {}".format(serve_on))
    logger.info(">> Started web server, use <Ctrl-C> to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n\nShutting down... Good bye!\n")
        logger.info("\n\nShutting down... Good bye!\n")
        server.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', default=8000, type=int)
    parser.add_argument('--dir', '-d', default=os.getcwd(), type=str)
    args = parser.parse_args()

    server_address = ('0.0.0.0', args.port)
    run_server(server_address, args.dir)
