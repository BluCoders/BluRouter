# BluRouter

BluRouter is our own internal routing system (screw quagga-ware...)

# Howto

* Edit the config-example.py exactly as you need it, then save as config.py
* Edit routes-example.txt and add any subnets the box owns. Use of netmasks is allowed.
* Run router.py, using 'router.py start', to daemonize the process.

# Requirements

* python-ipaddr
