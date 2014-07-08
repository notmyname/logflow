#!/usr/bin/env python

import re
import sys

import pygraphviz as pgv

try:
    filename = sys.argv[1]
except IndexError:
    print >>sys.stderr, 'Usage: %s <filename>' % sys.argv[0]
    sys.exit(1)

storage_log_pattern = r'''
.*?  # remote_addr
\s-\s-\s
\[.*?\]  # datetime
\s
"(.*?)\s.*?"  # req method and path
\s
(\d\d\d)  # status int
\s
.*?  # content length
\s
".*?"  # referrer
\s
".*?"  # txn id
\s
"(.*?)\s(\d*?)"  # user agent
\s
.*?  # transaction time
\s
(\d\d\d\d)  # server pid
'''

auth_pattern = r'''
User:\s
.*?  # user id
uses\stoken\s
.*?\s
\(trans_id .*?\)
'''

storage_log_regex = re.compile(storage_log_pattern, re.VERBOSE | re.MULTILINE)
auth_pattern_regex = re.compile(auth_pattern, re.VERBOSE | re.MULTILINE)

st_map = {
    'obj-server': 'object-server'
}

g = pgv.AGraph(strict=False, directed=True)
servers_found = set()

with open(filename, 'rb') as f:
    for rawline in f:
        line = rawline.strip()[16:]  # pull off syslog timestamp
        server_name, line = line.split(' ', 1)
        server_type, line = line.split(': ', 1)
        server_type = st_map.get(server_type.strip(), server_type.strip())
        m = storage_log_regex.match(line)
        if m:
            (method, status, source, source_pid, server_pid) = m.groups()
            source = st_map.get(source, source)
            source = '%s %s' % (source, source_pid)
            server_type = '%s %s' %(server_type, server_pid)
            g.add_edge(source, server_type, label='%s (%s)' % (method, status))
        else:
            m = auth_pattern_regex.match(line)
            if m:
                g.add_edge('proxy-server', 'auth')
                g.add_edge('auth', 'proxy-server')

g.layout(prog='dot')
g.draw('out.png')
