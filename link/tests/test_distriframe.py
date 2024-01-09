from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from service.models import DataCenter
from ipam.managers import OrgVirtualObjectManager
from link.managers.distriframe_manager import DistriFrameManager
from link.models import DistributionFrame
from link.models import LinkUserRole


class DistriFrameTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
    
    def test_list_distriframe(self):
        org1 = DataCenter(name='org1', name_en='org1 en')
        org1.save(force_insert=True)
        linkorg1 = OrgVirtualObjectManager.create_org_virt_obj(
            org=org1, name='铁科院', remark=''
        )
        linkorg2 = OrgVirtualObjectManager.create_org_virt_obj(
            org=org1, name='农科院', remark=''
        )
        DistriFrameManager.create_distriframe(
            number='test_distriframe_number1',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于铁科大厦一层弱电间，普天72芯一体化机框',
            remarks='【51893383随机呼转张效军18618417973和张东升13910987916】51893383找罗工、唐工',
            link_org=linkorg1
        )
        DistriFrameManager.create_distriframe(
            number='test_distriframe_number2',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于农科院信息所网络中心机房F4机柜，普天72芯一体化机框',
            remarks='',
            link_org=linkorg2
        )

        # user role 
        base_url = reverse('link-api:link-distributionframe-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.user3)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)

        # data
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)
        distriframe = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'model_type', 'row_count', 'col_count', 'place', 'remarks', 'link_org'
        ], distriframe)
        link_org = response.data['results'][0]['link_org']
        self.assertKeysIn([
            'id', 'name'
        ], link_org)
        id = distriframe['id']
        db_distriframe = DistributionFrame.objects.filter(id=id).first()
        self.assertEqual(distriframe['number'], db_distriframe.number)
        self.assertEqual(distriframe['model_type'], db_distriframe.model_type)
        self.assertEqual(distriframe['row_count'], db_distriframe.row_count)
        self.assertEqual(distriframe['col_count'], db_distriframe.col_count)
        self.assertEqual(distriframe['place'], db_distriframe.place)
        self.assertEqual(distriframe['remarks'], db_distriframe.remarks)
        self.assertEqual(distriframe['link_org']['id'], db_distriframe.link_org.id)
        self.assertEqual(distriframe['link_org']['name'], db_distriframe.link_org.name)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_distriframe(self):
        org1 = DataCenter(name='org1', name_en='org1 en')
        org1.save(force_insert=True)
        linkorg1 = OrgVirtualObjectManager.create_org_virt_obj(
            org=org1, name='铁科院', remark=''
        )
        distriframe = DistriFrameManager.create_distriframe(
            number='test_distriframe_number2',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于农科院信息所网络中心机房F4机柜，普天72芯一体化机框',
            remarks='',
            link_org=linkorg1
        )
        # user role
        base_url = reverse('link-api:link-distributionframe-detail',kwargs={'id': distriframe.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.user3)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)

        # Invalid id
        base_url = reverse('link-api:link-distributionframe-detail', kwargs={'id': '  '})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # data not exist
        base_url = reverse('link-api:link-distributionframe-detail', kwargs={'id': 'asd'})
        response = self.client.get(base_url)
        self.assertErrorResponse(
            status_code=404, code='DistributionFrameNotExist', response=response)

        # data
        base_url = reverse('link-api:link-distributionframe-detail',kwargs={'id': distriframe.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'number', 'model_type', 'row_count', 'col_count', 'place', 'remarks', 'link_org'
        ], response.data)
        self.assertKeysIn([
            'id', 'name'
        ], response.data['link_org'])
        self.assertEqual(response.data['id'], distriframe.id)
