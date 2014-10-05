#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Requires python-ipaddr """
import atexit       # script exit handlers
import sys          # sys.exit, sys.argv
import time         # time.time()
import getopt       # getopt.getopt()

from inc.CFG             import CFG             # Configuration file reader
from inc.Daemon          import Daemon          # Daemon tool
from inc.RouterTimeds    import RouterTimeds    # Propagate our routes
from inc.RouterNeighbors import RouterNeighbors # Set up and time out neighbors
from inc.RouterSockets   import RouterSockets   # get messages from the socket
# TODO: RouterLocal code moved into Router
from inc.RouterLocal     import RouterLocal     # Administer the kernel routing table
from inc.Router          import Router          # Filter the added routes for security, keep track of routes


# TODO:
# Possibility of binding a neighbor timeout to a callback.
# This makes it possible to profile the uptime of the network.

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
    def run(self, conf, foreground=False):
        # Set up logging
        if foreground:
            log = LogStdout()
        else:
            log = LogSyslog(syslog_facil, syslog_pri)
        # Localrouter is our connection to the kernel routing table.
        # TODO: make it poll that table and fight changes

        localrouter = RouterLocal    (log, conf)
        router      = Router         (log, localrouter, conf)
        neigh       = RouterNeighbors(log, router,      conf)
        socks       = RouterSockets  (log, neigh,       65536, conf)
        timed       = RouterTimeds   (log, socks,       conf)

        router.settimed(timed)
        atexit.register(unload, router)

        # Sensible to assume 2*select timeout + 1 second as
        # maximum time difference per round
        maxdiff = conf["select_timeout"]*2+1
        ts = None

        while True:
            oldts = ts
            ts = time.time()
            if oldts:
                diff = ts-oldts
                if diff < 0 or diff > maxdiff:
                    log.log("Jumped in time by " +str(diff)+" seconds")
                    timed.compensate(diff)
                    neigh.compensate(diff)
            timed.run(ts)
            neigh.run(ts)
            socks.select()

def usage():
    print "USAGE: "+sys.argv[0]+" [-c/--config config.ini] start|stop|restart|test"

try:
    opts, args = getopt.getopt(sys.argv[1:], "c:", ["config="])
    if args[0] not in ["start", "stop", "restart", "test"]:
        raise Exception('')
    action = args[0]
except Exception:
    usage()
    sys.exit(2)

try:
    configfile = opts[0][1]
except Exception:
    configfile = 'config.ini'

cfg  = CFG()
conf = cfg.read(configfile)

daemon = MyDaemon(conf["pidfile"])

if   action == 'start':
    daemon.start(conf)
elif action == 'stop':
    daemon.stop()
elif action == 'restart':
    daemon.restart(conf)
elif action == 'test':
    daemon.run(conf, True)
