# -*- coding: utf-8 -*-
'''
Created on 12.03.2013

@author: Karbovnichiy Vasiliy <menstenebris@gmail.com>
'''
import paramiko
import os
import utils
import logging
import subprocess

logger = logging.getLogger('backup')

class DefConnection(object):
    connection_timeout = 60
    session_timeout = 20
    console_line = 2048
    
    def __init__(self, server):
        self.server = server
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname = server.host, port = server.port, username = server.user, password = server.secret, timeout = self.connection_timeout)
        self.channel = self.client.get_transport()
        
    def exec_command(self, command):
        '''
        Подключение по SSH и выполнение комманды указанной ввиде строки
        '''
        session = self.channel.open_session()
        session.settimeout(self.session_timeout)
        session.exec_command(command)
        session.recv_exit_status()
        answer = session.recv(self.console_line)
        session.close()
        return answer

    def get_file_sftp(self, remotepath, localpath): # неработает
        '''
        Получение указанного файла по SSH
        '''
        sftp = paramiko.SFTPClient.from_transport(self.channel)
        sftp.get(remotepath, localpath)
        sftp.close()
                
    def get_dir_sftp(self, remotedir, localdir):
        '''
        Получение указанной директории по SSH
        '''
        sftp = paramiko.SFTPClient.from_transport(self.channel)       
        if os.path.exists(localdir) is False:
            os.makedirs(localdir)
        list_dir = sftp.listdir(remotedir)
        for name in list_dir:
            sftp.get(os.path.join(remotedir,name), os.path.join(localdir,name))
        sftp.close()
        
    def close(self):
        self.channel.close()
        self.client.close()
    
class Connection(DefConnection):
    def get_file_rsync(self, prev_backup_path, backup):
        include_string = " ".join(["%s@%s:%s" % (self.server.user, self.server.host, n) for n in self.server.include.split(';')])
        exclude_string = " ".join(["--exclude=%s" % (n) for n in self.server.exclude.split(';')])
#         delta_backup_path = os.path.join(backup.realpath, u'delta')
        
        if prev_backup_path is not None:
            rsync = '''rsync -vrpmgoztWRl --rsh="sshpass -p '%s' ssh -p %s"''' % (self.server.secret, self.server.port)
#             rsync = '''rsync -vrpmgoztWRl --force --delete --delete-excluded --backup --backup-dir="%s" --rsh="sshpass -p '%s' ssh -p %s"''' % (delta_backup_path, self.server.secret, self.server.port)
        else:
            utils.makingPath(backup.file_path)
            rsync = '''rsync -vrpmgoztWRl --rsh="sshpass -p '%s' ssh -p %s"''' % (self.server.secret, self.server.port)
        
        command = " ".join([rsync, include_string, exclude_string, backup.file_path])
        logger.debug("[%s] executing %s" % (self.server.name, command))
        answ = subprocess.Popen(command, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print (answ.stdout.read())
#         logger.debug(answ.stderr.read())
#         err = answ.stderr.read()
#         if err != '':
#             logger.warning(answ.stderr.read())
        logger.info("[%s] synchronize files complete" % (self.server.name))
        return answ
     
    def schemas_backup(self, backup_path):
        '''
        Получение таблиц из Oracle DB
        '''
        localpath = os.path.join(backup_path, "schemas")
        schema_dir = "/tmp/schemas"
        schema_name = "schema_%s.dmp" % (self.server.name)
        schema_path = os.path.join(schema_dir,schema_name)
        tns_admin = os.path.join(self.server.ora_home, 'network/admin')
        source = " ".join(["export ORACLE_HOME=%s;" % (self.server.ora_home), # повторная загрузка переменных окружения
                           "export NLS_LANG=%s;" % (self.server.ora_lang),
                           "export TNS_ADMIN=%s;" % (tns_admin)])
        schemas = self.server.schemas.split(';')
        schema_name2 = map(lambda x:"schema_%s_%s.dmp" % (self.server.name,x), range(1,len(schemas)))
        schema_path2 = map(lambda x: os.path.join(schema_dir,x), schema_name2)
        schemas2 = ','.join([d.split('/')[0] for d in schemas])
        ora_home = os.path.join(self.server.ora_home, 'bin/exp')
        sys_save_table = source + " nice -n 19 %s \\'%s@%s as sysdba\\' FILE=%s OWNER=%s ROWS=N" % (ora_home, self.server.ora_sys, self.server.ora_sid, schema_path, schemas2)
        save_table = map(lambda x,y: source + " nice -n 19 %s %s@%s FILE=%s ROWS=N" % (ora_home, x, self.server.ora_sid, y), schemas, schema_path2)
        
        if self.server.remote_flag == 1:
            self.exec_command("mkdir -p %s" % schema_dir)
            if (self.server.ora_sys is not None) or (self.server.ora_sys != ""):
                logger.debug('[%s] executing %s' % (self.server.name, sys_save_table))
                self.exec_command(sys_save_table)
            else:
                [logger.debug('[%s] executing %s' % self.server.name, table) for table in save_table]
                [self.exec_command(table) for table in save_table]
            try:
                self.get_dir_sftp(schema_dir, localpath)
            except:
                logger.error('[%s] cant find %s' % (self.server.name, schema_dir))
                return False
            self.exec_command("rm -r %s" % schema_dir)
        else:
            logger.critical('[%s] need enable remote block' % self.server.name)
            
        logger.info(u'[%s] oracle schema has been successfully backup' % self.server.name)
        return localpath
        
    def check_file_size(self):
        include_string = " ".join(self.server.include.split(';'))
        exclude_string = " ".join(["--exclude=%s" % (n) for n in self.server.exclude.split(';')])
        
        rsync_ans_remote = '/tmp/rsync_ans.txt'
        rsync_ans_local = '/home/rsync_ans.txt'
        
        command = "rsync -vrmWRil --ignore-errors --list-only %s %s '' >> %s" % (include_string, exclude_string, rsync_ans_remote)
        command2 = "cat %s | tail -1" % (rsync_ans_remote)
        
        logger.debug("[%s] executing %s" % (self.server.name, command))
        self.exec_command(command)
        logger.debug("[%s] executing %s" % (self.server.name, command2))
        answer = self.exec_command(command2)
        
        self.get_file_sftp(rsync_ans_remote, rsync_ans_local)
        with open(rsync_ans_local) as f:
            rs = f.read()
        self.exec_command("rm %s" % (rsync_ans_remote))
        os.remove(rsync_ans_local)
        
        try:
            filesize = float(answer.split()[3])/10**6
        except Exception as e:
            logger.error('[%s] connection failed with exception: %s: %s' % (self.server.name, e.__class__, e))
            return rs
        
        logger.info("[%s] total size is %s speedup is %s" % (self.server.name, filesize, answer[:-1].split()[-1]))
        logger.info("[%s] server maxsize = %s" % (self.server.name, self.server.maxsize))
        
        if filesize > self.server.maxsize:
            log_err = "[%s] exceeded backup size at %s MB" % (self.server.name, (filesize - self.server.maxsize))
            logger.error(log_err)
            return log_err + "\n\n\n" + rs
        else:
            return True