from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.link_manager import LinkManager
from link.managers.fibercable_manager import FiberCableManager
from link.managers.distriframe_manager import DistriFrameManager
from link.managers.connectorbox_manager import ConnectorBoxManager
from link.managers.leaseline_manager import LeaseLineManager
from django.urls import reverse
from link.models import Link, LinkUserRole, OpticalFiber, DistriFramePort, ElementLink
from urllib import parse
from datetime import date
import json

class LinkTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
        self.cable = FiberCableManager.create_fibercable(
            number='SM-test',
            fiber_count=30,
            length=30.5,
            endpoint_1='软件园',
            endpoint_2='古脊椎',
            remarks='test-remark'
        )
        self.distriframe = DistriFrameManager.create_distriframe(
            number='test_distriframe_number1',
            model_type='sc',
            row_count=6,
            col_count=12,
            place='位于铁科大厦一层弱电间，普天72芯一体化机框',
            remarks='【51893383随机呼转张效军18618417973和张东升13910987916】51893383找罗工、唐工',
            link_org=None
        )
        self.connectorbox = ConnectorBoxManager.create_connectorbox(
            number='test_connector2',
            place='test_place2',
            remarks='',
            location='',
        )
        self.leaseline = LeaseLineManager.create_leaseline(
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

    def test_list_link(self):
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
            link_element=[]
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
            link_status=Link.LinkStatus.IDLE,
            remarks="adaeda",
            enable_date="2014-07-01",
            link_element=[
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": self.leaseline.element.id
                }
            ]
        )

        # user role 
        base_url = reverse('api:link-link-list')
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
        link = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'user', 'endpoint_a', 'endpoint_z', 'bandwidth', 'description',
            'line_type', 'business_person', 'build_person', 'link_status', 'remarks', 'enable_date'
        ], link)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # query "link_status"
        query = parse.urlencode(query={'link_status': 'abc'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 400)
        query1 = parse.urlencode(query={'link_status': Link.LinkStatus.USING})
        query2 = parse.urlencode(query={'link_status': Link.LinkStatus.IDLE})
        response = self.client.get(f'{base_url}?{query1}&{query2}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        response = self.client.get(f'{base_url}?{query1}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['link_status'], Link.LinkStatus.USING)
        self.assertEqual(response.data['results'][0]['id'], link1.id)

    def test_retrieve_link(self):
        opticalfibers = OpticalFiber.objects.all()
        distriframeports = DistriFramePort.objects.all()
        link_element=[
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": opticalfibers[1].element.id
                },
                {
                    "index": 2,
                    "sub_index": 1,
                    "element_id": distriframeports[0].element.id
                },
                {
                    "index": 2,
                    "sub_index": 2,
                    "element_id": distriframeports[1].element.id
                }
            ]
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
            link_status=Link.LinkStatus.IDLE,
            remarks="adaeda",
            enable_date="2014-07-01",
            link_element=link_element
        )

        # user role
        base_url = reverse('api:link-link-detail', kwargs={'id': link.id})
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
        base_url = reverse('api:link-link-detail', kwargs={'id': '  '})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # element not exist
        base_url = reverse('api:link-link-detail', kwargs={'id': 'asd'})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='LinkNotExist', response=response)
        
        #data
        base_url = reverse('api:link-link-detail', kwargs={'id': link.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'number', 'user', 'endpoint_a', 'endpoint_z', 'bandwidth', 'description',
            'line_type', 'business_person', 'build_person', 'link_status', 'remarks', 'enable_date',
            'link_element'
        ], response.data)
        self.assertEqual(response.data['id'], link.id)
        self.assertEqual(len(response.data['link_element']), len(link_element))
        self.assertKeysIn([
            'index', 'sub_index', 'element_data'
        ], response.data['link_element'][0])
        self.assertKeysIn([
            'type', 'lease', 'port', 'fiber', 'box'
        ], response.data['link_element'][0]['element_data'])

    def test_creat_link(self):
        opticalfibers = OpticalFiber.objects.all()
        distriframeports = DistriFramePort.objects.all()
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "bandwidth": None,
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": "using",
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": opticalfibers[1].element.id
                },
                {
                    "index": 2,
                    "sub_index": 1,
                    "element_id": distriframeports[0].element.id
                },
                {
                    "index": 2,
                    "sub_index": 2,
                    "element_id": distriframeports[1].element.id
                }
            ]
        })
        # user role
        base_url = reverse('api:link-link-list')
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user3)
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # data
        link_id = response.data
        self.assertKeysIn([
            'link_id'
        ], link_id)
        self.assertEqual(Link.objects.count(), 1)
        self.assertEqual(ElementLink.objects.count(), 4)
        self.assertEqual(ElementLink.objects.first().link.id, Link.objects.first().id)
        # validate params
        #无效的 link_status
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": "eeeeee",
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[1].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 重复的index和sub_index
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[1].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 无效的 index序列
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 6,
                    "sub_index": 1,
                    "element_id": opticalfibers[1].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 重复的element_id
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": opticalfibers[0].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 重复的element_id
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": opticalfibers[0].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 重复的element_id
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": opticalfibers[0].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 相同链路位置网元类型不相同
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": distriframeports[0].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 在已经建立链路的网元（不可重复建立链路的网元）上再次建立链路
        ElementLink.objects.all().delete()
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                },
                {
                    "index": 1,
                    "sub_index": 2,
                    "element_id": opticalfibers[1].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.dumps({
            "number": "KY23092702",
            "user": "空天院-中国遥感卫星地面站",
            "endpoint_a": "空天院新技术园区B座A301机房，王萌13811835852",
            "endpoint_z": "海淀区丰贤东路5号，中国资源卫星应用中心一期楼三层机房A301，吴郡13811754165，光缆施工联系沈老师13810428468，布跳线联系徐工13521066224",
            "description": "中国遥感卫星地面站至中国资源卫星应用中心高分项目专线（裸纤）",
            "line_type": "科技云科技专线",
            "business_person": "周建虎",
            "build_person": "胡亮亮、王振伟",
            "link_status": Link.LinkStatus.USING,
            "remarks": "adaeda",
            "enable_date": "2014-07-01",
            "link_element": [
                {
                    "index": 1,
                    "sub_index": 1,
                    "element_id": opticalfibers[0].element.id
                }
            ]
        })
        response = self.client.post(base_url, data=data, content_type='application/json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
