#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

# Uses log, router
class RouterNeighbors():
    timer = {}
    def __init__(self, log, router, myip):
        self.log = log
        self.router = router
        self.myip = myip

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

        if addr == self.myip:
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
