#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import json
import ipaddr
from select import select

# Uses log, neigh
class RouterSockets:
    """
    RouterProtocol takes input and processes it. It also encodes stuff with json.
    Can route packets to different destinations within the program, if needed.
    What to find here: socket in/out/initialization + select
    """
    def __init__(self, log, neigh, bufsiz, conf):
        self.maxin = bufsiz
        self.neigh = neigh
        self.log   = log
        self.sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conf  = conf

        self.sock.bind((str(conf["udp_broadcast"]), conf["udp_port"]))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def select(self):
        inr, outr, exr = select([self.sock],[],[], self.conf["select_timeout"])
        for s in inr:
            if s == self.sock:
                self.input()

    def route(self, addr, data):
        if data['type'] == 'hello':
            self.neigh.hello(addr[0], data)

    def input(self):
        data, src = self.sock.recvfrom(self.maxin)
        if not ipaddr.IPv4Address(src[0]) in self.conf["udp_subnet"]:
            self.log.log("RouterSockets.input: Discarding packet from "+str(src[0])+"")
            return
        try:
            data = json.loads(data)
        except ValueError:
            self.log.log("RouterSockets.input: from "+str(src[0])+", failed to read JSON, someone messing with us?")
            return
        if not "type" in data:
            self.log.log("RouterSockets.input: from "+str(src[0])+", json data does not contain the type field.. Stop messing with me!")
            return
        self.route(src, data)

    def out(self, data):
        try:
            self.sock.sendto(json.dumps(data), (str(self.conf["udp_broadcast"]), self.conf["udp_port"]))
        except socket.error as e:
            self.log.log("RouterSockets.out: failed to send data: "+e.strerror)
