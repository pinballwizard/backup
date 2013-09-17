# -*- coding: utf-8 -*-
'''
Created on 12.03.2013

@author: Karbovnichiy Vasiliy <menstenebris@gmail.com>
'''

import os
import utils
import datetime
import logging

logger = logging.getLogger('backup')

class server(object):
    '''
    Класс информации о сервере
    '''
    def __init__(self, name, do_backup, host, user, port, secret, ora_home, ora_sid, ora_sys, ora_lang, base_addres, base_port, rsync_add,
                 exclude, include, schemas, maxsize, file_flag, schema_flag, remote_flag, operator, location):
        
        self.do_backup = do_backup
        self.name = name                                    # Имя хоста
        self.operator = operator                            # Мобильный оператор
        self.location = location                            # Расположение
        self.host = host                                    # IP адресс хоста
        self.user = user                                    # Имя пользователя
        self.secret = secret                                # Пароль
        self.port = port                                    # Порт
        self.ora_home = ora_home                            # Переменная $ORACLE_HOME из окружения пользователя oracle на сервере
        self.ora_sid = ora_sid                              # SID базы на сервере
        self.ora_sys = ora_sys                              # Параметры подключения пользователя sys
        self.ora_lang = ora_lang                            # Кодировка базы
        self.base_addres = base_addres                      # IP-адрес (или DNS-имя) для подключения к базе
        self.base_port = base_port                          # порт для подключения к базе
        self.rsync_add = rsync_add                          # дополнительные опции rsync
        self.exclude = exclude                              # маски исключений
        self.include = include                              # каталоги для копирования
        self.schemas = schemas                              # схемы для базы данных Oracle
        self.maxsize = maxsize                              # Максимальный размер
        self.file_flag = file_flag                          # Флаг бэкапа файлов
        self.schema_flag = schema_flag                      # Флаг бэкапа схему
        self.remote_flag = remote_flag                      # Бэкап схемы локально или удаленно
        self.init_errors()
        
    def init_errors(self):
        if (self.file_flag == 0) and (self.schema_flag == 0) and (self.do_backup == 1):
            logger.warning('[%s] Database warning: backup type flag is missing!!!' % (self.name))

    def todict(self):
        return {'name':self.name, 'operator':self.operator, 'location':self.location, 'host':self.host, 'user':self.user, 'port':self.port,
                'secret':self.secret, 'ora_home':self.ora_home, 'ora_sid':self.ora_sid, 'ora_sys':self.ora_sys, 'ora_lang':self.ora_lang,
                'base_addres':self.base_addres,'base_port':self.base_port,'rsync_add':self.rsync_add, 'exclude':self.exclude,'include':self.include,
                'schemas':self.schemas, 'maxsize':self.maxsize, 'file_flag':self.file_flag, 'schema_flag':self.schema_flag,
                'remote_flag':self.remote_flag, 'do_backup':self.do_backup}

class backup(object):
    '''
    Класс настроек бэкапа
    '''
    def __init__(self, name, makingtime, realpath, kind, file_size = None, schema_size = None):
        self.name = name                                            # Должно совпадать с названием сервера
        self.make_path(realpath)
        self.kind = kind
        if (file_size is None) and (schema_size is None):
            self.get_size()
        else:
            self.file_size = file_size
            self.schema_size = schema_size
        if type(makingtime) is unicode:
            string = [int(x) for x in makingtime.split('-')]
            self.makingtime = datetime.date(*string)
        elif makingtime == "now":
            self.makingtime = datetime.date.today()
        else:
            self.makingtime = makingtime
    
    def make_path(self, s):
        self.realpath = s
        self.file_path = os.path.join(self.realpath, 'file')
        self.schema_path = os.path.join(self.realpath, 'schemas')
    
    def get_size(self):
        if os.path.exists(self.file_path):
            self.file_size = utils.getFolderSize(self.file_path) # Текущий размер файлов
        else:
            self.file_size = None
        if os.path.exists(self.schema_path):
            self.schema_size = utils.getFolderSize(self.schema_path) # Текущий размер схем
        else:
            self.schema_size = None
            
    def __lt__(self, other):
        return self.makingtime < other.makingtime

    def purge(self):
        if os.path.exists(self.realpath):
            os.remove(self.realpath)
        logger.info('[%s] backup %s has been removed' % (self.name, self.realpath))
    
    def packing(self):
        self.realpath = utils.tarFolder(self.realpath)
        logger.info('[%s] backup %s has been packing' % (self.name, self.realpath))
    
    def todict(self):
        return {'name':self.name, 'file_size':self.file_size, 'schema_size':self.schema_size,
                'realpath':self.realpath, 'makingtime':self.makingtime, 'kind':self.kind}

class mainConfig():
        host_table = "hosts"
        backup_table = "backup"
        prefix = "/home/datastore2/"
        pidfile = "/var/run/backup.pid"
        full_backup_lifetime = 180 # количество дней жизни полного бэкапа
        inc_backup_lifetime = 14 # количество дней жизни инкрементного бэкапа
        time_before_packing = 7 # количество дней до упаковки бэкапа
        time_before_repeat = 1
        log_lifetime = 30 # количество дней жизни логов
        timeline = (8,22) # интервал работы в 24-x часовом формате
        sleeptime = 600 # время ожидания до повторной проверки
        
        def __init__(self):
            try:
                self.read_conf()
            except:
                logger.warn("can't read init config. using default parameters")
            self.make_env()
            self.make_logger()
        
#         def read_conf(self):
            
#             self.host_table = host_table
#             self.backup_table = backup_table
#             self.prefix = prefix
#             self.pidfile = pidfile
#             self.full_backup_lifetime = full_backup_lifetime
#             self.inc_backup_lifetime = inc_backup_lifetime
#             self.time_before_packing = time_before_packing
#             self.time_before_repeat = time_before_repeat
#             self.log_lifetime = log_lifetime
#             self.timeline = timeline
#             self.sleeptime = sleeptime
        
        def make_env(self):
            env = ["alert", "store", "config", "log"]
            self.env_dict = utils.makeEnv(self.prefix, env)
            self.dbpath = os.path.join(self.env_dict['config'], "database.db")
            self.config_path = os.path.join(self.env_dict['config'], "config.ini")
            
        def make_logger(self):
            self.logger = logging.getLogger('backup')
            self.logger.setLevel(level=logging.DEBUG)
            # mlogger = multiprocessing.get_logger()
            # mlogger.setLevel(level=logging.DEBUG)
            self.loggers = (logger,)