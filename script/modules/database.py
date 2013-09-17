# -*- coding: utf-8 -*-
'''
Created on 11.03.2013

@author: Karbovnichiy Vasiliy <menstenebris@gmail.com>
'''
import sqlite3
import sys
import time
import os
import userclass
import shutil
import logging
from utils import dt

logger = logging.getLogger('backup')

class DefDB(object):
    def __init__(self,dbpath = "database.db"):
        self.dbpath = dbpath
        try:
            self.conn = sqlite3.connect(self.dbpath)
        except Exception as e:
            logger.critical("can't open database: %s: %s" % (e.__class__, e))
   
    def execute(self, *command):
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute(*command)
        return c
    
    def cursor(self):
        self.conn.row_factory = sqlite3.Row
        return self.conn.cursor()
    
    def executeMany(self, *command):
        c = self.conn.cursor()
        c.executemany(*command)
        return c
        
    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()
    
    def dropTable(self,table_name):
        self.execute('''DROP TABLE IF EXISTS %s''' % (table_name))
        self.commit()
        logger.info('table "%s" was dropped' % (table_name))
    
class DB(DefDB):
    def createTable(self):
        try:
            self.execute('''CREATE TABLE IF NOT EXISTS hosts (
                        name TEXT UNIQUE PRIMARY KEY,
                        do_backup INTEGER,
                        operator TEXT,
                        location TEXT,
                        host TEXT,
                        user TEXT,
                        port INTEGER,
                        secret TEXT,
                        ora_home TEXT,
                        ora_sid TEXT,
                        ora_sys TEXT,
                        ora_lang TEXT,
                        base_addres TEXT,
                        base_port INTEGER,
                        rsync_add TEXT,
                        exclude TEXT,
                        include TEXT,
                        schemas TEXT,
                        maxsize REAL,
                        file_flag INTEGER,
                        schema_flag INTEGER,
                        remote_flag INTEGER
                        )''')
            self.execute('''CREATE TABLE IF NOT EXISTS backup (
                        name TEXT,
                        file_size REAL,
                        schema_size REAL,
                        makingtime TEXT,
                        realpath TEXT,
                        kind TEXT,
                        UNIQUE(name,makingtime)
                        FOREIGN KEY(name) REFERENCES hosts(name)
                        )''')
            self.commit()
        except Exception as e:
            logger.critical("failed creating table: %s: %s" % (e.__class__, e))
            sys.exit()

class currentDB(DB):
   
    def __init__(self, dbpath, host_table, backup_table):
        DB.__init__(self, dbpath)
        self.dbpath = dbpath
        self.host_table = host_table
        self.backup_table = backup_table
        
    def renew(self, server_list):
        t1 = time.time()
        if os.path.exists(self.dbpath) is True:
            shutil.copy(self.dbpath, self.dbpath + "~")
        self.dropTable(self.host_table)
        self.createTable()
        for name in server_list:
            nd = name.todict()
            column = ','.join(nd.keys())
            values = ',:'.join(nd.keys())
            self.execute('INSERT OR REPLACE INTO %s (%s) VALUES(:%s)' % (self.host_table, column, values), nd)
        self.commit()
        t2 = time.time()
        logger.info('update database complete' + dt(t1,t2))

    def init(self, name = None):
        t1 = time.time()
        if name is not None:
            where = 'WHERE name = "%s"' % (name)
        else:
            where = ''
        f = lambda table: [dict(zip(string.keys(),string)) for string in self.execute("SELECT * FROM %s %s" % (table, where)).fetchall()]
        server = [userclass.server(**string) for string in f(self.host_table)]
        backup = [userclass.backup(**string) for string in f(self.backup_table)]
        t2 = time.time()
        logger.info('initialize database complete' + dt(t1,t2))
        return (server, backup)
    
    def session_save(self, backup):
        nd = backup.todict()
        column = ','.join(nd.keys())
        values = ',:'.join(nd.keys())
        self.execute('INSERT OR REPLACE INTO %s (%s) VALUES(:%s)' % (self.backup_table, column, values), nd)
        self.commit()
        logger.info('[%s] backup save complete' % (backup.name))
    
    def delete_old(self, backup):
        self.execute('''DELETE FROM backup WHERE name = :name''', {u'name' : backup.name})
        self.commit()