# -*- coding: utf-8 -*-

import syslog

UDP_IP = "192.168.0.1"                    # Your IP within your VPN/LAN
UDP_BROADCAST = "192.168.0.255"           # Address all boxes will use to broadcast
UDP_PORT=12345                            # Port all boxes will use to broadcast

ALLOW_RANGES    = ["192.168.0.0/16"]      # Entire VPN/LAN range you use
PROTECTED_NETS  = ["192.168.0.0/24"]      # The VPN/LAN range this box is in

syslog_pri = syslog.LOG_NOTICE
syslog_facil = syslog.LOG_USER

routesfile='/path/to/routes.txt'
pidfile='/path/to/router.pid'
