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


# Uses neigh
class RouterSockets:
    """RouterProtocol takes input and processes it. It also encodes stuff"""
    sel_timeout = 1
    def __init__(self, bufsiz, neigh):
        self.maxin = bufsiz
        self.neigh = neigh
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_BROADCAST, UDP_PORT))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def select(self):
        inr, outr, exr = select([self.sock],[],[], self.sel_timeout)
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
        self.sock.sendto(json.dumps(data), (UDP_BROADCAST, UDP_PORT))

# Uses log, socks, neigh
class RouterTimeds:
    myroutes = []
    def __init__(self, interval, ttl, myroutefile, log, socks, neigh):
        self.routefile = myroutefile
        self.log = log
        self.socks = socks
        self.neigh = neigh
        self.hello_interval = interval
        self.hello_ttl = ttl
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

        if (ts-self.last_hello) >= self.hello_interval:
            self.hello()
            self.last_hello = ts
    def hello(self):
        """When this is called, it is time to broadcast our existence"""
        self.socks.out({'type':'hello', 'ttl':self.hello_ttl, 'nets':self.myroutes})

    def ts(self):
        return time.time()

# Uses log, router
class RouterNeighbors():
    timer = {}
    def __init__(self, maxttl, log, router):
        self.max_ttl = maxttl
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
        if ttl > self.max_ttl:
            ttl = self.max_ttl

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
    def run(self):
        #log = LogStdout()
        log = LogSyslog(syslog_facil, syslog_pri)
        localrouter = RouterLocal(log)
        router      = Router(localrouter, log)
        # max ttl to accept from other hosts
        neigh       = RouterNeighbors(3600, log, router)
        # Max buf size for a single packet. Will limit available routes
        socks       = RouterSockets(65536, neigh)
        # Interval between transmitting routes, timeout before we are offline, file with routes separated by newline
        timed       = RouterTimeds(30, 90, routesfile, log, socks, neigh)
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
        daemon.run()
    else:
        print "Unknown command"
        sys.exit(2)
    sys.exit(0)
else:
    print "usage: %s start|stop|restart|test" % sys.argv[0]
    sys.exit(2)
