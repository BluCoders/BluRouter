#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Requires python-ipaddr """
import ipaddr
import atexit
import sys
import time

from config import *

from Daemon import Daemon
from RouterTimeds    import RouterTimeds    # Propagate our routes
from RouterNeighbors import RouterNeighbors # Set up and time out neighbors
from RouterSockets   import RouterSockets   # get messages from the socket
# TODO: RouterLocal code moved into Router
from RouterLocal     import RouterLocal     # Administer the kernel routing table
from Router          import Router          # Filter the added routes for security, keep track of routes


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
        # Set up logging
        if foreground:
            log = LogStdout()
        else:
            log = LogSyslog(syslog_facil, syslog_pri)
        # Localrouter is our connection to the kernel routing table.
        # TODO: make it poll that table and fight changes

        localrouter = RouterLocal    (log, endian)
        # router(localrouter, timed)
        router      = Router         (log, localrouter, newip_sendnets, PROTECTED_NETS, ALLOW_RANGES)
        # neigh (router)
        neigh       = RouterNeighbors(log, router,      UDP_IP,         max_ttl)
        # socks (neigh)
        socks       = RouterSockets  (log, neigh,       65536,          UDP_BROADCAST,  UDP_PORT,    UDP_SUBNET, select_timeout)
        # timed (socks)
        timed       = RouterTimeds   (log, socks,       routesfile,     hello_interval, hello_timeout)

        router.settimed(timed)
        atexit.register(unload, router)

        # Sensible to assume 2*select timeout + 1 second as
        # maximum time difference per round
        maxdiff = select_timeout*2+1
        ts = None

        while True:
            oldts = ts
            ts = time.time()
            if oldts:
                diff = ts-oldts
                if diff < 0 or diff > maxdiff:
                    log.log("Jumped in time by at least " +str(diff)+" seconds")
                    timed.compensate(diff)
                    neigh.compensate(diff)
                #else:
                    #log.log("Normal time difference: "+str(diff)+" seconds")
            timed.run(ts)
            neigh.run(ts)
            socks.select()

globalscheck([
    'UDP_IP',        'UDP_SUBNET',     'UDP_BROADCAST',
    'UDP_PORT',      'ALLOW_RANGES',   'PROTECTED_NETS',
    'syslog_pri',    'syslog_facil',   'routesfile',
    'pidfile',       'endian',         'hello_interval',
    'hello_timeout', 'select_timeout', 'max_ttl',
    'newip_sendnets'
])

# ipaddr-ize PROTECTED_NETS, ALLOW_RANGES
PROTECTED_NETS = [ipaddr.IPv4Network(x) for x in PROTECTED_NETS]
ALLOW_RANGES   = [ipaddr.IPv4Network(x) for x in ALLOW_RANGES]
UDP_SUBNET     = ipaddr.IPv4Network(UDP_SUBNET)


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
