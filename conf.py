import ConfigParser
conf = ConfigParser.SafeConfigParser({'RESPONSE_READ_CHUNK_SIZE': 4096, 'sync_dir': '/tmp/sstest'})
conf.read('conf.ini')

# Transport settings
DEFAULT_SYNC_MACHINE_IP = conf.get('transport', 'sync_machine_ip')
DEFAULT_SYNC_MACHINE_PORT = conf.get('transport', 'sync_machine_port')
# EXCHANGE_SERVER_HOST = conf.get('transport', 'exchange_server_host')
# EXCHANGE_SERVER_POST = conf.get('transport', 'exchange_server_port')

# Sync settings
DEFAULT_LOCAL_SYNC_DIR = conf.get('dirconfig', 'sync_dir')
WATCH_RECURSIVE = conf.get('dirconfig', 'watch_recursive') == 'true'
AUTO_CREATE_SYNC_DIR = conf.get('dirconfig', 'auto_create_sync_dir') == 'true'

# Web server settings
WEBSERVER_PORT = int(conf.get('web_server', 'port'))
