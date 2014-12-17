#coding=utf-8
import sys
from django.db import models
from django.utils.encoding import force_unicode
from managers import OrgManager
from core.models import CachedModel
from exceptions import OperationAborted
from utils.getHZPy import makeSpellCode

#机构类型
org_categories = (
    (0, u'非业务'),#仅由系统使用，编号0保留
    (1, u'旅游集团'),
    (2, u'邮政'),
    (3, u'其它'),
    (4, u'邮政企业'),
    (5, u'分景点')
)

class Org(CachedModel):
    '''
    机构基础类
    使用时请注意：depth<1000, seq<1000
               机构树深度不能超过1000, 每个机构的直接下级不能超过1000(所有下级的数目总和无限制)
    '''
    category = models.IntegerField(u'机构类型', choices=org_categories, default=7)
    code = models.CharField(u'编码', max_length=200, unique=True)
    name = models.CharField(u'名称', max_length=200)
    abbreviation = models.CharField(u'简称', max_length=50, blank=True, default='')
    pinyin = models.CharField(u'拼音', max_length=20, editable=False)
    parent = models.ForeignKey('self', verbose_name=u'上级机构', null=True, blank=True)
    depth = models.IntegerField(u'级别', editable=False)
    path = models.CharField(u'路径', max_length=2000, editable=False)
    seq = models.IntegerField(u'顺序', help_text=u'确定该机构在同级列表中的顺序', default=0)
    sorting_order = models.CharField(u'排序', max_length=3000, editable=False)
    deleted = models.BooleanField(verbose_name=u'已删除', default=False, editable=False)
    flag1 = models.BooleanField(verbose_name=u'入库', default=False, db_index=True)
    flag2 = models.BooleanField(verbose_name=u'出库', default=False, db_index=True)
    flag3 = models.BooleanField(verbose_name=u'售票', default=False, db_index=True)
    flag4 = models.BooleanField(verbose_name=u'检票', default=False, db_index=True)

    objects = OrgManager()#扩展管理器

    def __unicode__(self):
        return force_unicode(self.name)

    class Meta:
        unique_together = (('name', 'parent',),)
        verbose_name = u'机构'
        permissions = (('manage', u'维护机构'), ('manage_group', u'维护角色'),)

    def _get_search_path(self):
        '''得到搜索路径，用于查找下级机构'''
        return u'%s%s/' % (self.path, self.id ,)

    def save(self, force_insert=False, force_update=False):
        #sorting_order, seq不能大于999
        self.seq = self.seq % 1000
        #强制depth, path为合理的值
        if not self.parent:
            self.depth = 0
            self.path = '/'
            self.sorting_order = str(self.seq).rjust(3, '0')
        else:
            if self.parent == self:
                raise OperationAborted(u'机构的上级不能是它自己')
            if not self.parent.id: #检查上级机构
                raise OperationAborted(u'如果指定了上级机构，那么它必须存在')
            self.depth = self.parent.depth + 1
            self.path = '%s%s/' % (self.parent.path, self.parent.id,)
            self.sorting_order = '%s%s' % (self.parent.sorting_order, str(self.seq).rjust(3, '0'))
        #补充拼音
        if self.name and not self.pinyin:
            self.pinyin = makeSpellCode(self.name.encode('gbk'))

        descendants = Org.objects.none() # 存放必须同时更新的下级机构
        #判断是否将引起下级机构迁移，如果修改已有机构的上级，必须同时更新所有下级机构的深度和路径
        if self.id is not None:
            #当前操作是修改已有机构，取得未保存前的机构信息
            old_org = Org.objects.get(pk=self.id)
            #如果deleted值被修改，属于“删除（标记为删除）”或“恢复（标记为未删除）”操作，需要特殊处理
            if old_org.deleted <> self.deleted:
                if self.deleted:#调用了mark_deleted，如果存在未标记为删除的下级，则禁止该操作
                    if old_org.get_descendants().filter(deleted=False).count():
                        raise OperationAborted(u'不能将包含下级的机构标记为已删除，必须先将所有下级标记为已删除')
                else:#调用了mark_undelete，如果上级被标记为删除，则禁止该操作
                    if self.parent and self.parent.deleted:
                        raise OperationAborted(u'不能恢复，其上级机构被标记为已删除，必须先恢复其上级机构')
            if not self.deleted and self.parent and self.parent.deleted:
                raise OperationAborted(u'不能将上级修改为已删除的机构，必须先恢复已删除的机构')
            #如果修改了sorting_order值，必须级联修改所有下级的sorting_order
            if old_org.parent <> self.parent or old_org.sorting_order <> self.sorting_order:
                descendants = Org.objects.filter(path__startswith=old_org._get_search_path())
        else:
            #当前操作是新增机构，需要判断上级是否被标记为已删除
            if self.parent and self.parent.deleted:
                raise OperationAborted(u'不能向已删除的机构添加下级，必须先恢复已删除的机构')
        #保存（必须先保存自己，才能级联地保存下级，因为上级的depth和path将分别作为下级的depth和path的一部分）
        result = super(Org, self).save(force_insert=force_insert, force_update=force_update)
        #如果修改已有机构的上级，必须同时更新所有下级机构的深度和路径
        for org in descendants:
            org.save(force_insert=force_insert, force_update=force_update)
        return result

    def mark_deleted(self):
        '''删除机构，标记为删除状态
           此方法保持数据完整性，不作彻底删除，彻底删除使用delete'''
        self.deleted = True
        return self.save()

    def mark_undeleted(self):
        '''恢复机构，标记为未删除状态'''
        self.deleted = False
        return self.save()

    def delete(self):
        '''彻底删除，不同于mark_deleted'''
        if self.has_child():
            raise OperationAborted(u'不能彻底删除包含下级的机构，必须先彻底删除所有下级')

        return super(Org, self).delete()

    def is_top(self):
        '''是否顶级机构'''
        return self.parent is None

    def has_child(self):
        '''是否有下级机构'''
        return Org.objects.filter(parent__exact=self).count() > 0

    def get_children(self):
        '''得到儿子'''
        return Org.objects.filter(parent__exact=self)

    def get_siblings(self):
        '''得到兄弟'''
        if self.is_top():
            return Org.objects.filter(depth__exact=0).exclude(id=self.id)
        else:
            return Org.objects.filter(parent__exact=self.parent).exclude(id=self.id)

    def get_descendants(self):
        '''得到子孙'''
        return Org.objects.filter(path__startswith=self._get_search_path())

    def get_descendants_pk_list(self, include_self=True):
        '''得到所有子孙的pk，可选择是否包含自身pk'''
        pk_list = list(self.get_descendants().values_list('id', flat=True))
        if include_self:
          pk_list.insert(0, self.pk)
        return pk_list

    def contains(self, org):
        '''是否包含某机构'''
        return org.path.startswith(self._get_search_path())

    def pprint(self, qs, file=sys.stdout):
        '''该方法仅用于调试，可能被删除'''
        for org in qs.order_by('sorting_order'):
            print >> file, '%s%s' % ('\t' * org.depth, unicode(org),)
