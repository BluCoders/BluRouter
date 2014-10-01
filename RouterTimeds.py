#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import ipaddr

# Uses log, socks
class RouterTimeds:
    """
    RouterTimeds is responsible for propagating our routes
    """
    myroutes = []
    def __init__(self, log, socks, myroutefile, hello_interval, myttl):
        self.routefile = myroutefile
        self.log = log
        self.socks = socks
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
        ts = time.time()
        self.readroutes(ts)

        if (ts-self.last_hello) >= self.hello_interval:
            self.hello()
            self.last_hello = ts

    def hello(self):
        """When this is called, it is time to broadcast our existence"""
        self.socks.out({'type':'hello', 'ttl':str(self.myttl), 'nets':[str(x) for x in self.myroutes]})
