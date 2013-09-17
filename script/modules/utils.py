# -*- coding: UTF-8 -*-
'''
Created on 12.03.2013

@author: Karbovnichiy Vasiliy <menstenebris@gmail.com>
'''

import os
import tarfile
import datetime 
import time
import shutil
import userclass
import logging
import sys
from ConfigParser import ConfigParser

logger = logging.getLogger('backup')

dt = lambda x,y: " in %s min" % (str((y-x)/60))

date_cmp = lambda x,y: datetime.date.today() >= x + datetime.timedelta(days=y)


class config:
    def __init__(self, configPath):
        self.configPath = configPath
        self.config = ConfigParser()
        self.config.read(configPath)

    def config_write(self, serverList):
        if os.path.exists(self.configPath):
            shutil.move(self.configPath, self.configPath + "~")
        [self.config.add_section(c.name) for c in serverList]
        for section in self.config.sections():
            [map(lambda x: self.config.set(section, **x), server.todict().items()) for server in serverList]
        self._config_save()
    
    def config_add(self, name, value):
        for section in self.config.sections():
            self.config.set(section, name, value)
        self._config_save()
    
    def config_remove(self, name):
        for section in self.config.sections():
            self.config.remove_option(section, name)
        self._config_save()
    
    def config_read(self):
        self.config.s
    
    def config_parse(self):
        l = lambda x: userclass.server(**dict(self.config.items(x)))
        serverList = [l(s) for s in self.config.sections()]
        return serverList
    
    def _config_save(self):
        with open(self.configPath, 'wb') as configfile:
            self.config.write(configfile)
            logger.info("Configuration file successfully updated")

def timer2(fn):
    deltat = lambda x,y: (y-x)/60
    def wrapped(*arg):
        t1 = time.time()
        fn(*arg)
        t2 = time.time()
        return deltat(t1,t2)
    return wrapped

def timer3(fn):
    deltat = lambda x,y: (y-x)/60
    def wrapped(*arg):
        t1 = time.time()
        fn(*arg)
        t2 = time.time()
        print "in %s min" % str(deltat(t1,t2))
    return wrapped

class Daemonize(object):
    def _make_pid(self):
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
            
        os.chdir("/")
        os.setsid()
        os.umask(0)
    
    def daemonize(self, pidfile):
        self._make_pid()
        self._make_pid()
        sys.stdout.flush()
        sys.stderr.flush()
        si = file('/dev/null', 'r')
        so = file('/dev/null', 'a+')
        se = file('/dev/null', 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        pid = str(os.getpid())
        file(pidfile,'w+').write("%s\n" % pid)
    
    
def getFolderSize(folder):
    '''
    Получение размера директории
    '''
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        item = item.decode("cp1251").encode("UTF-8") # убирает ошибку в кодировке # не работает в python 2.6 # cp1251 не распознает русские названия  
        folder = folder.decode("cp1251").encode("UTF-8")
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
    return total_size

def tarFolder(path):
    '''
    Запаковка директории в архив
    '''
    path = path.decode("cp1251").encode("UTF-8")
    path = os.path.normpath(path)
    tarpath = path + ".tar.bz2"
    with tarfile.open(tarpath,"w:bz2") as tar:
        tar.add(path, arcname=os.path.basename(path))
    shutil.rmtree(path)
    return tarpath

def makingPath(path):
    '''
    Создание всех директорий в пути
    '''
    if os.path.exists(path) is not True:
        os.makedirs(path)
    return path

def makeEnv(prefix,env):
    '''
    Создание рабочего окружения
    example:
    prefix = "/home/%username%/"
    env = ['config','log']
    '''
    path = map(lambda x: os.path.join(prefix,x),env)
    map(makingPath, path)
    return dict(zip(env, path))
