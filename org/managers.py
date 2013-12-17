#coding=utf-8
from django.db import models
from django.db import connection
from core.models import CachedManager

class OrgManager(CachedManager):
    '''机构管理器，提供一些额外方法'''
    def get_top_list(self):
        '''得到顶级机构列表'''
        return self.get_list_by_depth(0)

    def get_list_by_depth(self, depth):
        '''指定级别，得到机构列表'''
        return super(OrgManager, self).get_query_set().filter(depth__exact=depth)

    def clear_all(self):
        '''清除机构表数据'''
        cursor = connection.cursor()
        cursor.execute('delete from Org_Org')

    def get_choices(self, *args, **kwargs):
        '''
          得到机构列表选项列表
          这样使用：
            from django.forms import Select
            from Org.models import Org
            #取全部机构
            form.fields['org'].widget = Select(choices=Org.objects.get_choices())
            #可以增加过滤条件
            form.fields['org'].widget = Select(choices=Org.objects.get_choices(deleted=False))
        '''
        orgs = super(OrgManager, self).filter(*args, **kwargs).order_by('sorting_order')
        base_depth = orgs and orgs.values('depth').distinct().order_by('depth')[0]['depth'] or 0
        choices = []
        for o in orgs:
            format_str = o.deleted and u'%s%s(*已禁用*)' or '%s%s'
            choices.append((o.id, format_str % ('　'*2*(o.depth-base_depth), o)))

        choices.insert(0, ('', '-'*10))
        return choices
