import time
ISOTIMEFORMAT='%Y-%m-%d %X'
class log():
    def __init__(self):
        self.fp=None

    def write(self,keystr,args):
        timestr='[%s]:' %time.strftime(ISOTIMEFORMAT,time.localtime())
        self.fp=open('./logs/log.txt','a+')
        if keystr==None:
            Keystr='None'
        else:
            Keystr=str(keystr)
        if args==None:
            args='None'
        else:
            args=str(args)
        logstr=timestr+keystr+args+'\n'
        self.fp.write(logstr)
        self.fp.close()




