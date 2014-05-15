BluRouter
=========

BluRouter is our own internal routing system (screw quagga-ware...)

TODO
----
Points 1-5 are more or less essential before packaging
Points 6-7 are wishlist
* Logging to syslog and removal of "sent hello packet"
* Daemonizable (check pid, fork, write pid, ...)
* Some way to catch and syslog python errors (try: except: the main loop perhaps?)
* command line options (especially: where is our config file?)
* More elegant configuration (more customization? There is a few constants in router.py itself..)
* routes.txt is a hacky solution (effective though). We should think up a more elegant way
  * FYI: routes.txt is read about every second. If it changes, we send the new routes right away.
* Code optimalization (it has lots of potential for optimalization)
