# BluRouter

BluRouter is our own internal routing system (screw quagga-ware...)

# Changes
* Switching config.py to config.ini
 * python tool-inify.py reads config.py and writes config.ini

# Howto

* Edit the config-example.py exactly as you need it, then save as config.py
* Edit routes-example.txt and add any subnets the box owns. Use of netmasks is allowed.
* Run ./router.py, using './router.py start' to daemonize the process.
* It can also be run in foreground mode with './router.py test'

# Requirements

* python-ipaddr
