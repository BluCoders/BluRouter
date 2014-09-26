#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Requires python-ipaddr """
import subprocess
import ipaddr
import socket
import json
import time
import atexit
import syslog
import sys
from select import select
from daemon import Daemon

from config import *

# TODO:
# Possibility of binding a neighbor timeout to a callback.
# This makes it possible to profile the uptime of the network.

# hello_interval:
# Seconds between sending route advertisements
# Less = more network spam
# more = slow reaction time
# We also automatically send hello if you change routes.txt,
# which happens at least every select_timeout seconds.
hello_interval = 30

# hello_timeout:
# For the remote end: How long time can we be silent before we are assumed dead?
# setting 100 means we have a max of 100 seconds (2 lost packets) before we are assumed to be dead
# You can set this based on how intolerant to network loss you can be;
# if you do not tolerate losses,    set it between 1-2 intervals.
# If you tolerate one lost packet,  set it between 2-3 intervals.
# If you tolerate two lost packets, set it between 3-4 intervals.
hello_timeout = 100

# select_timeout:
# Give up on select every second
# This controls how often the timed code runs
# A low value is nice because:
#  - I don't think each round is very very expensive
#  - It keeps the program responsive
# This parameter controls the minimum intervals of
#  - How often we check if we need to send hello messages
#  - How often we read the routes file
#  - How often we check the neighbors for timeouts
# Try to keep it at most half of hello_interval
# Do not set it to 0 as it means infinite
select_timeout = 1

# max_ttl:
# This is how long someone can be offline without us assuming they are still online
# We will never let someone say they can be silent for more than an hour
max_ttl=3600


# PROTOCOL DOCUMENTATION
#       Runs on broadcast 192.168.0.255 port 12345
#       hello: Gave it a type to be able to do other stuff with protocol later :)
#               ttl: TTL
#               nets: SUBNETS
def cleanup_net(x):
    return str(ipaddr.IPv4Network(x))
def cleanup_addr(x):
    return str(ipaddr.IPv4Address(x))

def diff(a, b):
    b = set(b)
    # Things that are in a only
    return [aa for aa in a if aa not in b]


# Uses log, neigh
class RouterSockets:
    """RouterProtocol takes input and processes it. It also encodes stuff"""
    def __init__(self, bufsiz, neigh, log):
        self.maxin = bufsiz
        self.neigh = neigh
        self.log = log
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_BROADCAST, UDP_PORT))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def select(self):
        inr, outr, exr = select([self.sock],[],[], select_timeout)
        for s in inr:
            if s == self.sock:
                self.input()

    def route(self, addr, data):
        if data['type'] == 'hello':
            self.neigh.hello(addr[0], data)

    def input(self):
        data, src = self.sock.recvfrom(self.maxin)
        data = json.loads(data)
        self.route(src, data)

    def out(self, data):
        try:
            self.sock.sendto(json.dumps(data), (UDP_BROADCAST, UDP_PORT))
        except socket.error as e:
            self.log.log("RouterSockets.out failed: "+e.strerror)

# Uses log, socks, neigh
class RouterTimeds:
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
            l = sorted([cleanup_net(i.strip()) for i in f.readlines()])
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
        self.socks.out({'type':'hello', 'ttl':hello_timeout, 'nets':self.myroutes})

    def ts(self):
        return time.time()

# Uses log, router
class RouterNeighbors():
    timer = {}
    def __init__(self, log, router):
        self.log = log
        self.router = router

    def run(self):
        """ Remove expireds """
        ts = self.ts()
        delete = []
        for ip in self.timer:
            until = self.timer[ip]
            if until < ts:
                delete.append(ip)

        for ip in delete:
            self.log.log("RouterNeighbors.run: ip "+str(ip)+" expired")
            self.router.delroutes(ip)
            del self.timer[ip]


    def hello(self, addr, data):
        ttl = int(data['ttl'])
        nets = data['nets']
        if addr == UDP_IP:
            return
        if ttl < 0:
            return
        if ttl > max_ttl:
            ttl = max_ttl

        until = ttl+self.ts()
        self.timer[addr] = until
        self.router.setroutes(addr, nets)
    def ts(self):
        return time.time()

# Uses log
class Router:
    def __init__(self, localrouter, log):
        self.routes = {}
        self.log = log
        self.lr = localrouter
    def settimed(self, timed):
        self.timed = timed
    def shutdown(self):
        for ip in self.routes:
            self.lr.delete_multi(self.routes[ip], ip)

    def contains(self, new, routes):
        new = ipaddr.IPv4Network(new)
        for route in routes:
            if new.overlaps(ipaddr.IPv4Network(route)):
                return True
        return False

    def checkranges(self, route):
	if self.contains(route, PROTECTED_NETS):
	    return False

        route = ipaddr.IPv4Network(route)
        for net in ALLOW_RANGES:
            if ipaddr.IPv4Network(net).Contains(route):
                return True

	return False

    def busy(self, route, addr):
        # Walk all 'cept this one and check
        for ip in self.routes:
            if addr==ip:
                continue
            if self.contains(route, self.routes[ip]):
                return ip
        return False

    def owns(self, route):
        return self.contains(route, self.timed.myroutes)

    def has(self, ip, route):
        if not ip in self.routes:
            self.routes[ip] = []
            return False

    def setroutes(self, addr, routes):
        if not addr in self.routes:
            self.routes[addr] = []
        new = []
        old = self.routes[addr]
        for route in routes:
            if not self.checkranges(route):
                self.log.log(str(addr)+" tried to send us "+str(route)+", which is not in allowed ranges :/ (fix: poke hawken)")
                continue
            if self.owns(route):
                self.log.log(str(addr)+" tried to send us "+str(route)+", which is MINE!!!! (fix: poke hawken)")
                continue
            ip = self.busy(route, addr)
            if ip != False:
                self.log.log(str(addr)+" tried to send us "+str(route)+", which is owned by "+ip+" (fix: poke hawken)")
                continue
            new.append(route)
        create = diff(new, old)
        delete = diff(old, new)
        self.routes[addr] = new
        self.lr.add_multi(create, addr)
        self.lr.delete_multi(delete, addr)

    def delroutes(self, addr):
        self.setroutes(addr, [])
        del self.routes[addr]

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
            dst = cleanup_net(self.dehex(new['Destination'])+"/"+self.dehex(new['Mask']))
            gw  = cleanup_addr(self.dehex(new['Gateway']))
            self.table[dst] = gw
    
    def dehex(self, ip):
        tmp = [str(int(ip[i:i+2], 16)) for i in range(0, len(ip), 2)]
        if endian == 0:
            tmp = reversed(tmp)
        return ".".join(list(tmp))

    def route_add(self, route, gw):
        argv = ["route", "add", "-net", route, "gw", gw]
        ret = subprocess.call(argv)
        self.log.log("route_add: "+" ".join(argv)+": "+str(ret))
        if ret != 0:
            return False
        else:
            return True

    def route_del(self, route, gw):
        argv = ["route", "del", "-net", route, "gw", gw]
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
        socks       = RouterSockets(65536, neigh, log)
        # file with routes separated by newline
        timed       = RouterTimeds(routesfile, log, socks, neigh)
        router.settimed(timed)

        atexit.register(unload, router)
        while True:
            timed.run()
            socks.select()

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
