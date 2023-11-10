from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.distriframe_manager import DistriFrameManager
from link.managers.linkorg_manager import LinkOrgManager
from django.urls import reverse
from urllib import parse
from service.models import DataCenter
from link.models import DistriFramePort, LinkUserRole, ElementLink
from link.managers.elementlink_manager import ElementLinkManager
class DistriFramePortTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
        org1 = DataCenter(name='org1', name_en='org1 en')
        org1.save(force_insert=True)
        linkorg1 = LinkOrgManager.create_linkorg(
            data_center=org1,
            name='铁科院',
            remarks='',
            location=''
        )
        linkorg2 = LinkOrgManager.create_linkorg(
            data_center=org1,
            name='农科院',
            remarks='',
            location=''
        )
        self.distriframe1 = DistriFrameManager.create_distriframe(
            number='test_distriframe_number1',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于铁科大厦一层弱电间，普天72芯一体化机框',
            remarks='【51893383随机呼转张效军18618417973和张东升13910987916】51893383找罗工、唐工',
            link_org=linkorg1
        )
        self.distriframe2 = DistriFrameManager.create_distriframe(
            number='test_distriframe_number2',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于农科院信息所网络中心机房F4机柜，普天72芯一体化机框',
            remarks='',
            link_org=linkorg2
        )
    
    def test_list_distriframeport(self):
        # user role 
        base_url = reverse('api:link-distriframeport-list')
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
        self.assertEqual(response.data['count'], 144)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 20)
        distriframeport = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'row', 'col', 'distribution_frame', 'is_linked', 'element_id'
        ], distriframeport)
        self.assertKeysIn([
            'id', 'number'
        ], distriframeport['distribution_frame'])
        id = distriframeport['id']
        db_distriframeport = DistriFramePort.objects.filter(id=id).first()
        self.assertEqual(distriframeport['number'], db_distriframeport.number)
        self.assertEqual(distriframeport['row'], db_distriframeport.row)
        self.assertEqual(distriframeport['col'], db_distriframeport.col)
        self.assertEqual(distriframeport['is_linked'], False)
        self.assertEqual(distriframeport['element_id'], db_distriframeport.element.id)
        self.assertEqual(distriframeport['distribution_frame']['id'], db_distriframeport.distribution_frame.id)
        self.assertEqual(distriframeport['distribution_frame']['number'], db_distriframeport.distribution_frame.number)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 2})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 144)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)

        # query "is_linked"
        query = parse.urlencode(query={'is_linked': '1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'is_linked': 'False'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['is_linked'], False)
        distriframeport = DistriFramePort.objects.all().first()
        elementlink = ElementLinkManager.create_elementlink(
            number="test_link",
            id_list=[
                distriframeport.element.id,
            ],
            remarks="test_remarks",
            link_status=ElementLink.LinkStatus.IDLE,
            task=None
        )
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], distriframeport.id)
        self.assertEqual(response.data['results'][0]['is_linked'], True)

        # query "frame_id"
        query = parse.urlencode(query={'frame_id': 'abc'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        query = parse.urlencode(query={'frame_id': self.distriframe1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], self.distriframe1.col_count * self.distriframe1.row_count)
        self.assertEqual(response.data['results'][0]['distribution_frame']['id'], self.distriframe1.id)
        query = parse.urlencode(query={'frame_id': self.distriframe2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], self.distriframe2.col_count * self.distriframe2.row_count)
        self.assertEqual(response.data['results'][0]['distribution_frame']['id'], self.distriframe2.id)
