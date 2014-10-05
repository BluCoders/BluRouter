#!/usr/bin/python
# -*- coding: utf-8 -*-

import ipaddr

# Uses log, socks
class RouterTimeds:
    """
    RouterTimeds is responsible for propagating our routes
    """
    def __init__(self, log, socks, conf):
        self.myroutes   = []
        self.log        = log
        self.socks      = socks
        self.last_hello = 0
        self.conf       = conf

    def readroutes(self, ts):
        try:
            f = open(self.conf["routefile"], "r")
            l = sorted([ipaddr.IPv4Network(i.strip()) for i in f.readlines()])
            f.close()
        except Exception as e:
            self.log.log("readroutes: "+self.conf["routefile"]+" is trapped in another dimension..")
            return

        if l != self.myroutes:
            self.log.log("readroutes: New routes found in the routefile!")
            self.myroutes = l
            self.hello()
            self.last_hello = ts

    def compensate(self, diff):
        self.last_hello += diff

    def run(self, ts):
        self.readroutes(ts)

        if (ts-self.last_hello) >= self.conf["hello_interval"]:
            self.hello()
            self.last_hello = ts

    def hello(self):
        """When this is called, it is time to broadcast our existence"""
        self.socks.out({
            'type': 'hello',
            'ttl':  str(self.conf["hello_timeout"]),
            'nets': [str(x) for x in self.myroutes]
        })
