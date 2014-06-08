# -*- coding: utf-8 -*-

import syslog

UDP_IP = "192.168.0.1"
UDP_BROADCAST = "192.168.0.255"
UDP_PORT=12345

ALLOW_RANGES    = ["192.168.0.0/16"]
PROTECTED_NETS  = ["192.168.0.0/24"]

syslog_pri = syslog.LOG_NOTICE
syslog_facil = syslog.LOG_USER

#pidfile='/opt/BluRouter/router.pid'
pidfile='router.pid'
