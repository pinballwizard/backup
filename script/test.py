#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
Created on 14.03.2013

@author: vasiliy
'''

# from modules import utils
import os
import sys
import datetime
import time
# import sys
import threading
# import re
# import shutil
# import rdiff_backup
# import logging
  
# import ConfigParser
# configPath = u"/home/datastore/config/config.ini"
# config = ConfigParser.ConfigParser()
# config.read(configPath)
# for s in config.sections():
# #     config.remove_option(s, 'path')
#     config.set(s,'tbr','1')
# with open(configPath, 'wb') as configfile:
#         config.write(configfile)
#         
# import database
# dbpath = u"/home/datastore/database.db"
# backup_table = u"backup"
# backup1 = {'name':'s2v02n', 'backuptype':'file', 'realsize':-1, 'realpath':'/home/vasiliy/', 'makingtime':'01.04.2013', 'last':1}
# dbc1 = database.DB(dbpath)
# dbc1.execute(u'''INSERT INTO %s (host_name, backuptype, real_size, making_time, real_path, last) 
#                     VALUES(:name, :backuptype, :realsize, :makingtime, :realpath, :last)''' % (backup_table), backup1)
# dbc1.commit()
# dbc1.close()

# open("/home/datastore/alert1", "w+")

# 
# d = "total size is 60580  speedup is 56.04"
# a = re.findall("is .*  ", d)
# print float(a[0][3:-2])

# timeline = datetime.time(00)
# print datetime.datetime.now().hour == timeline.hour


# def writer(x, event_for_wait, event_for_set):
#     for i in xrange(10):
#         event_for_wait.wait() # wait for event
#         event_for_wait.clear() # clean event for future
#         print x
#         time.sleep(0.5)
#         event_for_set.set() # set event for neighbor thread
# 
# # init events
# e1 = threading.Event()
# e2 = threading.Event()
# 
# # init threads
# t1 = threading.Thread(target=writer, args=(0, e1, e2))
# t2 = threading.Thread(target=writer, args=(1, e2, e1))
# 
# # start threads
# t1.start()
# t2.start()
# 
# e1.set() # initiate the first event
# 
# # join threads to the main thread
# t1.join()
# t2.join()

# from multiprocessing import Process
#   
# def f():
#     while True:
#         print 'hello'
#         time.sleep(1)
#     g.terminate()
#          
#    
# def s():
#     while True:
#         print 'great'
#         time.sleep(1)
#    
# def h():
#     time.sleep(2)
#     p.terminate()
#     while True:
#         time.sleep(2)
#         print 'great'
#   
# if __name__ == '__main__':
#     p = Process(target=f)
#     g = Process(target=h)
# #     d = Process(target=s, args=())
#     p.start()
#     g.start()
#     p.is_alive()
#     g.join()
#      
#     p.join()
#     g.terminate()
#     sys.exit(0)



# class f(Exception):
#     def __init__(self, value):
#         self.value = value
#     def __str__(self):
#         return repr(self.value)
# while True:
#     try:
#         raise f("hello")
#     except:
#         print "haha i catch you %s" % f

# import logging
# 
# FORMAT = u'%(levelname)-4s [%(asctime)-4s] %(message)s'
# # formatter = logging.Formatter(fmt=FORMAT, datefmt='%X')
# logging.basicConfig(format=FORMAT, datefmt = '%X')
# logging.warning(u'hello')

# import librsync
# import paramiko
# from modules import selfssh
# 
# class s(object):
#     def __init__(self):
#         pass
#     
# 
# server = s
# server.host = 'backup'
# server.port = '22'
# server.user = 'root'
# server.secret = '123456'
# 
# client = paramiko.SSHClient()
# client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# client.connect(hostname = server.host, port = server.port, username = server.user, password = server.secret)
# channel = client.get_transport()
# session = channel.open_session()
# session.settimeout(20)
# session.exec_command('ls')
# session.recv_exit_status()
# answer = session.recv(2048)
# session.close()

# dst = file('/home/schema', 'rb')
#  
# # The source file.
# src = file('/home/vasiliy/exm/schema', 'rb')
#  
# # Where we will write the synchronized copy.
# synced = file('root@192.168.13.73:/home/schema', 'wb')
#  
# # Step 1: prepare signature of the destination file
# signature = librsync.signature(dst)
#  
# # Step 2: prepare a delta of the source file
# delta = librsync.delta(src, signature)
 
# Step 3: synchronize the files.
# In many cases, you would overwrite the destination with the result of
# synchronization. However, by default a new file is created.
# librsync.patch(dst, delta, synced)


class BackupException(Exception):
    def __init__(self, estr):
        self.err_str = estr
#         make_alert(os.path.join(env_dict['alert'], self.err_str))
#         logger.error(self.err_str)

    def __str__(self):
        return self.err_str
try:
    raise BackupException('hello')
except BackupException:
    print 'hello'
print 'h'