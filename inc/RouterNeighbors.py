#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import ipaddr

# Uses log, router
class RouterNeighbors():
    """
    RouterNeighbors does two things:
     - Remove expired neighbors
     - Process packets from neighbors
    """
    def __init__(self, log, router, conf):
        self.log    = log
        self.router = router
        self.conf   = conf
        self.timer  = {}

    def compensate(self, diff):
        for ip in self.timer:
            self.timer[ip] += diff


    def run(self, ts):
        """ Remove expired neighbors """
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

        if ipaddr.IPv4Address(addr) == self.conf["udp_ip"]:
            return
        if ttl <= 0:
            # Packet immediately times out on 0 or negative numbers
            self.log.log("RouterNeighbors.hello: "+str(addr)+" might want to update their ttl to something larger than "+str(ttl)+" seconds.")
            return
        if ttl > self.conf["max_ttl"]:
            ttl = self.conf["max_ttl"]

        until            = ttl+time.time()
        self.timer[addr] = until
        self.router.setroutes(addr, nets)
