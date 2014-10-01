#!/usr/bin/python
# -*- coding: utf-8 -*-

# Method to create a list of the things that are in a but not in b
def diff(a, b):
    b = set(b)
    return [aa for aa in a if aa not in b]

# Uses log
class Router:
    def __init__(self, localrouter, log, newip_sendnets, protected_nets, allow_ranges):
        self.routes = {}
        self.log = log
        self.lr = localrouter
        self.newip_sendnets = newip_sendnets
        self.protected_nets = protected_nets
        self.allow_ranges = allow_ranges

    def settimed(self, timed):
        self.timed = timed
    def shutdown(self):
        for ip in self.routes:
            self.lr.delete_multi(self.routes[ip], ip)

    def contains(self, new, routes):
        for route in routes:
            if new.overlaps(route):
                return True
        return False

    def checkranges(self, route):
	if self.contains(route, self.protected_nets):
	    return False

        for net in self.allow_ranges:
            if net.Contains(route):
                return True

	return False

    # Checks if a route is busy,
    # False if it is available
    # ip if it is taken (by another ip)
    def busy(self, route, addr):
        # Walk all 'cept this one and check
        for ip in self.routes:
            if addr==ip:
                continue
            if self.contains(route, self.routes[ip]):
                return ip
        return False

    # Check if we own this route
    def owns(self, route):
        return self.contains(route, self.timed.myroutes)

    def setroutes(self, addr, routes):
        # If this node is new, initialize an empty array
        if not addr in self.routes:
            self.routes[addr] = []
            if self.newip_sendnets:
                self.timed.hello()
        # New routes and routes we already have are diffed to know what actions to apply
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
