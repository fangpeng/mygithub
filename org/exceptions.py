#coding=utf-8
class OperationAborted(Exception):
    '''操作失败'''
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
        
    def __str__(self):
        return self.msg

    def __unicode__(self):
        return unicode(self.msg)
