# BluRouter

BluRouter is our own internal routing system (screw quagga-ware...)

# Howto

* Edit the config-example.py exactly as you need it, then save as config.py
* Edit routes-example.txt and add any subnets the box owns. Use of netmasks is allowed.
* Run ./router, using './router start' to daemonize the process.
* It can also be run in foreground mode with './router test'

# Requirements

* python-ipaddr
