#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Requires python-ipaddr """
import ipaddr
import atexit
import sys
from daemon import Daemon

from config import *

from RouterTimeds    import RouterTimeds
from RouterNeighbors import RouterNeighbors
from RouterSockets   import RouterSockets
from RouterLocal     import RouterLocal
from Router          import Router


# TODO:
# Possibility of binding a neighbor timeout to a callback.
# This makes it possible to profile the uptime of the network.

# PROTOCOL DOCUMENTATION
#       Runs on broadcast 192.168.0.255 port 12345
#       hello: Gave it a type to be able to do other stuff with protocol later :)
#               ttl: TTL
#               nets: SUBNETS
def globalscheck(x):
    for y in x:
        if not y in globals():
            print "Please define "+y+" in config.py"
            sys.exit(1)

def diff(a, b):
    b = set(b)
    # Things that are in a only
    return [aa for aa in a if aa not in b]

class LogStdout():
    def __init__(self):
        return
    def log(self, x):
        print "Log: "+str(x)

class LogSyslog():
    def __init__(self, fac, priority, idn="BluRouter"):
        syslog.openlog(facility=fac, ident=idn)
        self.pri = priority
    def log(self, x):
        syslog.syslog(self.pri, x)

def unload(router):
    router.shutdown()


class MyDaemon(Daemon):
    def run(self, foreground=False):
        if foreground:
            log = LogStdout()
        else:
            log = LogSyslog(syslog_facil, syslog_pri)
        localrouter = RouterLocal(log, endian)
        router      = Router(localrouter, log)
        # max ttl to accept from other hosts
        neigh       = RouterNeighbors(log, router, UDP_IP)
        # Max buf size for a single packet. Will limit available routes
        socks       = RouterSockets(65536, neigh, log, UDP_BROADCAST, UDP_PORT, UDP_SUBNET, select_timeout)
        # file with routes separated by newline
        timed       = RouterTimeds(routesfile, log, socks, neigh, hello_interval, hello_timeout)
        router.settimed(timed)

        atexit.register(unload, router)
        while True:
            timed.run()
            socks.select()

globalscheck([
    'UDP_IP', 'UDP_SUBNET', 'UDP_BROADCAST', 'UDP_PORT', 'ALLOW_RANGES', 'PROTECTED_NETS',
    'syslog_pri', 'syslog_facil', 'routesfile', 'pidfile', 'endian',
    'hello_interval', 'hello_timeout', 'select_timeout', 'max_ttl', 'newip_sendnets'
])

# ipaddr-ize PROTECTED_NETS, ALLOW_RANGES
PROTECTED_NETS = [ipaddr.IPv4Network(x) for x in PROTECTED_NETS]
ALLOW_RANGES   = [ipaddr.IPv4Network(x) for x in ALLOW_RANGES]
UDP_SUBNET = ipaddr.IPv4Network(UDP_SUBNET)


daemon = MyDaemon(pidfile)
if len(sys.argv) == 2:
    if 'start' == sys.argv[1]:
        daemon.start()
    elif 'stop' == sys.argv[1]:
        daemon.stop()
    elif 'restart' == sys.argv[1]:
        daemon.restart()
    elif 'test' == sys.argv[1]:
        daemon.run(True)
    else:
        print "Unknown command"
        sys.exit(2)
    sys.exit(0)
else:
    print "usage: %s start|stop|restart|test" % sys.argv[0]
    sys.exit(2)
