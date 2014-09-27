# -*- coding: utf-8 -*-

import syslog

UDP_IP = "192.168.0.1"                    # Your IP within your VPN/LAN
# Source addresses to accept packets from
# This should be limited to the addresses that also run blurouter.
UDP_SUBNET = "192.168.0.0/24"
UDP_BROADCAST = "192.168.0.255"           # Address all boxes will use to broadcast
UDP_PORT=12345                            # Port all boxes will use to broadcast

ALLOW_RANGES    = ["192.168.0.0/16"]      # Entire VPN/LAN range you use
PROTECTED_NETS  = ["192.168.0.0/24"]      # The VPN/LAN range this box is in

syslog_pri = syslog.LOG_NOTICE
syslog_facil = syslog.LOG_USER

routesfile='/path/to/routes.txt'
pidfile='/path/to/router.pid'

# little endian (x86 / amd64)
endian=0
# big endian
#endian=1

# Options you shouldn't touch unless you know what you are doing follows:

# hello_interval:
# Seconds between sending route advertisements
# Less = more network spam
# more = slow reaction time
# We also automatically send hello if you change routes.txt,
# which happens at least every select_timeout seconds.
hello_interval = 30

# hello_timeout:
# For the remote end: How long time can we be silent before we are assumed dead?
# setting 100 means we have a max of 100 seconds (2 lost packets) before we are assumed to be dead
# You can set this based on how intolerant to network loss you can be;
# if you do not tolerate losses,    set it between 1-2 intervals.
# If you tolerate one lost packet,  set it between 2-3 intervals.
# If you tolerate two lost packets, set it between 3-4 intervals.
hello_timeout = 100

# select_timeout:
# Give up on select every second
# This controls how often the timed code runs
# A low value is nice because:
#  - I don't think each round is very very expensive
#  - It keeps the program responsive
# This parameter controls the minimum intervals of
#  - How often we check if we need to send hello messages
#  - How often we read the routes file
#  - How often we check the neighbors for timeouts
# Try to keep it at most half of hello_interval
# Do not set it to 0 as it means infinite
select_timeout = 1

# max_ttl:
# This is how long someone can be offline without us assuming they are still online
# We will never let someone say they can be silent for more than an hour
max_ttl=3600

# newip_sendnets:
# Testing this behavior:
# When we receive hello from a new ip (expired or never seen before), we send our own hello packet back.
# The intended effect is that a new host entering the network is bootstrapped by us immediately.
# Normally, it takes up to 30 seconds before all routes are added.
# Potential problem: In a network of n machines starting up, minimum n**2 packets are sent.
# True or False
newip_sendnets = True
