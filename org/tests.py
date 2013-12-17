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
            01,����ʡ������˾
                0101,������������
                    010101,Ͷ�ݾ�
                        01010101,�ٵݹ�˾
                            0101010101,�����а����ٵ�վ
                            0101010102,��������Ҥ�ٵ�վ
                        01010102,11185�ͻ���������
                    010102,�廪��������
                        01010201,�ۺϲ�
                        01010202,���·־�
                            0101020201,������ӳ�֧��
                            0101020202,��Դ��·֧��
                        01010203,����·Ӫҵ��
                            0101020301,����·Ӫҵ���ۺϰ�
                            0101020302,����������·����֧��
                0102,��Ϫ��������
                    010201,��Ϫ�������ֻ���
                        01020101,������Դ��
                        01020102,����־�
                            0102010201,��֧��
        ''')
        import_from_file(file=buf, reset_table=True)
        
    def testImportFromFile(self):
        '''������ϵ'''
        orgs = Org.objects.all()
        self.assertEquals(20, len(orgs))
        self.assertEquals(1, Org.objects.get_top_list().count())
        #����
        top = Org.objects.get_top_list()[0]
        self.assertEquals(u'����ʡ������˾', top.name)
        self.assertEquals(2, top.get_children().count())
        self.assertEquals(19, top.get_descendants().count())
        #����
        second = top.get_children().order_by('seq')[0]
        self.assertEquals(u'������������', second.name)
        self.assertEquals(2, second.get_children().count())
        self.assertEquals(13, second.get_descendants().count())
        #����
        third = second.get_children().order_by('seq')[1]
        self.assertEquals(u'�廪��������', third.name)
        self.assertEquals(3, third.get_children().count())
        self.assertEquals(7, third.get_descendants().count())
        #�Ĳ�
        fourth = third.get_children().order_by('seq')[0]
        self.assertEquals(u'�ۺϲ�', fourth.name)
        self.assertEquals(0, fourth.get_children().count())
        self.assertEquals(0, fourth.get_descendants().count())
        fourth = third.get_children().order_by('seq')[2]
        self.assertEquals(u'����·Ӫҵ��', fourth.name)
        self.assertEquals(2, fourth.get_children().count())
        self.assertEquals(2, fourth.get_descendants().count())
        #���
        fifth = fourth.get_children().order_by('seq')[1]
        self.assertEquals(u'����������·����֧��', fifth.name)
        self.assertEquals(0, fifth.get_children().count())
        self.assertEquals(0, fifth.get_descendants().count())
    
    def testIntegrity(self):
        '''����ֵ��ȷ������'''
        top = Org.objects.get_top_list()[0]
        self.assertTrue(top.is_top())
        self.assertEquals(0, top.depth)
        self.assertEquals('/', top.path)
        self.assertEquals(None, top.parent)
        self.assertRaises(OperationAborted, top.delete)
        #����
        second = top.get_children().order_by('seq')[0]
        self.assertFalse(second.is_top())
        self.assertEquals(1, second.depth)
        self.assertEquals(top._get_search_path(), second.path)
        self.assertEquals(top, second.parent)
        self.assertRaises(OperationAborted, second.delete)
    
    def testGetDescendants(self):
        '''��ȡ�¼�����'''
        top = Org.objects.get_top_list()[0]
        for d in top.get_descendants():
            self.assertTrue(d.path.startswith(top._get_search_path()))
        #from parse import show_all
        #show_all()
    
    def testDelete(self):
        '''����ɾ��'''
        #�����¼����������ܳ���ɾ��
        top = Org.objects.get_top_list()[0]
        self.assertRaises(OperationAborted, top.delete)
        second = top.get_children().order_by('seq')[0]
        self.assertRaises(OperationAborted, second.delete)
        leaf_nodes = Org.objects.filter(name__exact=u'��֧��')
        self.assertEquals(1, leaf_nodes.count())
        self.assertEquals(0, leaf_nodes[0].get_children().count())
        leaf_nodes[0].delete()
        leaf_nodes = Org.objects.filter(name__exact=u'��֧��')
        self.assertEquals(0, leaf_nodes.count())
        #��һ����ɾ��
        for o in Org.objects.all().order_by('-depth'):
            o.delete()
        self.assertEquals(0, Org.objects.all().count())
        
    def testMarkDeleted(self):
        '''ɾ��&�ָ�'''
        #�����¼�����������ɾ��
        top = Org.objects.get_top_list()[0]
        #��ֹɾ��
        self.assertRaises(OperationAborted, top.mark_deleted)
        self.assertRaises(OperationAborted, Org.objects.get(name__exact=u'����־�').mark_deleted)
        #ɾ��
        Org.objects.get(name__exact=u'��֧��').mark_deleted()
        Org.objects.get(name__exact=u'����־�').mark_deleted()
        #��ֹ�ָ�
        self.assertRaises(OperationAborted, Org.objects.get(name__exact=u'��֧��').mark_undeleted)
        #��ֹ����ɾ���Ļ�������¼�
        self.assertRaises(OperationAborted, Org(name=u'�����Ļ���', parent=Org.objects.get(name__exact=u'��֧��')).save)
        #�������ѻָ��Ļ�������¼�
        Org.objects.get(name__exact=u'����־�').mark_undeleted()
        Org.objects.get(name__exact=u'��֧��').mark_undeleted()
        Org(name=u'�����Ļ���', parent=Org.objects.get(name__exact=u'��֧��')).save()
        #��ֹ����Ǩ�Ƶ���ɾ���Ļ�����
        Org.objects.get(name__exact=u'11185�ͻ���������').mark_deleted()
        org = Org.objects.get(name=u'�����Ļ���')
        org.parent = Org.objects.get(name__exact=u'11185�ͻ���������')
        self.assertRaises(OperationAborted, org.save)
        #Ϊ��Ӱ��������ݣ�ɾ���ո���ӵĻ���
        Org.objects.get(name=u'�����Ļ���').delete()
        #��һɾ��
        for o in Org.objects.all().order_by('-depth'):
            o.mark_deleted()
        self.assertEquals(0, Org.objects.filter(deleted=False).count())
        self.assertEquals(20, Org.objects.all().count())
        #��һ�ָ�
        for o in Org.objects.all().order_by('depth'):
            o.mark_undeleted()
        self.assertEquals(0, Org.objects.filter(deleted=True).count())
        self.assertEquals(20, Org.objects.all().count())

    def testUpdateCascade(self):
        '''����Ǩ��'''
        '''
            Ǩ��ǰ
            =====================================
            ����ʡ������˾
                ��Ϫ��������
                    ��Ϫ�������ֻ���
                        ������Դ��
                        ����־�
                            ��֧��
            Ǩ�ƺ�
            =====================================
            ����ʡ������˾
                ��Ϫ��������
                ��Ϫ�������ֻ���
                    ������Դ��
                    ����־�
                        ��֧��
        '''
        old1 = Org.objects.filter(name__exact=u'��Ϫ�������ֻ���')[0]
        old2 = Org.objects.filter(name__exact=u'������Դ��')[0]
        old3 = Org.objects.filter(name__exact=u'����־�')[0]
        old4 = Org.objects.filter(name__exact=u'��֧��')[0]
        
        new1 = Org.objects.filter(name__exact=u'��Ϫ�������ֻ���')[0]
        new1.parent = Org.objects.get_top_list()[0]
        new1.save()
        new2 = Org.objects.filter(name__exact=u'������Դ��')[0]
        new3 = Org.objects.filter(name__exact=u'����־�')[0]
        new4 = Org.objects.filter(name__exact=u'��֧��')[0]
        
        self.assertEquals(2, old1.depth)
        self.assertEquals(1, new1.depth)
        self.assertEquals(3, old2.depth)
        self.assertEquals(2, new2.depth)
        self.assertEquals(3, old3.depth)
        self.assertEquals(2, new3.depth)
        self.assertEquals(4, old4.depth)
        self.assertEquals(3, new4.depth)
    
    def testForbiddenOperation(self):
        '''����������ɲ���'''
        org = Org.objects.get(name__exact=u'��Ϫ�������ֻ���')
        org.parent = org
        self.assertRaises(OperationAborted, org.save)

    def testImportFromFileToParentOrg(self):
        from StringIO import StringIO
        from parse import import_from_file
        buf = StringIO(
        u'''
            0101010201,������������Ͷ�ݷֹ�˾
                010101020101,����Ͷ�ݷֹ�˾
                    01010102010101,����·Ͷ��֧��
                    01010102010102,����·Ͷ��֧��
                        0101010201010201,����Ͷ����
                        0101010201010202,������Ͷ����
                    01010102010103,����Ͷ��֧��
                        0101010201010301,ţ��ׯͶ����
                        0101010201010302,С����Ͷ����
                        0101010201010303,�����Ͷ����
                        0101010201010304,��ͤͶ����
                        0101010201010305,����ɽͶ����
                        0101010201010306,С��Ͷ����
                010101020102,����Ͷ�ݷֹ�˾
                    01010102010201,����·Ͷ��֧��	
                    01010102010202,����ӪͶ��֧��
                        0101010201020201,��ׯͶ����
                    01010102010203,ǰ��Ͷ��֧��
                010101020103,����Ͷ�ݷֹ�˾
                    01010102010301,����·Ͷ��֧��
        ''')
        parent_org = Org.objects.get(name__exact=u'11185�ͻ���������')
        import_from_file(file=buf, parent_org=parent_org)
        self.assertEquals(40, Org.objects.all().count())
        self.assertEquals(1, Org.objects.get_top_list().count())
        #����
        top = Org.objects.get_top_list()[0]
        self.assertEquals(u'����ʡ������˾', top.name)
        self.assertEquals(2, top.get_children().count())
        self.assertEquals(39, top.get_descendants().count())
        #���Ƭ�κ��parent_org
        self.assertEquals(1, parent_org.get_children().count())
        self.assertEquals(20, parent_org.get_descendants().count())
        #��Ƭ���Ƿ���ȷ
        new_child = parent_org.get_children().order_by('seq')[0]
        self.assertEquals(new_child.depth, parent_org.depth+1)
        self.assertEquals(u'������������Ͷ�ݷֹ�˾', new_child.name)
        self.assertEquals(3, new_child.get_children().count())
        self.assertEquals(19, new_child.get_descendants().count())
        
    def tearDown(self):
        pass

__test__ = {"doctest": """
�ٻ����Ƿ���Ч
�ڻ������ݱ���ʱ�Ƿ���ȷɾ������

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

