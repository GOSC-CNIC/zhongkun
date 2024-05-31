from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from apps.app_net_manage.managers import OrgVirtualObjectManager
from apps.app_net_link.managers.common import NetLinkUserRoleWrapper
from apps.app_net_link.managers.link import DistriFrameManager, LinkManager
from apps.app_net_link.models import DistriFramePort, Link
from apps.app_net_link.permissions import LinkIPRestrictor


class DistriFramePortTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')

        u2_roler = NetLinkUserRoleWrapper(self.user2)
        u2_roler.user_role = u2_roler.get_or_create_user_role()
        u2_roler.set_link_readonly(True)

        u3_roler = NetLinkUserRoleWrapper(self.user3)
        u3_roler.user_role = u3_roler.get_or_create_user_role()
        u3_roler.set_link_admin(True)

        org1 = get_or_create_organization(name='org1')
        linkorg1 = OrgVirtualObjectManager.create_org_virt_obj(
            org=org1, name='铁科院', remark=''
        )
        linkorg2 = OrgVirtualObjectManager.create_org_virt_obj(
            org=org1, name='农科院', remark=''
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

        LinkIPRestrictor.add_ip_rule(ip_value='0.0.0.0/0')
        LinkIPRestrictor.clear_cache()
    
    def test_list_distriframeport(self):
        # user role 
        base_url = reverse('net_link-api:link-distriframeport-list')
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
        link = LinkManager.create_link(
            number="KY23092702",
            user="空天院-中国遥感卫星地面站",
            endpoint_a="空天院新技术园区B座A301机房，王萌13811835852",
            endpoint_z="海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            bandwidth=None,
            description="中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            line_type="科技云科技专线",
            business_person="周建虎",
            build_person="胡亮亮、王振伟",
            link_status=Link.LinkStatus.USING,
            remarks="adaeda",
            enable_date="2014-07-01",
            link_element=[
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": distriframeport.element.id
                },
            ]
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
