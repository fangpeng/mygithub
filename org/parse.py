#coding=utf-8
import re
import sys
from uuid import uuid4
from models import Org, org_categories
from django.db import transaction
from django.utils.encoding import force_unicode
from django.db import connection

def test_file(file):
    stack = []
    indent = ' '*3
    travel_depth = 0
    lines = open(file).readlines()
    for line in lines:
        current = re.sub('[\n\r]', '', line)
        depth = current.count(indent)
        current = current.strip()
        if depth == travel_depth:
            if stack:
                stack.pop()
            stack.append(current)
            print '/'.join(stack)
        elif depth > travel_depth:
            travel_depth = depth
            stack.append(current)
            print '/'.join(stack)
        else:
            for i in range(travel_depth-depth+1):
                stack.pop()
            stack.append(current)
            print '/'.join(stack)
            travel_depth = depth

def create_org(parent, name, seq):
    org = Org()
    org.parent = parent
    if not isinstance(name, unicode):
        name = force_unicode(name.strip().decode('gbk'))
    code,name = name.split(',',2)
    org.code = code.strip()
    org.name = name.strip()
    org.seq = seq
    org.category = org_categories[-1][0] #使用最后一个类别
    return org

@transaction.commit_manually
def import_from_file(file, parent_org=None, reset_table=False, indent=' '*4, quiet=True):
    '''
    从磁盘文件生成机构表数据或者将文件中生成的机构作为独立片段附加到parent_org
    file 要导入到文件
    parent_org 附加到指定机构（作为下级）
    reset_table True=导入前清除机构表
    indent 缩进（如果文件中的缩进不一致，生成的机构信息可能有错误）
    quiet True=打印提示信息
    '''
    if not hasattr(file, 'readlines'):
        lines = open(file).readlines()
    else:
        lines = file.readlines()
    try:
        stack = []
        travel_depth = 0
        seq_dict = {}
        counter = 0
        if not parent_org and reset_table:
            Org.objects.all().delete()
        for line in lines:
            counter += 1
            current = re.sub('[\n\r]', '', line).rstrip() #滤掉回车换行，并去除右导空格
            if not len(re.sub('[\s]', '', current)): continue #忽略空行
            depth = current.count(indent)
            #print '+', current, travel_depth, current.count(indent), '/'.join(map(unicode, stack))
            for i in range(travel_depth-depth+1):
                if not stack: break
                stack.pop()
            parent = stack and stack[-1] or parent_org
            seq_dict[len(stack)] = seq_dict.setdefault(len(stack), -1) + 1 #得到这个深度的当前序号
            if parent_org and parent == parent_org:
                #如果指定附加到某机构，必须取该机构目前可用的子机构seq，然后+1作为seq值
                siblings = parent_org.get_children().order_by('-seq')
                org = create_org(parent, current, siblings and (siblings[0].seq + 1) or 0)
            else:
                org = create_org(parent, current, seq_dict[len(stack)])
            org.save()
            stack.append(org)
            travel_depth = depth
    except Exception, e:
        transaction.rollback()
        if not quiet: print 'failed! line:', counter, e
        raise
    else:
        transaction.commit()
        if not quiet: print 'done!'

def show_all(file=sys.stdout):
    '''显示机构表结构'''
    for org in Org.objects.all().order_by('sorting_order'):
        print >> file, '%s%s\t\t%s\tdepth(%s)\tseq(%s)' % ('\t' * org.depth, unicode(org), org.sorting_order, org.depth, org.seq,)

def reset_pinyin():
    for org in Org.objects.all():
        org.pinyin = ''
        org.save()