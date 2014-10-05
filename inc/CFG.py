#!/usr/bin/python
# -*- coding: utf-8 -*-

import ConfigParser
import os
import ipaddr
import syslog

class CFG:
    def __init__(self):
        self.cfg = ConfigParser.ConfigParser()
        self.sect = "BluRouter"

    def _reraise(self, key, e):
        raise Exception("Error in configuration file: "+key+": "+str(e))

    def read(self, configfile):
        self.cfg.read(configfile)
        if not os.path.isfile(configfile):
            raise IOError("File not found: "+configfile)
        out = {
            "udp_ip":         self.udp_ip(),
            "udp_subnet":     self.udp_subnet(),
            "udp_broadcast":  self.udp_broadcast(),
            "udp_port":       self.udp_port(),
            "allow_ranges":   self.allow_ranges(),
            "protected_nets": self.protected_nets(),
            "syslog_pri":     self.syslog_pri(),
            "syslog_facil":   self.syslog_facil(),
            "routefile":      self.routefile(),
            "pidfile":        self.pidfile(),
            "hello_interval": self.hello_interval(),
            "hello_timeout":  self.hello_timeout(),
            "select_timeout": self.select_timeout(),
            "max_ttl":        self.max_ttl(),
            "newip_sendnets": self.newip_sendnets()
        }
        return out

    def udp_ip(self):
        try:
            return ipaddr.IPv4Address(self.cfg.get(self.sect, "udp_ip").strip())
        except Exception as e:
            self._reraise("udp_ip", e)

    def udp_subnet(self):
        try:
            return ipaddr.IPv4Network(self.cfg.get(self.sect, "udp_subnet").strip())
        except Exception as e:
            self._reraise("udp_subnet", e)

    def udp_broadcast(self):
        try:
            return ipaddr.IPv4Address(self.cfg.get(self.sect, "udp_broadcast").strip())
        except Exception as e:
            self._reraise("udp_broadcast", e)

    def udp_port(self):
        try:
            return self.cfg.getint(self.sect, "udp_port")
        except Exception as e:
            self._reraise("udp_port", e)

    def allow_ranges(self):
        try:
            arr = self.cfg.get(self.sect, "allow_ranges").strip("\t \r\n,").split(",")
            if arr == [""]:
                return []
            return [ipaddr.IPv4Network(x.strip()) for x in arr]
        except Exception as e:
            self._reraise("allow_ranges", e)

    def protected_nets(self):
        try:
            arr = self.cfg.get(self.sect, "protected_nets").strip("\t \r\n,").split(",")
            if arr == [""]:
                return []
            return [ipaddr.IPv4Network(x.strip()) for x in arr]
        except Exception as e:
            self._reraise("protected_nets", e)

    def syslog_pri(self):
        m = {
            "log_emerg":    syslog.LOG_EMERG,
            "log_alert":    syslog.LOG_ALERT,
            "log_crit":     syslog.LOG_CRIT,
            "log_err":      syslog.LOG_ERR,
            "log_warning:": syslog.LOG_WARNING,
            "log_notice":   syslog.LOG_NOTICE,
            "log_info":     syslog.LOG_INFO,
            "log_debug":    syslog.LOG_DEBUG
        }
        try:
            pri = self.cfg.get(self.sect, "syslog_pri").strip().lower()
            return m[pri]
        except Exception as e:
            self._reraise("syslog_pri", e)

    def syslog_facil(self):
        m = {
            "log_kern":   syslog.LOG_KERN,
            "log_user":   syslog.LOG_USER,
            "log_mail":   syslog.LOG_MAIL,
            "log_daemon": syslog.LOG_DAEMON,
            "log_auth":   syslog.LOG_AUTH,
            "log_lpr":    syslog.LOG_LPR,
            "log_news":   syslog.LOG_NEWS,
            "log_uucp":   syslog.LOG_UUCP,
            "log_cron":   syslog.LOG_CRON,
            "log_syslog": syslog.LOG_SYSLOG,
            "log_local0": syslog.LOG_LOCAL0,
            "log_local1": syslog.LOG_LOCAL1,
            "log_local2": syslog.LOG_LOCAL2,
            "log_local3": syslog.LOG_LOCAL3,
            "log_local4": syslog.LOG_LOCAL4,
            "log_local5": syslog.LOG_LOCAL5,
            "log_local6": syslog.LOG_LOCAL6,
            "log_local7": syslog.LOG_LOCAL7
        }
        try:
            pri = self.cfg.get(self.sect, "syslog_facil").strip().lower()
            return m[pri]
        except Exception as e:
            self._reraise("syslog_facil", e)

    def routefile(self):
        try:
            return self.cfg.get(self.sect, "routefile").strip()
        except Exception as e:
            self._reraise("routefile", e)

    def pidfile(self):
        try:
            return self.cfg.get(self.sect, "pidfile").strip()
        except Exception as e:
            self._reraise("pidfile", e)

    def hello_interval(self):
        try:
            return self.cfg.getint(self.sect, "hello_interval")
        except Exception as e:
            self._reraise("hello_interval", e)

    def hello_timeout(self):
        try:
            return self.cfg.getint(self.sect, "hello_timeout")
        except Exception as e:
            self._reraise("hello_timeout", e)

    def select_timeout(self):
        try:
            return self.cfg.getint(self.sect, "select_timeout")
        except Exception as e:
            self._reraise("select_timeout", e)

    def max_ttl(self):
        try:
            return self.cfg.getint(self.sect, "max_ttl")
        except Exception as e:
            self._reraise("max_ttl", e)

    def newip_sendnets(self):
        try:
            return self.cfg.getboolean(self.sect, "newip_sendnets")
        except Exception as e:
            self._reraise("newip_sendnets", e)
