#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
Created on 14.03.2013

@author: vasiliy
'''


# from multiprocessing import Process, Lock, Event
# import time
# import subprocess
#  
# def f(l, i):
#     l.acquire()
#     for n in range(10):
#         subprocess.Popen('echo %s' % i, shell = True)
# #         print 'hello world', i
#         time.sleep(1)
#     l.release()
#   
# if __name__ == '__main__':
#     for num in range(100000):
#         lock = Lock()
#         watcher_event = Event()
#         s = Process(target=f, args=(lock, num))
#         s.start()
#         s.join()
import modules.exceptions


raise modules.exceptions.BackupException('hello','test')