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
from modules.utils import dt

import time
import os
import logging
import shutil
import sys
import datetime
import traceback
import subprocess
import multiprocessing
from multiprocessing import Process, Event

#  Глобальные переменные
host_table = "hosts"
backup_table = "backup"
prefix = "/home/datastore/"
env = ["alert", "store", "config", "log"]
env_dict = utils.makeEnv(prefix, env)
dbpath = os.path.join(env_dict['config'], "database.db")
config_path = os.path.join(env_dict['config'], "config.ini")
pidfile = "/var/run/backup.pid"

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
    f = open(filename, "w+")
    f.write(alert_body)
    f.close()


class BackupException(Exception):
    def __init__(self, estr, alert_body=''):
        self.err_str = estr
        make_alert(os.path.join(env_dict['alert'], self.err_str), alert_body)
        logger.error(self.err_str)

    def __str__(self):
        return self.err_str


class do_backup(object):
    def __init__(self, server):
        self.server = server
        self.backup_path = makingpath(self.server)
        self.connection_alert_path = os.path.join(env_dict['alert'], "[%s] connection failed" % (self.server.name))
        self.backup = userclass.backup(name=self.server.name, makingtime='now', realpath=self.backup_path)

    def connect(self):
        try:
            self.connection = selfssh.Connection(self.server)
            logger.debug('[%s] connection established' % (self.server.name))
        except Exception as e:
            alert = '[%s] connection failed with exception: %s: %s' % (self.server.name, e.__class__, e)
            logger.warning(alert)
            make_alert(self.connection_alert_path, alert)
            self.destroy()
            return False

    def full(self):
        logger.info('[%s] processing full backup' % (self.server.name))
        self.prev_backup_path = None
        self.body()
        return self.backup

    def incremental(self, prev_backup):
        logger.info('[%s] processing incremental backup' % (self.server.name))
        p = os.path.join(prev_backup.realpath, 'file')
        if (os.path.isdir(prev_backup.realpath) is True) and (os.path.exists(p) is True):
            self.prev_backup_path = p
            subprocess.call('cp -ru %s %s' % (self.prev_backup_path, self.backup_path + os.sep), shell = True)
#             shutil.copytree(self.prev_backup_path, os.path.join(self.backup_path, u'file'), symlinks=True)
        else:
            self.prev_backup_path = None
        self.body()
        return self.backup

    def body(self):
        t1 = time.time()
        for n in range(0,3):
            cans = self.connect()
            if cans is not False:
                break
        del n
        if cans is False:
            self.raise_exception("[%s] can't connect..." % (self.server.name))
        if self.server.schema_flag == 1:
            self.schema_backup()
        if self.server.file_flag == 1:
            self.file_backup()
        t2 = time.time()
        logger.info('[%s] creating backup complete' % (self.server.name) + dt(t1, t2))
        self.alert_destroy()

    def check_schema(self):
#         if not os.path.exists(self.backup.realpath):
#             self.raise_exception("[%s] backup doesn't exist" % (self.server.name))
        if not os.path.exists(self.backup.schema_path):
            self.raise_exception("[%s] schema backup doesn't exist" % (self.server.name))
        elif not os.listdir(self.backup.schema_path):
            self.raise_exception("[%s] schema backup doesn't exist" % (self.server.name))

    def check_file(self):
#         if not os.path.exists(self.backup.realpath):
#             self.raise_exception("[%s] backup doesn't exist" % (self.server.name))
        if not os.path.exists(self.backup.file_path):
            self.raise_exception("[%s] file backup doesn't exist" % (self.server.name))
        elif not os.listdir(self.backup.file_path):
            self.raise_exception("[%s] file backup doesn't exist" % (self.server.name))

    def schema_backup(self):
        self.connection.schemas_backup(self.backup_path)
        logger.info('[%s] creating schema backup complete' % self.server.name)
        self.check_schema()

    def file_backup(self):
        self.check_size = self.connection.check_file_size()
        if self.check_size is True:
            self.connection.get_file_rsync(self.prev_backup_path, self.backup)
#             watcher_event = Event()
#             self.prisoner = Process(target=self.rsync_launcher, args=(watcher_event,))
#             self.watcher = Process(target=self.rsync_destroyer, args=(watcher_event,))
#             self.prisoner.start()
#             self.watcher.start()
#             self.prisoner.join()
#             self.watcher.join()
            logger.info('[%s] creating file backup complete' % self.server.name)
        else:
            self.raise_exception("[%s] exceeded backup size" % self.server.name, alert_body = self.check_size)
        self.check_file()
    
    def rsync_launcher(self, watcher_event):
        watcher_event.set()
        self.connection.get_file_rsync(self.prev_backup_path, self.backup)
        self.watcher.terminate()
    
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
        self.raise_exception("[%s] rsync freeze and watcher destroy him" % (self.server.name))

    def alert_destroy(self):
        for name in os.listdir(env_dict['alert']):
            if self.server.name in name:
                os.remove(os.path.join(env_dict['alert'], name))
        logger.debug("[%s] all alert destroyed" % (self.server.name))
    
    def raise_exception(self,except_string):
        self.destroy()
        raise BackupException(except_string)
    
    def destroy(self):
        logger.warning("[%s] destroyer started" % (self.server.name))
        if os.path.exists(self.backup.realpath) is True:
            shutil.rmtree(self.backup.realpath)
            logger.warning("[%s] all data was destroy" % (self.server.name))


class MyDaemon(utils.Daemonize):
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
#             [dlogger.removeHandler(h) for h in current_handlers]
            [h.close() for h in current_handlers]
            dlogger.addHandler(log_handler)
            dlogger.debug('number of logger handlers were removed = %s' % len(current_handlers))
            dlogger.debug('number of logger handlers now = %s' % len(dlogger.handlers[:]))
            dlogger.info('logger write in %s' % log_path)
        
        for name in loggers:
            lo(name)
    
    def log_cleaner(self):
        day_number = 30 # количество дней жизни
        log_list = os.listdir(env_dict['log'])
        delta_date = datetime.date.today()-datetime.timedelta(day_number)
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
        sleeptime = 600 # Время ожидания до повторной проверки
        timeline = [2,6] # Интервал работы в 24-x часовом формате
        self.daemonize(pidfile)
        while True:
            hour_now = datetime.datetime.now().hour
            if (hour_now >= timeline[0]) and (hour_now <= timeline[1]):
                try:
                    self.logger_init()
                    logger.info('starting new session')
                    self.log_cleaner()
                    self.checking_state(self.name)
                    logger.info('session end')
                except Exception as e:
                    err_str = 'caught unknown exception: %s: %s /n %s' % (e.__class__, e, Exception.message)
                    logger.critical(err_str)
                    make_alert(os.path.join(env_dict['alert'], "daemon crash"), err_str + '\n' + traceback.format_exc())
            time.sleep(sleeptime)

    def db_renew(self):
        config = utils.config(config_path)
        (serverList) = config.config_parse()
        self.wdb.renew(serverList)

    def db_backup_erase(self):
        self.wdb.dropTable(backup_table)
        self.wdb.createTable()
    
    def _backup_full(self, server):
        try:
            backup = do_backup(server).full()
            self.wdb.session_save(backup)
        except BackupException:
            return
    
    def _backup_inc(self, server, last_backup):
        try:
            backup = do_backup(server).incremental(last_backup)
            self.wdb.session_save(backup)
        except BackupException:
            return

    def _finding_last_backup(self, backup_match):
        last_backup = max(backup_match)
        return last_backup
    
    def clear_base(self):
        (server_list, backup_list) = self.wdb.init()
        for server in server_list:
            backup_match = [backup for backup in backup_list if backup.name == server.name]
            for backup in backup_match:
                self._delete_old(backup, server)
            
    def _delete_old(self, backup, server):
        if utils.date_cmp(backup.makingtime, server.lifetime):
            backup.purge_oldest()
            self.wdb.delete_old(backup)
    
    def _packing_old(self, backup, server):
        if utils.date_cmp(backup.makingtime, server.ltbp):
            if os.path.isdir(backup.realpath) is True:
                backup.packing()
                self.wdb.session_save(backup)
    
    def _backup_choise(self, backup_tool, last_backup, server):
        if utils.date_cmp(last_backup.makingtime, server.tbr):
            if datetime.date.isoweekday(datetime.date.today()) == 1:
                self._backup_full(backup_tool)
            else:
                self._backup_inc(backup_tool, last_backup)
        else:
            logger.info('[%s] backup state is actual' % (server.name))
        
    def checking_state(self, name):
        (server_list, backup_list) = self.wdb.init(name)
        for server in server_list:
            if server.do_backup == 1:
                backup_match = [backup for backup in backup_list if backup.name == server.name]
                if (not backup_match) or (name is not None):
                    self._backup_full(server)
                else:
                    last_backup = self._finding_last_backup(backup_match)
                    self._backup_choise(server, last_backup, server)
                    for backup in backup_match:
                        self._delete_old(backup, server)
                        self._packing_old(backup, server)


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
    elif 'db-backup-erase' == options:
        d.db_backup_erase()
        print ("Backup table erase complete")
    else:
        print ("Unknown command")
        print ("Usage: $NAME now | dbrenew | db-backup-erase")
        sys.exit(0)