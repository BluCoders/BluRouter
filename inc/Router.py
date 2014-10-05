#!/usr/bin/python
# -*- coding: utf-8 -*-

# Method to create a list of the things that are in a but not in b
def diff(a, b):
    b = set(b)
    return [aa for aa in a if aa not in b]

# Uses log
class Router:
    """
    Mainly exports setroutes and delroutes
    Router polices who gets which IP ranges
    """
    def __init__(self, log, localrouter, conf):
        self.routes = {}
        self.log    = log
        self.lr     = localrouter
        self.conf   = conf

    def settimed(self, timed):
        self.timed = timed

    # Removes our routes
    def shutdown(self):
        for ip in self.routes:
            self.lr.delete_multi(self.routes[ip], ip)

    # Check if any of routes overlap with new
    def contains(self, new, routes):
        for route in routes:
            if new.overlaps(route):
                return True
        return False

    # Check if the route is in protected nets or not in allow_ranges
    def checkranges(self, route):
        if self.contains(route, self.conf["protected_nets"]):
            return False

        for net in self.conf["allow_ranges"]:
            if net.Contains(route):
                return True

        return False

    def busy(self, route, addr):
        """
        Checks if any of the other hosts have taken this route already
        return false if it's available, return ip if busy
        """
        # Walk all 'cept this one and check
        for ip in self.routes:
            if addr==ip:
                continue
            if self.contains(route, self.routes[ip]):
                return ip
        return False

    def owns(self, route):
        """ Are we the owners of route """
        return self.contains(route, self.timed.myroutes)

    """ Setroutes called with a string address """
    def setroutes(self, addr, routes):
        """ Takes an address and a list of routes, tries to route those routes through addr """
        # If this node is new, initialize an empty array
        if not addr in self.routes:
            self.routes[addr] = []
            if self.conf["newip_sendnets"]:
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
        """ Timeout an address """
        self.setroutes(addr, [])
        del self.routes[addr]
