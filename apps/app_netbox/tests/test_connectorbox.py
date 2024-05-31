from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_link.managers.link import LinkManager, ConnectorBoxManager
from apps.app_net_link.managers.common import NetLinkUserRoleWrapper as NetBoxUserRoleWrapper
from apps.app_net_link.models import ConnectorBox, Link
from apps.app_net_link.permissions import LinkIPRestrictor


class ConnectorBoxTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')

        u2_roler = NetBoxUserRoleWrapper(self.user2)
        u2_roler.user_role = u2_roler.get_or_create_user_role()
        u2_roler.set_link_readonly(True)

        u3_roler = NetBoxUserRoleWrapper(self.user3)
        u3_roler.user_role = u3_roler.get_or_create_user_role()
        u3_roler.set_link_admin(True)

        ConnectorBoxManager.create_connectorbox(
            number='test_connector1',
            place='test_place1',
            remarks='',
            location='',
        )
        ConnectorBoxManager.create_connectorbox(
            number='test_connector2',
            place='test_place2',
            remarks='',
            location='',
        )
        LinkIPRestrictor.add_ip_rule(ip_value='0.0.0.0/0')
        LinkIPRestrictor.clear_cache()

    def test_list_connectorbox(self):
        # user role 
        base_url = reverse('netbox-api:link-connectorbox-list')
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
        connectorbox = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'place', 'remarks', 'location', 'place', 'is_linked', 'element_id', 'link_id'
        ], connectorbox)
        id = connectorbox['id']
        db_connectorbox = ConnectorBox.objects.filter(id=id).first()
        self.assertEqual(connectorbox['number'], db_connectorbox.number)
        self.assertEqual(connectorbox['place'], db_connectorbox.place)
        self.assertEqual(connectorbox['remarks'], db_connectorbox.remarks)
        self.assertEqual(connectorbox['location'], db_connectorbox.location)
        self.assertEqual(connectorbox['place'], db_connectorbox.place)
        self.assertEqual(connectorbox['is_linked'], False)
        self.assertEqual(connectorbox['element_id'], db_connectorbox.element.id)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # query "is_linked"
        query = parse.urlencode(query={'is_linked': '1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(
            status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'is_linked': 'False'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['is_linked'], False)
        connectorbox = ConnectorBox.objects.all().first()
        link1 = LinkManager.create_link(
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
                    "element_id": connectorbox.element.id
                },
            ]
        )
        link2 = LinkManager.create_link(
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
                    "element_id": connectorbox.element.id
                },
            ]
        )
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], connectorbox.id)
        self.assertEqual(response.data['results'][0]['is_linked'], True)
        self.assertEqual(len(response.data['results'][0]['link_id']), 2)
        self.assertEqual(sorted([response.data['results'][0]['link_id'][0],
                                 response.data['results'][0]['link_id'][1]]),
                         sorted([link1.id, link2.id]))
