# BluRouter

BluRouter is our own internal routing system (screw quagga-ware...)

# Howto

* Edit the config-example.py exactly as you need it, then save as config.py
* Edit routes-example.txt and add any subnets the box owns. Use of netmasks is allowed.
* Run router.py, using 'router.py start', to daemonize the process.

# Requirements

* python-ipaddr

## TODO

### Important
* command line options (especially: where is our config file?)

### Wishlist
* routes.txt is a hacky solution (effective though). We should think up a more elegant way
  * FYI: routes.txt is read about every second. If it changes, we send the new routes right away.
  * In case of network spam, routes.txt can be read very often (after every packet)
  * Potential DoS vulnerability!
  * TODO: use timestamps to make sure it is only read every second
