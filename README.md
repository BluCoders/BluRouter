# BluRouter

BluRouter is our own internal routing system (screw quagga-ware...)

# Requirements

* python-ipaddr

## TODO

### Important
* Some way to catch and syslog python errors (try: except: the main loop perhaps?)
* command line options (especially: where is our config file?)
* More elegant configuration (more customization? There is a few constants in router.py itself..)
* Interface up/down/delete/create can lead to: sockets dying, routing table reset. We need to handle these scenarios.
  * Idea: interval=10 polling of routing table and verification
  * Idea: Somehow hook something that triggers when it happens?

### Wishlist
* routes.txt is a hacky solution (effective though). We should think up a more elegant way
  * FYI: routes.txt is read about every second. If it changes, we send the new routes right away.
  * TODO: use timestamps to make sure it is only read every second
* Code optimalization (it has lots of potential for optimalization)
