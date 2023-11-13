from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.leaseline_manager import LeaseLineManager
from link.managers.elementlink_manager import ElementLinkManager
from link.managers.task_manager import TaskManager
from link.managers.elementlink_manager import ElementLinkManager
from datetime import date
from django.urls import reverse
from link.models import Task, ElementLink, LinkUserRole
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse


class ElementLinkTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)


    def test_list_elementlink(self):
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
        elementlink1 = ElementLinkManager.create_elementlink(
            id_list=[leaseline1.element.id, leaseline2.element.id],
            remarks='test',
            link_status=ElementLink.LinkStatus.IDLE,
            task=task,
            number='test_number'
        )
    
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

        # query "task_id"
        query = parse.urlencode(query={'task_id': 'abc'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        query = parse.urlencode(query={'task_id': task.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        # query "link_status"
        elementlink2 = ElementLinkManager.create_elementlink(
            id_list=[leaseline1.element.id, leaseline2.element.id],
            remarks='test',
            link_status=ElementLink.LinkStatus.IDLE,
            task=task,
            number='test_number'
        )
        elementlink3 = ElementLinkManager.create_elementlink(
            id_list=[leaseline1.element.id, leaseline2.element.id],
            remarks='test',
            link_status=ElementLink.LinkStatus.DELETED,
            task=task,
            number='test_number'
        )
        query = parse.urlencode(query={'link_status': 'abc'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 400)
        query1 = parse.urlencode(query={'link_status': ElementLink.LinkStatus.DELETED})
        query2 = parse.urlencode(query={'link_status': ElementLink.LinkStatus.USING})
        response = self.client.get(f'{base_url}?{query1}&{query2}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['link_status'], ElementLink.LinkStatus.DELETED)
        query = parse.urlencode(query={'link_status': ElementLink.LinkStatus.USING})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

    def test_retrieve_elementlink(self):
        task1 = TaskManager.create_task(
            number='KY23092702',
            user='空天院-中国遥感卫星地面站',
            endpoint_a='空天院新技术园区B座A301机房，王萌13811835852',
            endpoint_z='海淀区后厂村路55号北京气象卫星地面站，球形建筑，1层机房，林茂伟13810802009，光缆施工联系闫振宇 13811904589',
            bandwidth=None,
            task_description='中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）',
            line_type='科技云科技专线',
            task_person='周建虎',
            build_person='胡亮亮、王振伟',
            task_status=Task.TaskStatus.NORMAL
        )
        elementlink = ElementLinkManager.create_elementlink(
            id_list=[],
            remarks='test',
            link_status=ElementLink.LinkStatus.IDLE,
            task=task1,
            number='test_number'
        )
        # user role
        base_url = reverse('api:link-elementlink-detail',
                           kwargs={'id': elementlink.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(
            status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.user3)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)

        # Invalid id
        base_url = reverse('api:link-elementlink-detail', kwargs={'id': '  '})
        response = self.client.get(base_url)
        self.assertErrorResponse(
            status_code=400, code='InvalidArgument', response=response)

        # element not exist
        base_url = reverse('api:link-elementlink-detail', kwargs={'id': 'asd'})
        response = self.client.get(base_url)
        self.assertErrorResponse(
            status_code=404, code='ElementLinkNotExist', response=response)

        # data
        base_url = reverse('api:link-elementlink-detail',
                           kwargs={'id': elementlink.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'number', 'remarks', 'link_status', 'task', 'element_id_list'
        ], response.data)
        self.assertKeysIn([
            'id', 'number', 'user'
        ], response.data['task'])
        self.assertEqual(response.data['id'], elementlink.id)
