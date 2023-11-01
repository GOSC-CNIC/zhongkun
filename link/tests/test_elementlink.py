from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.leaseline_manager import LeaseLineManager
from link.managers.elementlink_manager import ElementLinkManager
from link.managers.task_manager import TaskManager
from link.managers.elementlink_manager import ElementLinkManager
from datetime import date
from django.urls import reverse
from link.models import Task, ElementLink
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse


class ElementLinkTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        UserRoleWrapper(user=self.user2).add_read_permission()
        UserRoleWrapper(user=self.user3).add_write_permission()
        task = TaskManager.create_task(
            number='YW2023101001',
            user='广东空天科技研究院（简称广天院）',
            endpoint_a='广东省广州市南沙区万新大道与横一路交叉口东80米，广东空天科技研究院科研楼机房，张钧魁13233579691',
            endpoint_z='力学所',
            bandwidth='100',
            task_description='广东空天科技研究院至力学所',
            line_type='用户专线',
            task_person='杨云希',
            build_person='胡亮亮、北京联通',
            task_status=Task.TaskStatus.NORMAL
        )
        leaseline1 = LeaseLineManager.create_leaseline(
            private_line_number='00645713',
            lease_line_code='天津空港物流加工区西七道32号',
            line_username='天津工业生物技术研究所',
            endpoint_a='北京市海淀区中关村南四街4号',
            endpoint_z='天津空港物流加工区西七道32号',
            line_type='接入网',
            cable_type='MSTP电路',
            bandwidth=400,
            length=None,
            provider='联通（北京）',
            enable_date=date.fromisoformat('2021-10-05'),
            is_whithdrawal=False,
            money=300.20,
            remarks='电路代号：北京天津ANE0365NP，起租时间2010.08.16,2014-1-1日由30M扩容为100M，2017年7月28日由100M扩容至150M,2019年8月由150M升级为250M.20201017升级到400M。'
        )
        leaseline2 = LeaseLineManager.create_leaseline(
            private_line_number='26001927719',
            lease_line_code='',
            line_username='国家气象中心云岗通信台',
            endpoint_a='北京市海淀区中关村南四街4号',
            endpoint_z='',
            line_type='接入网',
            cable_type='MSTP电路',
            bandwidth=170,
            length=None,
            provider='移动（北京）',
            enable_date=date.fromisoformat('2014-11-22'),
            is_whithdrawal=True,
            money=300.20,
            remarks=''
        )
        ElementLinkManager.create_elementlink(
            id_list=[leaseline1.element.id, leaseline2.element.id],
            remarks='test',
            link_status=ElementLink.LinkStatus.IDLE,
            task=task,
            number='test_number'
        )

    def test_list_elementlink(self):
        # user role 
        base_url = reverse('api:link-elementlink-list')
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
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)
        elementlink = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'remarks', 'link_status', 'task', 'element_id_list'
        ], elementlink)
        self.assertKeysIn([
            'id', 'number', 'user'
        ], elementlink['task'])
        self.assertEqual(len(elementlink['element_id_list']), 2)
        id = elementlink['id']
        db_elementlink = ElementLink.objects.filter(id=id).first()
        self.assertEqual(elementlink['number'], db_elementlink.number)
        self.assertEqual(elementlink['remarks'], db_elementlink.remarks)
        self.assertEqual(elementlink['link_status'], db_elementlink.link_status)
        self.assertEqual(elementlink['task']['id'], db_elementlink.task.id)
        self.assertEqual(elementlink['task']['number'], db_elementlink.task.number)
        self.assertEqual(elementlink['task']['user'], db_elementlink.task.user)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 1, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)