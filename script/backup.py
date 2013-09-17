#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
Created on 11.03.2013

@author: Karbovnichiy Vasiliy <menstenebris@gmail.com>
'''

from modules import selfssh
from modules import database
from modules import userclass
from modules import utils
from modules.utils import dt, Daemonize
# from modules.exceptions import DefException, CrashException, BackupException, AlertBodyException

import time
import os
import logging
import shutil
import sys
import datetime
import traceback
from multiprocessing import Process, Event, Lock

global env_dict

#  Глобальные переменные
host_table = "hosts"
backup_table = "backup"
prefix = "/home/datastore/"
env = ["alert", "store", "config", "log"]
env_dict = utils.makeEnv(prefix, env)
dbpath = os.path.join(env_dict['config'], "database.db")
config_path = os.path.join(env_dict['config'], "config.ini")
pidfile = "/var/run/backup.pid"


full_backup_lifetime = 180 # количество дней жизни полного бэкапа
inc_backup_lifetime = 14 # количество дней жизни инкрементного бэкапа
time_before_packing = 7 # количество дней до упаковки бэкапа
time_before_repeat = 1
log_lifetime = 30 # количество дней жизни логов
timeline = (2,6) # интервал работы в 24-x часовом формате
sleeptime = 600 # время ожидания до повторной проверки

#  Настройка модуля logging
logger = logging.getLogger('backup')
logger.setLevel(level=logging.DEBUG)
# mlogger = multiprocessing.get_logger()
# mlogger.setLevel(level=logging.DEBUG)
loggers = (logger,)


def makingpath(server):
    backupdir = os.path.join(env_dict['store'], server.operator, server.name, str(datetime.date.today()))
    if os.path.exists(backupdir) is not True:
        os.makedirs(backupdir)
        logger.debug("[%s] directory %s was created" % (server.name, backupdir))
    return backupdir

def make_alert(filename, alert_body=''):
    with open(filename, "w+") as f:
        f.write(alert_body)
       
class BackupException(Exception):
    def __init__(self, estr):
        self.err_str = estr
        logger.error(self.err_str)
        make_alert(os.path.join(env_dict['alert'], self.err_str))
    def __str__(self):
        return self.err_str  
    
class AlertBodyException(Exception):
    def __init__(self, estr, alert_body):
        self.err_str = estr
#         logger.error(self.err_str)
        make_alert(os.path.join(env_dict['alert'], self.err_str), alert_body)
    def __str__(self):
        return self.err_str  

class do_backup(object):
    def __init__(self, server):
        backup_path = makingpath(server)
        self.server = server
        self.connection_alert_path = os.path.join(env_dict['alert'], "[%s] connection failed" % (server.name))
        self.backup = userclass.backup(name=server.name, makingtime='now', kind=None, realpath=backup_path)

    def connect(self):
        try:
            self.connection = selfssh.Connection(self.server)
            logger.debug('[%s] connection established' % (self.server.name))
        except Exception as e:
            alert = '[%s] connection failed with exception: %s: %s' % (self.server.name, e.__class__, e)
            logger.warning(alert)
            return False

    def full(self):
        logger.info('[%s] processing full backup' % (self.server.name))
        self.backup.kind = 'full'
        self.prev_backup = None
        self.body()
        return self.backup

    def incremental(self, prev_backup):
        logger.info('[%s] processing incremental backup' % (self.server.name))
        self.backup.kind = 'inc'
        self.prev_backup = prev_backup
        self.body()
        return self.backup
    
#     @utils.timer2
    def body(self):
        t1 = time.time()
        for n in range(0,3):
            cans = self.connect()
            if cans is not False:
                break
        del n
        if cans is False:
            self.destroy()
            raise BackupException("[%s] can't connect..." % (self.server.name))
        if self.server.schema_flag == 1:
            self.schema_backup()
        if self.server.file_flag == 1:
            self.file_backup()
        t2 = time.time()
        logger.info('[%s] creating backup complete' % (self.server.name) + dt(t1, t2))
        self.alert_destroy()

    def check_schema(self):
        if not os.path.exists(self.backup.schema_path):
            self.destroy()
            raise BackupException("[%s] schema backup doesn't exist" % (self.server.name))
        elif not os.listdir(self.backup.schema_path):
            self.destroy()
            raise BackupException("[%s] schema backup doesn't exist" % (self.server.name))

    def check_file(self):
        if not os.path.exists(self.backup.file_path):
            self.destroy()
            if self.backup.kind == 'full':
                raise BackupException("[%s] file backup doesn't exist" % (self.server.name))
        elif not os.listdir(self.backup.file_path):
            self.destroy()
            if self.backup.kind == 'full':
                raise BackupException("[%s] file backup doesn't exist" % (self.server.name))

    def schema_backup(self):
        self.connection.schemas_backup(self.backup.realpath)
        logger.info('[%s] creating schema backup complete' % self.server.name)
        self.check_schema()

    def file_backup(self):
        self.check_size = self.connection.check_file_size()
        if self.check_size is True:
            self.connection.get_file_rsync(self.prev_backup, self.backup)
#             lock = Lock()
#             watcher_event = Event()
#             prisoner = Process(target=self.rsync_launcher)
#             self.watcher = Process(target=self.rsync_destroyer, args=(watcher_event))
#             prisoner.start()
#             self.watcher.start()
#             prisoner.join()
#             self.watcher.join()
            self.backup.get_size()
            logger.info('[%s] creating file backup complete' % self.server.name)
        else:
            self.destroy()
            raise AlertBodyException("[%s] exceeded backup size" % self.server.name, alert_body = self.check_size)
        self.check_file()
    
    def rsync_launcher(self):
#         lock.acquire()
        logger.debug('[%s] prisoner process start' % self.server.name)
#         watcher_event.set()
        self.connection.get_file_rsync(self.prev_backup, self.backup)
#         self.watcher.terminate()
        logger.debug('[%s] prisoner process stop' % self.server.name)
#         lock.release()
    
    def rsync_destroyer(self, watcher_event):
        t = 60
        fsize = 0
        watcher_event.wait()
        time.sleep(t)
        ssize = utils.getFolderSize(self.backup.file_path)
        while fsize < ssize:
            fsize = ssize
            time.sleep(t)
            ssize = utils.getFolderSize(self.backup.file_path)
        time.sleep(t)
        self.prisoner.terminate()
        self.destroy()
        raise BackupException("[%s] rsync freeze and watcher destroy him" % (self.server.name))

    def alert_destroy(self):
        for name in os.listdir(env_dict['alert']):
            if self.server.name in name:
                os.remove(os.path.join(env_dict['alert'], name))
        logger.debug("[%s] all alert destroyed" % (self.server.name))
       
    def destroy(self):
        logger.warning("[%s] destroyer started" % (self.server.name))
        if os.path.exists(self.backup.realpath) is True:
            shutil.rmtree(self.backup.realpath)
            logger.warning("[%s] all data was destroy" % (self.server.name))


class MyDaemon(Daemonize):
    name = None

    def __init__(self):
        self.logger_init()
        self.wdb = database.currentDB(dbpath, host_table, backup_table)
    
    def __del__(self):
        self.wdb.close()
        del self.wdb
    
    def logger_init(self):
        FORMAT = '%(levelname)-4s [%(asctime)-4s] %(message)s'
        formatter = logging.Formatter(fmt=FORMAT, datefmt='%X')
        log_path = os.path.join(env_dict['log'], '%s.log' % (str(datetime.date.today())))
        log_handler = logging.FileHandler(log_path)
        log_handler.setFormatter(formatter)
        log_handler.setLevel(level=logging.DEBUG)
        
        def lo(dlogger):
            current_handlers = dlogger.handlers[:]
#             [h.close() for h in current_handlers]
            [dlogger.removeHandler(h) for h in current_handlers]
            dlogger.addHandler(log_handler)
            dlogger.debug('number of logger handlers were removed = %s' % len(current_handlers))
            dlogger.debug('number of logger handlers now = %s' % len(dlogger.handlers[:]))
            dlogger.info('logger write in %s' % log_path)
        
        for name in loggers:
            lo(name)
    
    def log_cleaner(self):
        log_list = os.listdir(env_dict['log'])
        delta_date = datetime.date.today()-datetime.timedelta(log_lifetime)
        removed = []
        for log in log_list:
            str_date = map(int,log.split('.')[0].split('-'))
            log_date = datetime.date(*str_date)
            if log_date < delta_date:
                log_path = os.path.join(env_dict['log'],log)
                os.remove(log_path)
                removed.append(log)
        if not removed:
            logger.debug('cleared file : %s' % removed)
            logger.info('log file cleared')
    
    def wait_for_midnight(self):
        self.daemonize(pidfile)
        while True:
            hour_now = datetime.datetime.now().hour
            if timeline[0] <= hour_now <= timeline[1]:
                try:
                    self.logger_init()
                    logger.info('starting new session')
                    self.log_cleaner()
                    self.checking_state(self.name)
                    logger.info('session end')
                except Exception as e:
                    err_str = 'caught unknown exception: %s: %s \n %s' % (e.__class__, e, Exception.message)
                    alert_body = err_str + '\n' + traceback.format_exc()
                    make_alert(os.path.join(env_dict['alert'], "daemon crash"), alert_body)
            time.sleep(sleeptime)

    def db_renew(self):
        config = utils.config(config_path)
        (serverList) = config.config_parse()
        self.wdb.renew(serverList)
        logger.info("database was updated")
    
    def config_par_remove(self, name):
        c = utils.config(config_path)
        c.config_remove(name)
        logger.info("parameter %s in %s was removed" % (name, config_path))
    
    def db_backup_erase(self):
        self.wdb.dropTable(backup_table)
        self.wdb.createTable()
        logger.info("database was erased")
    
    def __backup_full(self, server):
        try:
            backup = do_backup(server).full()
            self.wdb.session_save(backup)
        except BackupException, AlertBodyException:
            return
    
    def __backup_inc(self, server, last_backup):
        try:
            backup = do_backup(server).incremental(last_backup)
            self.wdb.session_save(backup)
        except BackupException, AlertBodyException:
            return
       
    def __backup_choise(self, server, backup_match):
        last_backup = max([backup for backup in backup_match])
        if utils.date_cmp(last_backup.makingtime, time_before_repeat) is not True:
            logger.info('[%s] backup state is actual' % (server.name))
            return
        if datetime.date.isoweekday(datetime.date.today()) == 1:
            self.__backup_full(server)
        else:
            last_full_backup = self.__finding_last_backup(backup_match)
            if last_full_backup is None:
                self.__backup_full(server)
            elif (os.path.isdir(last_full_backup.realpath) is True) and (os.path.exists(last_full_backup.file_path) is True):
                self.__backup_inc(server, last_full_backup)
            else:
                self.__backup_full(server)

    def __finding_last_backup(self, backup_match):            
        def change_state(current, backup):
            os.rename(backup.realpath, current)
            backup.make_path(current)
            self.wdb.session_save(backup)
            
        def make_current(backup):
            current = backup.realpath + '_current'
            change_state(current, backup)
        
        def unmake_current(backup):
            current = backup.realpath.replace('_current','')
            change_state(current, backup)
        
        full_backup_list = [backup for backup in backup_match if backup.kind == 'full']
        if not full_backup_list:
            return None
        last_full_backup = max(full_backup_list)
        logger.debug('[%s]' % last_full_backup.name)
        if 'current' not in last_full_backup.realpath:
            [unmake_current(backup) for backup in backup_match if 'current' in backup.realpath]
            make_current(last_full_backup)
        logger.info('[%s] date of last full backup is %s' % (last_full_backup.name, last_full_backup.makingtime))
        logger.debug('[%s] and his realpath is %s' % (last_full_backup.name, last_full_backup.realpath))
        return last_full_backup
    
    def clear_base(self):
        (server_list, backup_list) = self.wdb.init()
        for server in server_list:
            backup_match = [backup for backup in backup_list if backup.name == server.name]
            for backup in backup_match:
                self._delete_old(backup, server)
        logger.info("backup table is clear")
            
    def __delete_old(self, backup):
        if utils.date_cmp(backup.makingtime, inc_backup_lifetime) and (backup.kind == 'inc'):
            backup.purge()
            self.wdb.delete_old(backup)
        if utils.date_cmp(backup.makingtime, full_backup_lifetime) and (backup.kind == 'full'):
            backup.purge()
            self.wdb.delete_old(backup)
    
    def __packing_old(self, backup):
        if utils.date_cmp(backup.makingtime, time_before_packing):
            if os.path.isdir(backup.realpath) is True:
                backup.packing()
                self.wdb.session_save(backup)

    def checking_state(self, name):
        (server_list, backup_list) = self.wdb.init(name)
        for server in server_list:
            if server.do_backup == 1:
                try:
                    backup_match = [backup for backup in backup_list if backup.name == server.name]
                    if (not backup_match) or (name is not None):
                        self.__backup_full(server)
                    else:
                        self.__backup_choise(server, backup_match)
                        for backup in backup_match:
                            self.__packing_old(backup)
                            self.__delete_old(backup)
                except Exception as e:
                    err_str = '[%s] caught unknown exception: %s: %s \n %s' % (server.name, e.__class__, e, Exception.message)
                    alert_body = err_str + '\n' + traceback.format_exc()
                    make_alert(os.path.join(env_dict['alert'], "daemon crash"), alert_body)


if __name__ == "__main__":
    d = MyDaemon()
    if len(sys.argv) >= 2:
        options = sys.argv[1]
    elif len(sys.argv) == 1:
        d.wait_for_midnight()
    if 'now' == options:
        if len(sys.argv) == 3:
            d.name = sys.argv[2]
        else:
            d.name = None
        d.checking_state(d.name)
    elif 'dbrenew' == options:
        d.db_renew()
        print ("Database update complete")
    elif 'config_par_remove' == options:
        d.config_par_remove(sys.argv[2])
        print ("parameter %s in %s was removed" % (sys.argv[2], config_path))
    elif 'db-backup-erase' == options:
        d.db_backup_erase()
        print ("Backup table erase complete")
    elif 'dbclear' == options:
        d.clear_base()()
        print ("Backup table is clear")
    else:
        print ("Unknown command")
        print ("Usage: $NAME now | dbrenew | db-backup-erase")
        sys.exit(0)