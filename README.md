BluRouter
=========

BluRouter is our own internal routing system (screw quagga-ware...)

TODO
----
* Logging to syslog and removal of "sent hello packet"
* Daemonizable (check pid, fork, write pid, ...)
* Some way to catch and syslog python errors (try: except: the main loop perhaps?)
