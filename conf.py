import ConfigParser
conf = ConfigParser.SafeConfigParser({'RESPONSE_READ_CHUNK_SIZE': 4096, 'sync_dir': '/tmp/sstest'})
conf.read('conf.ini')

CHUNK_SIZE = conf.get('transport', 'RESPONSE_READ_CHUNK_SIZE')

DEFAULT_LOCAL_SYNC_DIR = conf.get('dirconfig', 'sync_dir')

DEFAULT_SYNC_MACHINE_IP = conf.get('transport', 'sync_machine_ip')

DEFAULT_SYNC_MACHINE_PORT = conf.get('transport', 'sync_machine_port')

EXCHANGE_SERVER_HOST = conf.get('transport', 'exchange_server_host')

EXCHANGE_SERVER_POST = conf.get('transport', 'exchange_server_port')
