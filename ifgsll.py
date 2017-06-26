#!/usr/bin/python
#coding:utf8
#author:chengongliang

import os
import sys
import yaml
import salt.client
from optparse import OptionParser

cwd = os.getcwd()
local = salt.client.LocalClient()

def parseHost(host, **args):
	hostcnf = os.path.join(cwd,'confs','server.yaml')
	hostinfo = yaml.load(file(hostcnf))
	for i in hostinfo:
		if host in i.split('-'):
			return hostinfo[i]['hostname'][:]
	else:
		print "ip或者hostname未写入配置"
		sys.exit(1)

def parseProject(project, **args):
	projCNF = os.path.join(cwd,'confs','projects','%s.yaml' % project)
	if not os.path.exists(projCNF):
		print "%s 不存在或未配置" % project
		sys.exit(1)
	dirinfo = yaml.load(file(projCNF))
	return dirinfo

def _save2file(context, target_file):
	if os.path.exists(target_file):
		print "%s 配置已存在，请检查" % target_file
		sys.exit(1)
	else: 
		with open(target_file, 'w') as target_handle:
			target_handle.write(context)
		print "%s 创建成功" % target_file

def init_conf(project, _type):
	projCNF = os.path.join(cwd,'confs','projects','%s.yaml' % project)
	projSLS = "/srv/salt/%s/%s.sls" % (_type, project)
	www_cnf = """%s:
  type: wwwroot
  dest: /home/wwwroot/%s.test.com/
  tmp: /srv/salt/wwwroot/files/%s.test.com/
"""% (project, project, project)
	webuser_cnf = """%s:
  type: webuser
  dest: /home/webuser/%s/
  tmp: /srv/salt/webuser/files/%s/
  exclude:
    conf
    logs
    *.pid
"""% (project, project, project)
	www_sls = """/home/wwwroot/%s.test.com/:
  file.recurse:
    - source: salt://files/%s.test.com/
    - file_mode: 644
    - dir_mode: 755
    - makedir: True
    - include_empty: True
    - clean: True
"""% (project, project)
	webuser_sls = """/home/webuser/%s/:
  file.recurse:
    - source: salt://files/%s/
    - makedir: True
    - include_empty: True
    - clean: True
/home/webuser/%s/bin/:
  file.directory:
    - dir_mode: 755
    - file_mode: 755
    - recurse:
      - mode
stop:
  cmd.run:
    - name: /home/webuser/%s/bin/shutdown.sh
    - user: root
start:
  cmd.run:
    - name: /home/webuser/%s/bin/startup.sh
    - user: root
"""% (project, project, project, project, project)
	if _type == "wwwroot":
		_save2file(www_cnf, projCNF)
		_save2file(www_sls, projSLS )
	elif _type == "webuser":
		_save2file(webuser_cnf, projCNF)
		_save2file(webuser_sls, projSLS)
	else:
		print "类型错误(wwwroot|webuser)"
		sys.exit(1)

class BR:
	def __init__(self, project, destDir, **kw):
		import datetime
		today = datetime.date.today()
		BACK_DIR = "/home/ifgsll/backup/"
		self.backDir = BACK_DIR + today.isoformat()
		self.p_back = self.backDir + '/' + destDir.split('/')[-2] + '/'

	def backup(self, project, destDir):
		if not os.path.exists(self.backDir):
			os.makedirs(self.backDir)
		rsync = "rsync -avp --delete %s %s" % (destDir, self.p_back)
		os.system(rsync)
		
	def rollback(self, project, destDir):
		rsync = "rsync -avp --delete %s %s" % (self.p_back, destDir)
		os.system(rsync)

def rsync(testServer,destDir,exclude):
	cmd = 'rsync -apv --delete --exclude={%s} %s:%s %s' % (exclude, testServer, destDir, destDir)
	if not os.path.exists(destDir):
		os.makedirs(destDir)
	os.system(cmd)

def getPID(host, project):
	cmd = "ps -ef|grep -v grep|grep %s" % project
	salt_cmd = local.cmd(host,'cmd.run',[cmd])
	if salt_cmd.values()[0] == '':
		print "程序未运行."
		sys.exit(0)
	else:
		pid = salt_cmd.values()[0].replace('  ','').split(' ')[1]
		return pid

def startTomcat(hostname, destDir):
	binPath = destDir + "bin"
	cmd = "sh %s/startup.sh" % binPath
	print local.cmd(hostname,'cmd.run',[cmd])
	project = destDir.split('/')[-2]

def stopTomcat(hostname, destDir):
	pid = getPID(hostname, destDir)
	cmd = "kill -9 %s" % pid
	local.cmd(hostname,'cmd.run',[cmd])
	project = destDir.split('/')[-2]
	try:
		print "%s 的进程已停止,PID: %s" % (project, pid)
	except Exception, e:
		print "%s 停止失败" % project

def update(hostname, project, exclude, destDir, tmpDir, env):
	sync = 'rsync -ap --delete --exclude={%s} %s %s' % (exclude, destDir, tmpDir)
	if not os.path.exists(tmpDir):
		os.makedirs(tmpDir)
	os.system(sync)
	salt_info = local.cmd(hostname,"state.sls",[project,env])
	dic = salt_info.values()[0].values()[0]
	Host = salt_info.keys()[0]
	comment = dic.get('comment')
	result = dic.get('result')
	path = dic.get('name')
	starttime = dic.get('start_time')
	changes = dic.get('changes')
	duration = dic.get('duration')
	info = """Hostname: %s
Project: %s
Result: %s
Duration: %s
Start_time: %s
Path: %s
Comment: %s
Changes: %s
"""% (Host, project, result, duration, starttime, path, comment, changes)
	print info

def main():
	parser = OptionParser()
	parser.add_option('-p','--porject',
					dest='project',
					action='store',
					help='order,tem-order')
	parser.add_option('-l','--host',
					dest='host',
					action='store',
					help='host')
	parser.add_option('-c','--command',
					dest='command',
					action='store',
					help='rsync,update,rollback,start,stop,restart,init')
	parser.add_option('-t','--type',
					dest='type',
					action='store',
					help='wwwroot,webuser')
	options, args = parser.parse_args()

	host = options.host
	project = options.project
	cmd = options.command
	_type = options.type
	
	if not project:
		os.system('%s --help'%__file__)
		sys.exit()
		
	if not cmd == "init":
		dirinfo = parseProject(project)
		env = dirinfo.get(project)['type']
		destDir = dirinfo[project]['dest'][:] 
		exclude = ','.join(dirinfo.get(project)['exclude'].split(' '))

	if cmd == 'rsync':
		br = BR(project, destDir)
		br.backup(project, destDir)
		if env == 'wwwroot':
			testServer = '192.168.1.210'
			rsync(testServer, destDir, exclude)
		elif env == 'webuser':
			testServer = '192.168.1.210'
			rsync(testServer, destDir, exclude)
	elif cmd == 'update':
		if host == None:
			print "请指定host"
			sys.exit(1)
		hostname = parseHost(host)
		tmpDir = dirinfo.get(project)['tmp']
		update(hostname, project, exclude, destDir, tmpDir, env)
	elif cmd == 'rollback':
		br = BR(project, destDir)
		br.rollback(project, destDir)
	elif cmd == 'stop':
		if env == 'webuser':
			hostname = parseHost(host)
			stopTomcat(hostname, destDir)
	elif cmd == 'start':
		if env == 'webuser':
			hostname = parseHost(host)
			print hostname
			startTomcat(hostname, destDir)
	elif cmd == 'restart':
		if env == 'webuser':
			hostname = parseHost(host)
			stopTomcat(hostname, destDir)
			startTomcat(hostname, destDir)
	elif cmd == 'init':
		if _type:
			init_conf(project, _type)
		else:
			print "必须指定项目类型(wwwroot|webuser)"
			sys.exit()
	else:
		print "未知命令!\n请使用 %s -h 查看帮助信息" % __file__
		sys.exit(1)
	
if __name__ == "__main__":
	main()
