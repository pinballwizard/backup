# -*- coding: utf-8 -*-
'''
Created on 10 сент. 2013 г.

@author: vasiliy
'''

import logging
import traceback
import os
from src.script.backup import env_dict

logger = logging.getLogger('backup')
alert_path = env_dict['alert']

def make_alert(filename, alert_body=''):
    with open(filename, "w+") as f:
        f.write(alert_body)

class DefException(Exception):
    def __init__(self, estr):
        self.err_str = estr
        self.logger()
    def __logger(self):
        logger.error(self.err_str)
    def __str__(self):
        return self.err_str  

class CrashException(DefException):
    def __init__(self, estr):
        DefException.__init__(self, estr)
        self.alert_body = self.err_str + '\n' + traceback.format_exc()
        make_alert(os.path.join(self.alert_path, "daemon crash"), self.alert_body)
    def __logger(self):
        logger.critical(self.err_str)
        
class BackupException(DefException):
    def __init__(self, estr):
        DefException.__init__(self, estr)
        make_alert(os.path.join(self.alert_path, self.err_str))

class AlertBodyException(DefException):
    def __init__(self, estr, alert_body):
        DefException.__init__(self, estr)
        make_alert(os.path.join(self.alert_path, self.err_str), alert_body)
        