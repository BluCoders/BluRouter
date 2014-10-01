#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Requires python-ipaddr """
import subprocess
import ipaddr
import time
import atexit
import syslog
import sys
from daemon import Daemon

from config import *

from RouterSockets import RouterSockets
from Router        import Router


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

# Uses log, socks, neigh
class RouterTimeds:
    """
    RouterTimeds contains the code we run mostly every second.
    It is responsible for:
     - propagating the routes file (sending hello)
     - calling RouterNeighbors run function to time out neighbors
    """
    myroutes = []
    def __init__(self, myroutefile, log, socks, neigh):
        self.routefile = myroutefile
        self.log = log
        self.socks = socks
        self.neigh = neigh
        self.last_hello = 0

    def readroutes(self, ts):
        try:
            f = open(self.routefile, "r")
            l = sorted([ipaddr.IPv4Network(i.strip()) for i in f.readlines()])
            f.close()
        except:
            self.log.log("readroutes: "+self.routefile+" is trapped in another dimension..")
            return

        if l != self.myroutes:
            self.log.log("readroutes: New routes found in the routefile!")
            self.myroutes = l
            self.hello()
            self.last_hello = ts

    def run(self):
        ts = self.ts()
        self.readroutes(ts)
        self.neigh.run()

        if (ts-self.last_hello) >= hello_interval:
            self.hello()
            self.last_hello = ts
    def hello(self):
        """When this is called, it is time to broadcast our existence"""
        self.socks.out({'type':'hello', 'ttl':hello_timeout, 'nets':[str(x) for x in self.myroutes]})

    def ts(self):
        return time.time()

# Uses log, router
class RouterNeighbors():
    timer = {}
    def __init__(self, log, router):
        self.log = log
        self.router = router

    def run(self):
        """ Remove expired neighbors """
        ts = self.ts()
        delete = []
        for ip in self.timer:
            until = self.timer[ip]
            if until < ts:
                delete.append(ip)

        for ip in delete:
            self.log.log("RouterNeighbors.run: ip "+str(ip)+" expired")
            # TODO: optional callback
            self.router.delroutes(ip)
            del self.timer[ip]


    def hello(self, addr, data):
        try:
            ttl = int(data['ttl'])
        except:
            self.log.log("RouterNeighbors.hello: "+str(addr)+", you sent me an Invalid/nonexistant 'ttl' field, stop messing with me!")
            return
        try:
            # Code to verify and make it a list of strings
            netstmp = data['nets']
            nets = []
            for net in netstmp:
                nets.append(ipaddr.IPv4Network(net))
        except:
            self.log.log("RouterNeighbors.hello: "+str(addr)+" sent me an invalid/nonexistant 'nets' field. Could someone please tell me why?!")
            return

        if addr == UDP_IP:
            return
        if ttl <= 0:
            # Packet immediately times out on 0 or negative numbers
            self.log.log("RouterNeighbors.hello: "+str(addr)+" might want to update their ttl to something larger than "+str(ttl)+" seconds.")
            return
        if ttl > max_ttl:
            ttl = max_ttl

        until = ttl+self.ts()
        self.timer[addr] = until
        self.router.setroutes(addr, nets)
    def ts(self):
        return time.time()

# Uses log
class RouterLocal():
    table = {}
    def __init__(self, log):
        self.get_kernel_table()
        self.log = log

    def get_kernel_table(self):
        f = open("/proc/net/route", "r")
        lines = f.readlines()
        f.close()
        newl = []
        for l in lines:
            newl.append(l.strip().split("\t"))
        idx = [i.strip() for i in newl.pop(0)]
        for l in newl:
            new = {}
            for k,v in enumerate(l):
                new[idx[k]] = v
            dst = ipaddr.IPv4Network(self.dehex(new['Destination'])+"/"+self.dehex(new['Mask']))
            gw  = ipaddr.IPv4Address(self.dehex(new['Gateway']))
            self.table[dst] = gw
    
    def dehex(self, ip):
        tmp = [str(int(ip[i:i+2], 16)) for i in range(0, len(ip), 2)]
        if endian == 0:
            tmp = reversed(tmp)
        return ".".join(list(tmp))

    def route_add(self, route, gw):
        argv = ["route", "add", "-net", str(route), "gw", str(gw)]
        ret = subprocess.call(argv)
        self.log.log("route_add: "+" ".join(argv)+": "+str(ret))
        if ret != 0:
            return False
        else:
            return True

    def route_del(self, route, gw):
        argv = ["route", "del", "-net", str(route), "gw", str(gw)]
        ret = subprocess.call(argv)
        self.log.log("route_del: "+" ".join(argv)+": "+str(ret))
        if ret != 0:
            return False
        else:
            return True


    def add(self, route, gw):
        if route in self.table:
            self.log.log("BIG HUGE WARNING: There is a route already present blocking "+str(route)+" from being added!")
            return
        if self.route_add(route,gw):
            self.table[route] = gw
    
    def delete(self, route, gw):
        if not route in self.table:
            self.log.log("BIG HUGE WARNING: There route for "+str(route)+" that we wanted to delete is not present!")
            return
        if self.route_del(route,gw):
            del self.table[route]

    def add_multi(self, routes, gw):
        for route in routes:
            self.add(route, gw)
    def delete_multi(self, routes, gw):
        for route in routes:
            self.delete(route, gw)
        return

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
        localrouter = RouterLocal(log)
        router      = Router(localrouter, log)
        # max ttl to accept from other hosts
        neigh       = RouterNeighbors(log, router)
        # Max buf size for a single packet. Will limit available routes
        socks       = RouterSockets(65536, neigh, log, UDP_BROADCAST, UDP_PORT, UDP_SUBNET, select_timeout)
        # file with routes separated by newline
        timed       = RouterTimeds(routesfile, log, socks, neigh)
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
