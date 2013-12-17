#coding=gbk
from django.test import TestCase
from employee.models import Employee
from models import Org
from exceptions import OperationAborted

class OrgTestCase(TestCase):
    def setUp(self):
        from StringIO import StringIO
        from parse import import_from_file
        buf = StringIO(
        u'''
            01,云南省邮政公司
                0101,昆明市邮政局
                    010101,投递局
                        01010101,速递公司
                            0101010101,昆明市白龙速递站
                            0101010102,昆明市南窑速递站
                        01010102,11185客户服务中心
                    010102,五华区邮政局
                        01010201,综合部
                        01010202,高新分局
                            0101020201,正大电子城支局
                            0101020202,海源中路支局
                        01010203,人民路营业部
                            0101020301,人民路营业部综合办
                            0101020302,昆明市人民路邮政支局
                0102,玉溪市邮政局
                    010201,玉溪市邮政局机关
                        01020101,人力资源部
                        01020102,储汇分局
                            0102010201,马井支局
        ''')
        import_from_file(file=buf, reset_table=True)
        
    def testImportFromFile(self):
        '''机构关系'''
        orgs = Org.objects.all()
        self.assertEquals(20, len(orgs))
        self.assertEquals(1, Org.objects.get_top_list().count())
        #顶层
        top = Org.objects.get_top_list()[0]
        self.assertEquals(u'云南省邮政公司', top.name)
        self.assertEquals(2, top.get_children().count())
        self.assertEquals(19, top.get_descendants().count())
        #二层
        second = top.get_children().order_by('seq')[0]
        self.assertEquals(u'昆明市邮政局', second.name)
        self.assertEquals(2, second.get_children().count())
        self.assertEquals(13, second.get_descendants().count())
        #三层
        third = second.get_children().order_by('seq')[1]
        self.assertEquals(u'五华区邮政局', third.name)
        self.assertEquals(3, third.get_children().count())
        self.assertEquals(7, third.get_descendants().count())
        #四层
        fourth = third.get_children().order_by('seq')[0]
        self.assertEquals(u'综合部', fourth.name)
        self.assertEquals(0, fourth.get_children().count())
        self.assertEquals(0, fourth.get_descendants().count())
        fourth = third.get_children().order_by('seq')[2]
        self.assertEquals(u'人民路营业部', fourth.name)
        self.assertEquals(2, fourth.get_children().count())
        self.assertEquals(2, fourth.get_descendants().count())
        #五层
        fifth = fourth.get_children().order_by('seq')[1]
        self.assertEquals(u'昆明市人民路邮政支局', fifth.name)
        self.assertEquals(0, fifth.get_children().count())
        self.assertEquals(0, fifth.get_descendants().count())
    
    def testIntegrity(self):
        '''属性值正确并完整'''
        top = Org.objects.get_top_list()[0]
        self.assertTrue(top.is_top())
        self.assertEquals(0, top.depth)
        self.assertEquals('/', top.path)
        self.assertEquals(None, top.parent)
        self.assertRaises(OperationAborted, top.delete)
        #二层
        second = top.get_children().order_by('seq')[0]
        self.assertFalse(second.is_top())
        self.assertEquals(1, second.depth)
        self.assertEquals(top._get_search_path(), second.path)
        self.assertEquals(top, second.parent)
        self.assertRaises(OperationAborted, second.delete)
    
    def testGetDescendants(self):
        '''获取下级机构'''
        top = Org.objects.get_top_list()[0]
        for d in top.get_descendants():
            self.assertTrue(d.path.startswith(top._get_search_path()))
        #from parse import show_all
        #show_all()
    
    def testDelete(self):
        '''彻底删除'''
        #含有下级机构，不能彻底删除
        top = Org.objects.get_top_list()[0]
        self.assertRaises(OperationAborted, top.delete)
        second = top.get_children().order_by('seq')[0]
        self.assertRaises(OperationAborted, second.delete)
        leaf_nodes = Org.objects.filter(name__exact=u'马井支局')
        self.assertEquals(1, leaf_nodes.count())
        self.assertEquals(0, leaf_nodes[0].get_children().count())
        leaf_nodes[0].delete()
        leaf_nodes = Org.objects.filter(name__exact=u'马井支局')
        self.assertEquals(0, leaf_nodes.count())
        #逐一彻底删除
        for o in Org.objects.all().order_by('-depth'):
            o.delete()
        self.assertEquals(0, Org.objects.all().count())
        
    def testMarkDeleted(self):
        '''删除&恢复'''
        #含有下级机构，不能删除
        top = Org.objects.get_top_list()[0]
        #禁止删除
        self.assertRaises(OperationAborted, top.mark_deleted)
        self.assertRaises(OperationAborted, Org.objects.get(name__exact=u'储汇分局').mark_deleted)
        #删除
        Org.objects.get(name__exact=u'马井支局').mark_deleted()
        Org.objects.get(name__exact=u'储汇分局').mark_deleted()
        #禁止恢复
        self.assertRaises(OperationAborted, Org.objects.get(name__exact=u'马井支局').mark_undeleted)
        #禁止向已删除的机构添加下级
        self.assertRaises(OperationAborted, Org(name=u'新增的机构', parent=Org.objects.get(name__exact=u'马井支局')).save)
        #可以向已恢复的机构添加下级
        Org.objects.get(name__exact=u'储汇分局').mark_undeleted()
        Org.objects.get(name__exact=u'马井支局').mark_undeleted()
        Org(name=u'新增的机构', parent=Org.objects.get(name__exact=u'马井支局')).save()
        #禁止机构迁移到已删除的机构中
        Org.objects.get(name__exact=u'11185客户服务中心').mark_deleted()
        org = Org.objects.get(name=u'新增的机构')
        org.parent = Org.objects.get(name__exact=u'11185客户服务中心')
        self.assertRaises(OperationAborted, org.save)
        #为不影响测试数据，删除刚刚添加的机构
        Org.objects.get(name=u'新增的机构').delete()
        #逐一删除
        for o in Org.objects.all().order_by('-depth'):
            o.mark_deleted()
        self.assertEquals(0, Org.objects.filter(deleted=False).count())
        self.assertEquals(20, Org.objects.all().count())
        #逐一恢复
        for o in Org.objects.all().order_by('depth'):
            o.mark_undeleted()
        self.assertEquals(0, Org.objects.filter(deleted=True).count())
        self.assertEquals(20, Org.objects.all().count())

    def testUpdateCascade(self):
        '''机构迁移'''
        '''
            迁移前
            =====================================
            云南省邮政公司
                玉溪市邮政局
                    玉溪市邮政局机关
                        人力资源部
                        储汇分局
                            马井支局
            迁移后
            =====================================
            云南省邮政公司
                玉溪市邮政局
                玉溪市邮政局机关
                    人力资源部
                    储汇分局
                        马井支局
        '''
        old1 = Org.objects.filter(name__exact=u'玉溪市邮政局机关')[0]
        old2 = Org.objects.filter(name__exact=u'人力资源部')[0]
        old3 = Org.objects.filter(name__exact=u'储汇分局')[0]
        old4 = Org.objects.filter(name__exact=u'马井支局')[0]
        
        new1 = Org.objects.filter(name__exact=u'玉溪市邮政局机关')[0]
        new1.parent = Org.objects.get_top_list()[0]
        new1.save()
        new2 = Org.objects.filter(name__exact=u'人力资源部')[0]
        new3 = Org.objects.filter(name__exact=u'储汇分局')[0]
        new4 = Org.objects.filter(name__exact=u'马井支局')[0]
        
        self.assertEquals(2, old1.depth)
        self.assertEquals(1, new1.depth)
        self.assertEquals(3, old2.depth)
        self.assertEquals(2, new2.depth)
        self.assertEquals(3, old3.depth)
        self.assertEquals(2, new3.depth)
        self.assertEquals(4, old4.depth)
        self.assertEquals(3, new4.depth)
    
    def testForbiddenOperation(self):
        '''不允许的若干操作'''
        org = Org.objects.get(name__exact=u'玉溪市邮政局机关')
        org.parent = org
        self.assertRaises(OperationAborted, org.save)

    def testImportFromFileToParentOrg(self):
        from StringIO import StringIO
        from parse import import_from_file
        buf = StringIO(
        u'''
            0101010201,昆明市邮政局投递分公司
                010101020101,东区投递分公司
                    01010102010101,北京路投递支局
                    01010102010102,东郊路投递支局
                        0101010201010201,白龙投递组
                        0101010201010202,王大桥投递组
                    01010102010103,关上投递支局
                        0101010201010301,牛街庄投递组
                        0101010201010302,小板桥投递组
                        0101010201010303,大板桥投递组
                        0101010201010304,凉亭投递组
                        0101010201010305,跑马山投递组
                        0101010201010306,小哨投递组
                010101020102,南区投递分公司
                    01010102010201,新闻路投递支局	
                    01010102010202,豆腐营投递支局
                        0101010201020201,官庄投递组
                    01010102010203,前卫投递支局
                010101020103,西区投递分公司
                    01010102010301,人民路投递支局
        ''')
        parent_org = Org.objects.get(name__exact=u'11185客户服务中心')
        import_from_file(file=buf, parent_org=parent_org)
        self.assertEquals(40, Org.objects.all().count())
        self.assertEquals(1, Org.objects.get_top_list().count())
        #顶层
        top = Org.objects.get_top_list()[0]
        self.assertEquals(u'云南省邮政公司', top.name)
        self.assertEquals(2, top.get_children().count())
        self.assertEquals(39, top.get_descendants().count())
        #添加片段后的parent_org
        self.assertEquals(1, parent_org.get_children().count())
        self.assertEquals(20, parent_org.get_descendants().count())
        #新片段是否正确
        new_child = parent_org.get_children().order_by('seq')[0]
        self.assertEquals(new_child.depth, parent_org.depth+1)
        self.assertEquals(u'昆明市邮政局投递分公司', new_child.name)
        self.assertEquals(3, new_child.get_children().count())
        self.assertEquals(19, new_child.get_descendants().count())
        
    def tearDown(self):
        pass

__test__ = {"doctest": """
①缓存是否起效
②机构数据保存时是否正确删除缓存

>>> from django.db import connection
>>> from org.models import Org
>>> from django.core.cache import cache
>>> from django.conf import settings
>>> settings.DEBUG = True
>>> Org.objects.filter(code__in=('01', '0101')).delete()
>>> org1 = Org(code='01', name='root org')
>>> org1.save()
>>> org2 = Org(parent=org1, code='0101', name='child org')
>>> org2.save()
>>> id1, id2 = org1.pk, org2.pk
>>> key1, key2 = Org.objects._get_cache_key(id1), Org.objects._get_cache_key(id2)
>>> connection.queries = []
>>> org1, org2 = Org.objects.get_for_id(id1), Org.objects.get_for_id(id2)
>>> len(connection.queries)
2
>>> connection.queries = []
>>> org1, org2 = Org.objects.get_for_id(id1), Org.objects.get_for_id(id2)
>>> len(connection.queries)
0
>>> org2.save()
>>> connection.queries = []
>>> org1, org2 = Org.objects.get_for_id(id1), Org.objects.get_for_id(id2)
>>> len(connection.queries)
1
>>> org1.seq = org1.seq + 1
>>> org1.save()
>>> cache.get(key1), cache.get(key2)
(None, None)
>>> connection.queries = []
>>> org1, org2 = Org.objects.get_for_id(id1), Org.objects.get_for_id(id2)
>>> len(connection.queries)
2
>>> org2.delete()
>>> cache.get(key1), cache.get(key2)
(<Org: root org>, None)
"""}

