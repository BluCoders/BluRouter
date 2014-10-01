#!/usr/bin/python
# -*- coding: utf-8 -*-

import ipaddr

# Uses log
class RouterLocal():
    table = {}
    def __init__(self, log, endian):
        self.endian = endian
        self.log = log
        self.get_kernel_table()

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
        if self.endian == 0:
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
