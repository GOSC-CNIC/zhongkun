from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.task_manager import TaskManager
from django.urls import reverse
from link.models import Task, LinkUserRole
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse


class TaskTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
        TaskManager.create_task(
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
        TaskManager.create_task(
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
    def test_list_task(self):
        # user role 
        base_url = reverse('api:link-task-list')
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
        task = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'endpoint_a', 'endpoint_z', 'bandwidth', 'task_description',
            'line_type', 'task_person', 'build_person', 'task_status'
        ], task)
        id = task['id']
        db_task = Task.objects.filter(id=id).first()
        self.assertEqual(task['number'], db_task.number)
        self.assertEqual(task['endpoint_a'], db_task.endpoint_a)
        self.assertEqual(task['endpoint_z'], db_task.endpoint_z)
        self.assertEqual(task['bandwidth'], db_task.bandwidth)
        self.assertEqual(task['task_description'], db_task.task_description)
        self.assertEqual(task['line_type'], db_task.line_type)
        self.assertEqual(task['task_person'], db_task.task_person)
        self.assertEqual(task['build_person'], db_task.build_person)
        self.assertEqual(task['task_status'], db_task.task_status)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)