#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import ipaddr

# Uses log, socks, neigh
class RouterTimeds:
    """
    RouterTimeds contains the code we run mostly every second.
    It is responsible for:
     - propagating the routes file (sending hello)
     - calling RouterNeighbors run function to time out neighbors
    """
    myroutes = []
    def __init__(self, myroutefile, log, socks, neigh, hello_interval, myttl):
        self.routefile = myroutefile
        self.log = log
        self.socks = socks
        self.neigh = neigh
        self.last_hello = 0
        self.myttl = myttl
        self.hello_interval = hello_interval

    def readroutes(self, ts):
        try:
            f = open(self.routefile, "r")
            l = sorted([ipaddr.IPv4Network(i.strip()) for i in f.readlines()])
            f.close()
        except Exception as e:
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
        self.socks.out({'type':'hello', 'ttl':str(self.myttl), 'nets':[str(x) for x in self.myroutes]})

    def ts(self):
        return time.time()
