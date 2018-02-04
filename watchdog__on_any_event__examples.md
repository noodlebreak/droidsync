## FILES

CREATED
	on_any_event: ('created', '/tmp/abc', False)
MODIFIED
	on_any_event: ('modified', '/tmp/abc', False)
MOVED
	on_any_event: ('moved', '/tmp/abc', '/tmp/abdf', False)
MOVED OUT OF WATCHED DIR
    dfdfd.fdfd was moved to /tmp/
    on_any_event: ('deleted', '/tmp/www/dfdfd.fdfd', False)

DELETED
	on_any_event: ('deleted', '/tmp/www/dfdfd', False)


## DIRECTORIES

CREATED
	on_any_event: ('created', '/tmp/xxx', True)
MODIFIED
	on_any_event: ('modified', '/tmp/xxx', True)
DELETED
    on_any_event: ('deleted', '/tmp/www/xyz', True)
MOVED
	on_any_event: ('moved', '/tmp/xxx', '/tmp/vvv', True)
MOVED OUT OF WATCHED DIR
    ppp was moved to /tmp/
    on_any_event: ('deleted', '/tmp/www/ppp', True)
