import time
from decimal import Decimal
from datetime import timedelta
from urllib import parse

from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache as django_cache
from django.conf import settings

from monitor.models import (
    MonitorJobCeph, MonitorJobServer, WebsiteDetectionPoint,
    MonitorWebsite, MonitorWebsiteRecord, MonitorWebsiteTask, MonitorWebsiteVersion, get_str_hash,
    MonitorJobTiDB, LogSite
)
from monitor.managers import (
    VideoMeetingQueryChoices, WebsiteQueryChoices, MonitorWebsiteManager
)
from monitor.utils import MonitorEmailAddressIPRestrictor
from bill.models import PayApp, PayAppService
from order.models import Price
from utils.test import (
    get_or_create_user, get_test_case_settings, get_or_create_organization,
    MyAPITestCase, get_or_create_org_data_center
)
from service.models import OrgDataCenter

from .tests import (
    get_or_create_monitor_job_meeting, get_or_create_monitor_provider
)
from ..handlers.monitor_website import TaskSchemeType


class MonitorVideoMeetingTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.client.force_login(user=self.user)

    def query_response(self, query_tag: str = None):
        querys = {}
        if query_tag:
            querys['query'] = query_tag

        url = reverse('monitor-api:video-meeting-query-list')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, query_tag: str):
        response = self.query_response(query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        data_item = response.data[0]
        self.assertKeysIn(["value", "monitor"], data_item)
        self.assertKeysIn(["name", "name_en", "job_tag"], data_item["monitor"])
        self.assertIsInstance(data_item["value"], list)
        values = data_item["value"]
        self.assertKeysIn(['value', 'metric'], values[0])
        self.assertKeysIn(['name', 'longitude', 'latitude', 'ipv4s'], values[0]['metric'])
        self.assertIsInstance(values[0]['metric']["ipv4s"], list)
        return response

    def test_query(self):
        get_or_create_monitor_job_meeting()

        # no permission
        # response = self.query_response(query_tag=VideoMeetingQueryChoices.NODE_STATUS.value)
        # self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin permission
        # self.user.set_federal_admin()
        self.query_ok_test(query_tag=VideoMeetingQueryChoices.NODE_STATUS.value)
        self.query_ok_test(query_tag=VideoMeetingQueryChoices.NODE_LATENCY.value)


class MonitorWebsiteTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')

    def test_create_website_task(self):
        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        app = app
        po = get_or_create_organization(name='机构')
        po.save()
        app_service1 = PayAppService(
            name='website monitor', app=app, orgnazition=po
        )
        app_service1.save()

        price = Price(
            vm_ram=Decimal('0.0'),
            vm_cpu=Decimal('0.0'),
            vm_disk=Decimal('0'),
            vm_pub_ip=Decimal('0'),
            vm_upstream=Decimal('0'),
            vm_downstream=Decimal('1'),
            vm_disk_snap=Decimal('0'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66,
            mntr_site_base=Decimal('0.3'),
            mntr_site_tamper=Decimal('0.2'),
            mntr_site_security=Decimal('0.5')
        )
        price.save()

        # NotAuthenticated
        url = reverse('monitor-api:website-list')
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.c', 'uri': '/', 'remark': 'test'
        }, content_type='application/json')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # InvalidUrl
        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.c', 'uri': '/', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUrl', response=r)

        # InvalidUri
        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.com', 'uri': '', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.com', 'uri': 'a/b/c', 'remark': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        self.client.force_login(self.user)
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=r)
        site_version_ins = MonitorWebsiteVersion.get_instance()
        site_version_ins.pay_app_service_id = app_service1.id
        site_version_ins.save(update_fields=['pay_app_service_id'])

        # balance 100
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        userpointaccount = self.user.userpointaccount
        userpointaccount.balance = Decimal('99')
        userpointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        userpointaccount.balance = Decimal('100')
        userpointaccount.save(update_fields=['balance'])

        # user, 1 ok
        website_url = 'https://test.cn/a/b?test=1&c=6#test'
        r = self.client.post(path=url, data={
            'name': 'name-test', 'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True, 'remark': 'test'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name-test', 'url': website_url,
            'remark': 'test', 'url_hash': get_str_hash(website_url),
            'scheme': 'https://', 'hostname': 'test.cn', 'uri': '/a/b?test=1&c=6#test',
            'is_tamper_resistant': True
        }, d=r.data)

        website_id = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 1)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id)
        self.assertEqual(website.name, 'name-test')
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test.cn')
        self.assertEqual(website.uri, '/a/b?test=1&c=6#test')
        self.assertIs(website.is_tamper_resistant, True)
        self.assertEqual(website.full_url, website_url)
        self.assertEqual(website.remark, 'test')

        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url)
        self.assertEqual(task.url_hash, website.url_hash)
        self.assertIs(task.is_tamper_resistant, True)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 1)

        # user, 2 ok
        website_url2 = 'https://test66.com/'
        r = self.client.post(path=url, data={
            'name': 'name-test666', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/', 'remark': '测试t88'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        userpointaccount.balance = Decimal('103')
        userpointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name-test666', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/', 'remark': '测试t88'
        })
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name-test666', 'url': website_url2,
            'remark': '测试t88', 'url_hash': get_str_hash(website_url2)
        }, d=r.data)

        website_id2 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 2)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id2)
        self.assertEqual(website.name, 'name-test666')
        self.assertEqual(website.full_url, website_url2)
        self.assertEqual(website.remark, '测试t88')
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test66.com')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 2)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url2)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 2)

        # user2, 1 ok
        self.client.logout()
        self.client.force_login(self.user2)

        # balance 100
        website_url3 = 'https://test3.cnn/'
        r = self.client.post(path=url, data={
            'name': 'name3-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/', 'remark': '3test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount = self.user2.userpointaccount
        user2pointaccount.balance = Decimal('99')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name3-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/', 'remark': '3test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount.balance = Decimal('100')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name3-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/', 'remark': '3test'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name3-test', 'url': website_url3,
            'remark': '3test', 'url_hash': get_str_hash(website_url3)
        }, d=r.data)

        website_id3 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id3)
        self.assertEqual(website.name, 'name3-test')
        self.assertEqual(website.full_url, website_url3)
        self.assertEqual(website.remark, '3test')
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test3.cnn')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 3)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_url3)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 3)

        # user2, TargetAlreadyExists; website_url3='https://test3.cnn'
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test3.cnn', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        # user2, 2 ok, website_url2 = 'https://test66.com/'
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount.balance = Decimal('100.3')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        user2pointaccount.balance = Decimal('100.5')
        user2pointaccount.save(update_fields=['balance'])

        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'https://', 'hostname': 'test66.com', 'uri': '/',
            'is_tamper_resistant': True, 'remark': '4test'
        })
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)
        self.assert_is_subdict_of(sub={
            'name': 'name4-test', 'url': website_url2,
            'remark': '4test', 'url_hash': get_str_hash(website_url2)
        }, d=r.data)

        website_id4 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 4)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_id4)
        self.assertEqual(website.name, 'name4-test')
        self.assertEqual(website.full_url, website_url2)
        self.assertEqual(website.remark, '4test')
        self.assertEqual(website.scheme, 'https://')
        self.assertEqual(website.hostname, 'test66.com')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, True)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 3)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation')[1]
        self.assertEqual(task.url, website_url2)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, True)
        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 4)

        # tcp test
        user2pointaccount.balance = Decimal('130')
        user2pointaccount.save(update_fields=['balance'])
        website_tcp1 = 'tcp://testtcp.com:22/'
        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '/a/b.txt', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '', 'remark': 'test tcp'
        })

        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:', 'uri': '/a/b.txt', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:22', 'uri': '/a/b.txt', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:220000', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:test', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp:sss.com:test', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:22', 'uri': '/', 'remark': 'test tcp'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)

        self.assert_is_subdict_of(sub={
            'name': 'tcp1-test', 'url': website_tcp1,
            'remark': 'test tcp', 'url_hash': get_str_hash(website_tcp1)
        }, d=r.data)

        website_tcpid5 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 5)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_tcpid5)
        self.assertEqual(website.name, 'tcp1-test')
        self.assertEqual(website.full_url, website_tcp1)
        self.assertEqual(website.remark, 'test tcp')
        self.assertEqual(website.scheme, 'tcp://')
        self.assertEqual(website.hostname, 'testtcp.com:22')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)

        self.assertEqual(MonitorWebsiteTask.objects.count(), 4)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_tcp1)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)
        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 5)

        # user2, TargetAlreadyExists; website_tcp1='tcp://testtcp.com:22'
        r = self.client.post(path=url, data={
            'name': 'name4-test', 'scheme': 'tcp://', 'hostname': 'testtcp.com:22', 'uri': '/',
            'is_tamper_resistant': False, 'remark': '4test'
        })
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        website_tcp2 = 'tcp://111.111.111.111:22/'
        r = self.client.post(path=url, data={
            'name': 'tcp1-test', 'scheme': 'tcp://', 'hostname': '111.111.111.111:22', 'uri': '/a/b.txt',
            'remark': 'test tcp'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUri', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp2-test', 'scheme': 'tcp://', 'hostname': '111.111.111.111:22', 'uri': '/',
            'remark': 'test tcp2', 'is_tamper_resistant': True
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        r = self.client.post(path=url, data={
            'name': 'tcp2-test', 'scheme': 'tcp://', 'hostname': '111.111.111.111:22', 'uri': '/',
            'remark': 'test tcp2', 'is_tamper_resistant': False
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'], container=r.data)

        self.assert_is_subdict_of(sub={
            'name': 'tcp2-test', 'url': website_tcp2,
            'remark': 'test tcp2', 'url_hash': get_str_hash(website_tcp2)
        }, d=r.data)

        website_tcpid6 = r.data['id']
        self.assertEqual(MonitorWebsite.objects.count(), 6)
        website: MonitorWebsite = MonitorWebsite.objects.get(id=website_tcpid6)
        self.assertEqual(website.name, 'tcp2-test')
        self.assertEqual(website.full_url, website_tcp2)
        self.assertEqual(website.remark, 'test tcp2')
        self.assertEqual(website.scheme, 'tcp://')
        self.assertEqual(website.hostname, '111.111.111.111:22')
        self.assertEqual(website.uri, '/')
        self.assertIs(website.is_tamper_resistant, False)   # tcp不支持

        self.assertEqual(MonitorWebsiteTask.objects.count(), 5)
        task: MonitorWebsiteTask = MonitorWebsiteTask.objects.order_by('-creation').first()
        self.assertEqual(task.url, website_tcp2)
        self.assertEqual(task.url_hash, get_str_hash(website.full_url))
        self.assertIs(task.is_tamper_resistant, False)
        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 6)

    def test_list_website_task(self):
        odc1 = OrgDataCenter(name='odc1', name_en='odc en', organization=None)
        odc1.save(force_insert=True)

        # NotAuthenticated
        base_url = reverse('monitor-api:website-list')
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # ok, no data
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 0)

        # add data
        nt = timezone.now()
        user_tcp_task1 = MonitorWebsite(
            name='tcp_task1', scheme='tcp://', hostname='2222.com:8888', uri='/', is_tamper_resistant=False,
            remark='remark tcp_task1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_tcp_task1.save(force_insert=True)

        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='11.com', uri='/', is_tamper_resistant=True,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.save(force_insert=True)

        nt = timezone.now()
        user_website2 = MonitorWebsite(
            name='name2', scheme='https://', hostname='222.com', uri='/', is_tamper_resistant=False,
            remark='remark2', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website2.save(force_insert=True)

        nt = timezone.now()
        user2_website1 = MonitorWebsite(
            name='name3', scheme='https://', hostname='333.com', uri='/', is_tamper_resistant=True,
            remark='remark3', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website1.save(force_insert=True)

        nt = timezone.now()
        user_website6 = MonitorWebsite(
            name='name66', scheme='https://', hostname='666.com', uri='/a/b?a=6&c=6#test', is_tamper_resistant=False,
            remark='remark66', user_id=self.user.id, odc=odc1, creation=nt, modification=nt
        )
        user_website6.save(force_insert=True)

        nt = timezone.now()
        odc_website7 = MonitorWebsite(
            name='name77', scheme='tcps://', hostname='777.com', uri='/', is_tamper_resistant=False,
            remark='remark77', user_id=None, odc=odc1, creation=nt, modification=nt
        )
        odc_website7.save(force_insert=True)

        # ok, list
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'is_tamper_resistant', 'url',
            'remark', 'url_hash', 'creation', 'user', 'modification', 'is_attention', 'odc'
        ], container=r.data['results'][0])
        self.assert_is_subdict_of(sub={
            'name': user_website6.name, 'url': user_website6.full_url,
            'remark': user_website6.remark, 'url_hash': user_website6.url_hash,
            'scheme': 'https://', 'hostname': '666.com', 'uri': '/a/b?a=6&c=6#test',
            'is_tamper_resistant': False
        }, d=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][0]['user']['username'], self.user.username)
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['odc'])

        # ok, list, page_size
        query = parse.urlencode(query={'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], user_website6.id)
        self.assertEqual(r.data['results'][1]['id'], user_website2.id)

        # ok, list, page, page_size
        query = parse.urlencode(query={'page': 2, 'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], user_website1.id)
        self.assertEqual(r.data['results'][1]['id'], user_tcp_task1.id)

        # ok, list, scheme
        query = parse.urlencode(query={'scheme': TaskSchemeType.TCP.value})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], user_tcp_task1.id)

        # odc admin test
        odc1.users.add(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 5)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(len(r.data['results']), 5)

        query = parse.urlencode(query={'scheme': TaskSchemeType.TCP.value})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], odc_website7.id)
        self.assertEqual(r.data['results'][1]['id'], user_tcp_task1.id)

    def test_delete_website_task(self):
        # NotAuthenticated
        url = reverse('monitor-api:website-detail', kwargs={'id': 'test'})
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='11.com', uri='/', is_tamper_resistant=False,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.url = user_website1.full_url
        user_website1.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=user_website1.full_url, is_tamper_resistant=True)
        task1.save(force_insert=True)

        nt = timezone.now()
        website_url2 = 'https://222.com/'
        user_website2 = MonitorWebsite(
            name='name2',  scheme='https://', hostname='222.com', uri='/', is_tamper_resistant=True,
            remark='remark2', user_id=self.user.id, creation=nt, modification=nt
        )
        self.assertEqual(user_website2.full_url, website_url2)
        user_website2.save(force_insert=True)
        task2 = MonitorWebsiteTask(url=user_website2.full_url, is_tamper_resistant=True)
        task2.save(force_insert=True)

        nt = timezone.now()
        user2_website2 = MonitorWebsite(
            name='name22', scheme='https://', hostname='222.com', uri='/', is_tamper_resistant=False,
            remark='remark22', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website2.save(force_insert=True)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 2)

        # ok, NotFound
        self.client.force_login(self.user)
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user delete user2's website
        url = reverse('monitor-api:website-detail', kwargs={'id': user2_website2.id})
        r = self.client.delete(path=url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user delete website1 ok
        url = reverse('monitor-api:website-detail', kwargs={'id': user_website1.id})
        r = self.client.delete(path=url)
        self.assertEqual(r.status_code, 204)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 2)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        self.assertEqual(MonitorWebsiteRecord.objects.count(), 1)
        record1: MonitorWebsiteRecord = MonitorWebsiteRecord.objects.first()
        self.assertEqual(user_website1.full_url, record1.full_url)
        self.assertEqual(user_website1.creation, record1.creation)
        self.assertEqual(record1.type, MonitorWebsiteRecord.RecordType.DELETED.value)

        # user delete website2 ok
        task2.refresh_from_db()
        self.assertIs(task2.is_tamper_resistant, True)
        url = reverse('monitor-api:website-detail', kwargs={'id': user_website2.id})
        r = self.client.delete(path=url)
        self.assertEqual(r.status_code, 204)
        task2.refresh_from_db()
        self.assertIs(task2.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 2)
        self.assertEqual(MonitorWebsite.objects.count(), 1)
        self.assertEqual(MonitorWebsiteTask.objects.count(), 1)
        task = MonitorWebsiteTask.objects.first()
        self.assertEqual(task.url, user2_website2.full_url)
        self.assertEqual(MonitorWebsiteRecord.objects.count(), 2)

    def test_task_version_list(self):
        url = reverse('monitor-api:website-task-version')
        r = self.client.get(path=url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['version'], 0)

        v = MonitorWebsiteVersion.get_instance()
        v.version = 66
        v.save(update_fields=['version'])

        r = self.client.get(path=url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['version'], 66)

        task1 = MonitorWebsiteTask(url='https://11.com/', is_tamper_resistant=True)
        task1.save(force_insert=True)
        task2 = MonitorWebsiteTask(url='https://22.com/', is_tamper_resistant=True)
        task2.save(force_insert=True)
        task3 = MonitorWebsiteTask(url='https://33.com/', is_tamper_resistant=False)
        task3.save(force_insert=True)
        task4 = MonitorWebsiteTask(url='https://44.com/', is_tamper_resistant=False)
        task4.save(force_insert=True)

        # list task
        base_url = reverse('monitor-api:website-task-list')
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'has_next', 'page_size', 'marker', 'next_marker', 'results'
        ], container=r.data)
        self.assertEqual(r.data['has_next'], False)
        self.assertEqual(r.data['page_size'], 2000)
        self.assertIsNone(r.data['marker'])
        self.assertIsNone(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn(keys=['url', 'url_hash', 'creation', 'is_tamper_resistant'], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['url'], task4.url)

        # list task, query "page_size"
        query = parse.urlencode(query={'page_size': 2})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['has_next'], True)
        self.assertEqual(r.data['page_size'], 2)
        self.assertIsNone(r.data['marker'])
        self.assertIsNotNone(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['url'], task4.url)
        next_marker = r.data['next_marker']

        # list task, query "page_size" and "marker"
        query = parse.urlencode(query={'page_size': 2, 'marker': next_marker})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['has_next'], False)
        self.assertEqual(r.data['page_size'], 2)
        self.assertEqual(r.data['marker'], next_marker)
        self.assertIsNone(r.data['next_marker'])
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['url'], task2.url)

    def test_change_website_task(self):
        # NotAuthenticated
        url = reverse('monitor-api:website-detail', kwargs={'id': 'test'})
        r = self.client.put(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        website_url1 = 'https://111.com/'
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=False,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.url = user_website1.full_url
        user_website1.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=user_website1.full_url, is_tamper_resistant=False)
        task1.save(force_insert=True)

        nt = timezone.now()
        website_url2 = 'https://2222.com/'
        user_website2 = MonitorWebsite(
            name='name2', scheme='https://', hostname='2222.com', uri='/', is_tamper_resistant=True,
            remark='remark2', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website2.url = user_website2.full_url
        user_website2.save(force_insert=True)
        task1 = MonitorWebsiteTask(url=user_website2.full_url, is_tamper_resistant=True)
        task1.save(force_insert=True)

        nt = timezone.now()
        user2_website2 = MonitorWebsite(
            name='name222', scheme='https://', hostname='2222.com', uri='/', is_tamper_resistant=False,
            remark='remark222', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website2.url = user2_website2.full_url
        user2_website2.save(force_insert=True)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].url, website_url2)
        self.assertEqual(tasks[1].url, website_url1)

        # ok, NotFound
        self.client.force_login(self.user)
        url = reverse('monitor-api:website-detail', kwargs={'id': 'test'})

        # no "name"， BadRequest
        r = self.client.put(path=url, data={
            'scheme': 'https://', 'hostname': 'ccc.com', 'uri': '/', 'is_tamper_resistant': True, 'remark': ''})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        # NotFound
        data = {'name': 'test', 'scheme': 'https://', 'hostname': 'ccc.com', 'uri': '/',
                'is_tamper_resistant': True, 'remark': ''}
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user change user2's website
        url = reverse('monitor-api:website-detail', kwargs={'id': user2_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user change website1 name, ok
        data = {'name': 'change name', 'scheme': user_website1.scheme, 'hostname': user_website1.hostname,
                'uri': user_website1.uri, 'is_tamper_resistant': user_website1.is_tamper_resistant,
                'remark': user_website1.remark}
        url = reverse('monitor-api:website-detail', kwargs={'id': user_website1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website1 = MonitorWebsite.objects.get(id=user_website1.id)
        self.assertEqual(website1.name, 'change name')
        self.assertEqual(website1.full_url, user_website1.url)
        self.assertEqual(website1.remark, user_website1.remark)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 0)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].url, website_url2)
        self.assertIs(tasks[0].is_tamper_resistant, True)
        self.assertEqual(tasks[1].url, website_url1)
        self.assertIs(tasks[1].is_tamper_resistant, False)

        # user change website1 "name" and "url", InvalidUrl
        r = self.client.put(path=url, data={
            'name': 'nametest', 'scheme': 'https://', 'hostname': 'ccc', 'uri': '/', 'remark': ''})
        self.assertErrorResponse(status_code=400, code='InvalidUrl', response=r)

        # user change website1 "name" and "url", ok
        new_website_url1 = 'https://666.cn/'
        data = {'name': user_website1.name, 'scheme': 'https://', 'hostname': '666.cn', 'uri': '/',
                'remark': user_website1.remark}
        url = reverse('monitor-api:website-detail', kwargs={'id': user_website1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website1 = MonitorWebsite.objects.get(id=user_website1.id)
        self.assertEqual(website1.name, user_website1.name)
        self.assertEqual(website1.full_url, new_website_url1)
        self.assertEqual(website1.remark, user_website1.remark)
        self.assertKeysIn(keys=[
            'id', 'name', 'scheme', 'hostname', 'uri', 'url', 'is_tamper_resistant',
            'remark', 'url_hash', 'creation', 'modification', 'is_attention'
        ], container=r.data)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 1)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1].url, website_url2)
        self.assertIs(tasks[1].is_tamper_resistant, True)
        self.assertEqual(tasks[0].url, new_website_url1)
        self.assertIs(tasks[0].is_tamper_resistant, False)

        # user change website2 "remark" and "uri", ok
        new_website_url2 = 'https://888.cn/a/?b=6&c=8#test'
        data = {'name': user_website2.name, 'scheme': 'https://', 'hostname': '888.cn', 'uri': '/a/?b=6&c=8#test',
                'remark': '新的 remark'}
        url = reverse('monitor-api:website-detail', kwargs={'id': user_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website2 = MonitorWebsite.objects.get(id=user_website2.id)
        self.assertEqual(website2.name, user_website2.name)
        self.assertEqual(website2.full_url, new_website_url2)
        self.assertEqual(website2.remark, '新的 remark')
        self.assertIs(website2.is_tamper_resistant, True)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 2)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].url, new_website_url2)
        self.assertIs(tasks[0].is_tamper_resistant, True)
        self.assertEqual(tasks[1].url, new_website_url1)
        self.assertIs(tasks[1].is_tamper_resistant, False)
        self.assertEqual(tasks[2].url, website_url2)
        self.assertIs(tasks[2].is_tamper_resistant, False)

        # user change website2 "is_tamper_resistant", ok
        data = {'name': user_website2.name, 'scheme': 'https://', 'hostname': '888.cn', 'uri': '/a/?b=6&c=8#test',
                'is_tamper_resistant': False, 'url': new_website_url2, 'remark': '新的 remark'}
        url = reverse('monitor-api:website-detail', kwargs={'id': user_website2.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        website2 = MonitorWebsite.objects.get(id=user_website2.id)
        self.assertEqual(website2.name, user_website2.name)
        self.assertEqual(website2.full_url, new_website_url2)
        self.assertEqual(website2.remark, '新的 remark')
        self.assertIs(website2.is_tamper_resistant, False)

        version = MonitorWebsiteVersion.get_instance()
        self.assertEqual(version.version, 3)
        self.assertEqual(MonitorWebsite.objects.count(), 3)
        tasks = MonitorWebsiteTask.objects.order_by('-creation').all()
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0].url, new_website_url2)
        self.assertIs(tasks[0].is_tamper_resistant, False)
        self.assertEqual(tasks[1].url, new_website_url1)
        self.assertIs(tasks[1].is_tamper_resistant, False)
        self.assertEqual(tasks[2].url, website_url2)
        self.assertIs(tasks[2].is_tamper_resistant, False)

        # tcp test
        nt = timezone.now()
        user1_tcp_task1 = MonitorWebsite(
            name='tcp_task1', scheme='tcp://', hostname='2222.com:8888', uri='/', is_tamper_resistant=False,
            remark='remark tcp_task1', user_id=self.user.id, creation=nt, modification=nt
        )
        user1_tcp_task1.save(force_insert=True)

        data = {'name': user1_tcp_task1.name, 'scheme': 'tcp://', 'hostname': '2222.com:8888', 'uri': '/',
                'is_tamper_resistant': True, 'remark': '新的 remark'}
        url = reverse('monitor-api:website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        data = {'name': user1_tcp_task1.name, 'scheme': 'tcp://', 'hostname': '2222.com', 'uri': '/',
                'remark': '新的 remark'}
        url = reverse('monitor-api:website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidHostname', response=r)

        data = {'name': user1_tcp_task1.name, 'scheme': 'tcp://', 'hostname': '2222.cn:666', 'uri': '/',
                'remark': '新的 remark'}
        url = reverse('monitor-api:website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)
        user1_tcp_task1.refresh_from_db()
        self.assertEqual(user1_tcp_task1.hostname, '2222.cn:666')

        data = {'name': user1_tcp_task1.name, 'scheme': 'https://', 'hostname': '2222.cn:666', 'uri': '/',
                'remark': '新的 remark'}
        url = reverse('monitor-api:website-detail', kwargs={'id': user1_tcp_task1.id})
        r = self.client.put(path=url, data=data)
        self.assertEqual(r.status_code, 200)

    def test_list_website_detection_point(self):
        # NotAuthenticated
        base_url = reverse('monitor-api:website-detection-point')
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # ok, no data
        self.client.force_login(self.user)
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 0)

        # add data
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en2', creation=nt, modification=nt, remark='remark2', enable=False
        )
        detection_point2.save(force_insert=True)

        # ok, list
        r = self.client.get(path=base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 1)
        self.assertIsInstance(r.data['results'], list)
        self.assertEqual(len(r.data['results']), 2)

        # ok, list, page_size
        query = parse.urlencode(query={'page_size': 1})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point2.id)

        # ok, list, page, page_size
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point1.id)

        # query "enable" true
        query = parse.urlencode(query={'enable': True})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point1.id)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'remark', 'modification', 'creation', 'enable'
        ], container=r.data['results'][0])

        # query "enable" false
        query = parse.urlencode(query={'enable': False})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], detection_point2.id)

    def test_website_task_attention_mark(self):
        # NotAuthenticated
        url = reverse('monitor-api:website-mark-attention', kwargs={'id': 'test'})
        r = self.client.post(path=url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # add data
        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='111.com', uri='/', remark='remark1', user_id=self.user.id,
            creation=nt, modification=nt, is_attention=False
        )
        user_website1.save(force_insert=True)

        self.client.force_login(self.user2)

        # query "action"
        url = reverse('monitor-api:website-mark-attention', kwargs={'id': 'test'})
        r = self.client.post(path=url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'action': ''})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'action': 'marttt'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # NotFound
        url = reverse('monitor-api:website-mark-attention', kwargs={'id': 'test'})
        query = parse.urlencode(query={'action': 'mark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # AccessDenied, user2 change user's website
        url = reverse('monitor-api:website-mark-attention', kwargs={'id': user_website1.id})
        query = parse.urlencode(query={'action': 'mark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.logout()
        self.client.force_login(self.user)

        # user2 mark website1, ok
        url = reverse('monitor-api:website-mark-attention', kwargs={'id': user_website1.id})
        query = parse.urlencode(query={'action': 'mark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'url', 'remark', 'url_hash', 'creation', 'modification', 'is_attention'
        ], container=r.data)

        user_website1.refresh_from_db()
        self.assertIs(user_website1.is_attention, True)

        # user2 unmark website1, ok
        url = reverse('monitor-api:website-mark-attention', kwargs={'id': user_website1.id})
        query = parse.urlencode(query={'action': 'unMark'})
        r = self.client.post(path=f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'url', 'remark', 'url_hash', 'creation', 'modification', 'is_attention'
        ], container=r.data)

        user_website1.refresh_from_db()
        self.assertIs(user_website1.is_attention, False)

    @staticmethod
    def _set_iprestrict_rule(ips: list):
        setattr(settings, MonitorEmailAddressIPRestrictor.SETTING_KEY_NAME, ips)
        mea_ip_rt = MonitorEmailAddressIPRestrictor()
        mea_ip_rt.reload_ip_rules()
        MonitorEmailAddressIPRestrictor.allowed_ips = mea_ip_rt.allowed_ips

    def test_list_site_emails(self):
        self._set_iprestrict_rule(ips=[])

        base_url = reverse('monitor-api:website-user-email')
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        query = parse.urlencode(query={'url_hash': ''})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'url_hash': 'xxxx'})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.force_login(self.user)
        r = self.client.get(reverse('api:email-realip'))
        real_ip = r.data['real_ip']
        self._set_iprestrict_rule(ips=[real_ip])
        self.client.logout()

        # ok, no data
        url_hash = 'xxxx'
        query = parse.urlencode(query={'url_hash': url_hash})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['url_hash', 'results'], container=r.data)
        self.assertEqual(r.data['url_hash'], url_hash)
        self.assertEqual(len(r.data['results']), 0)

        # add data
        user3 = get_or_create_user(username='lisi@qq.com')
        nt = timezone.now()
        user_website1 = MonitorWebsite(
            name='name1', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=True,
            remark='remark1', user_id=self.user.id, creation=nt, modification=nt
        )
        user_website1.save(force_insert=True)

        nt = timezone.now()
        user2_website1 = MonitorWebsite(
            name='name2', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=False,
            remark='remark2', user_id=self.user2.id, creation=nt, modification=nt
        )
        user2_website1.save(force_insert=True)

        nt = timezone.now()
        user3_website3 = MonitorWebsite(
            name='name3', scheme='https://', hostname='333.com', uri='/', is_tamper_resistant=True,
            remark='remark3', user_id=user3.id, creation=nt, modification=nt
        )
        user3_website3.save(force_insert=True)

        # ok, list
        url_hash = user_website1.url_hash
        query = parse.urlencode(query={'url_hash': url_hash})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['url_hash', 'results'], container=r.data)
        self.assertEqual(r.data['url_hash'], url_hash)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'scheme', 'hostname', 'uri', 'email'
        ], container=r.data['results'][0])
        for item in r.data['results']:
            url1 = item['scheme'] + item['hostname'] + item['uri']
            self.assertEqual(url1, user2_website1.full_url)
            self.assertIn(item['email'], [self.user.username, self.user2.username])

        # test odc
        user4 = get_or_create_user(username='u4@cstnet.cn')
        odc1 = OrgDataCenter(name='odc1', name_en='odc1 en', organization=None)
        odc1.save(force_insert=True)
        odc2 = OrgDataCenter(name='odc2', name_en='odc2 en', organization=None)
        odc2.save(force_insert=True)
        nt = timezone.now()
        odc1_website1 = MonitorWebsite(
            name='odc name1', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=False,
            remark='remark odc', user_id=None, odc=odc1, creation=nt, modification=nt
        )
        odc1_website1.save(force_insert=True)
        nt = timezone.now()
        odc2_website1 = MonitorWebsite(
            name='odc name2', scheme='https://', hostname='111.com', uri='/', is_tamper_resistant=False,
            remark='remark odc2', user_id=None, odc=odc2, creation=nt, modification=nt
        )
        odc2_website1.save(force_insert=True)

        query = parse.urlencode(query={'url_hash': url_hash})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['url_hash', 'results'], container=r.data)
        self.assertEqual(r.data['url_hash'], url_hash)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'scheme', 'hostname', 'uri', 'email'
        ], container=r.data['results'][0])
        for item in r.data['results']:
            url1 = item['scheme'] + item['hostname'] + item['uri']
            self.assertEqual(url1, user2_website1.full_url)
            self.assertIn(item['email'], [self.user.username, self.user2.username])

        odc1.users.add(self.user, self.user2, user3)
        odc2.users.add(self.user2, user4)
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['url_hash', 'results'], container=r.data)
        self.assertEqual(r.data['url_hash'], url_hash)
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn(keys=[
            'scheme', 'hostname', 'uri', 'email'
        ], container=r.data['results'][0])
        for item in r.data['results']:
            url1 = item['scheme'] + item['hostname'] + item['uri']
            self.assertEqual(url1, user2_website1.full_url)
            self.assertIn(item['email'], [self.user.username, self.user2.username, user3.username, user4.username])

        ret_emails = [item['email'] for item in r.data['results']]
        ret_emails.sort()
        target_emails = [self.user.username, self.user2.username, user3.username, user4.username]
        target_emails.sort()
        self.assertEqual(ret_emails, target_emails)

    def test_split_http_url(self):
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='HttPs://User:passWd@Host:port/a/b?c=1&d=6#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'User:passWd@Host:port')
        self.assertEqual(uri, '/a/b?c=1&d=6#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://user:passwd@host:port/a/b?c=1&d=6#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'user:passwd@host:port')
        self.assertEqual(uri, '/a/b?c=1&d=6#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host:port/a/b?c=1#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host:port')
        self.assertEqual(uri, '/a/b?c=1#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host/a/b?c=1#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '/a/b?c=1#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host/a/b')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '/a/b')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host/a/b?')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '/a/b')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host/')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '/')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host/?c=1#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '/?c=1#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host?c=1#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '?c=1#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host?c=t测试&d=6#frag')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '?c=t测试&d=6#frag')
        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(
            http_url='https://host/tes测试/b')
        self.assertEqual(scheme, 'https://')
        self.assertEqual(hostname, 'host')
        self.assertEqual(uri, '/tes测试/b')


class MonitorWebsiteQueryTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='tom@cnic.cn', password='password')
        self.provider = get_or_create_monitor_provider(alias='MONITOR_WEBSITE')
        testcase_settings = get_test_case_settings()
        nt = timezone.now()
        self.website = MonitorWebsite(
            name='test',
            scheme=testcase_settings['MONITOR_WEBSITE']['WEBSITE_SCHEME'],
            hostname=testcase_settings['MONITOR_WEBSITE']['WEBSITE_HOSTNAME'],
            uri=testcase_settings['MONITOR_WEBSITE']['WEBSITE_URI'],
            # url=testcase_settings['MONITOR_WEBSITE']['WEBSITE_URL'],
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        self.website.save(force_insert=True)

    def test_query(self):
        website = self.website

        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        # NotAuthenticated
        r = self.query_response(
            website_id=website.id, detection_point_id='',
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # InvalidArgument
        r = self.query_response(
            website_id=website.id, detection_point_id='detection_point_id',
            query_tag='InvalidArgument')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # Conflict, not set provider
        r = self.query_response(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # set provider
        detection_point1.provider_id = self.provider.id
        detection_point1.save(update_fields=['provider_id'])

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # NotFound
        r = self.query_response(
            website_id='websiteid', detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # NoSuchDetectionPoint
        r = self.query_response(
            website_id=website.id, detection_point_id='detection_point1.id',
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # Conflict, detection_point2 not enable
        r = self.query_response(
            website_id=website.id, detection_point_id=detection_point2.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.SUCCESS.value)
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value)
        self.query_ok_test(
            website_id=website.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value, list_len=5)

        # tcp
        nt = timezone.now()
        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1:8888',
            uri='/',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # InvalidArgument
        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.SUCCESS.value)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])
        r = self.query_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

        # NotFound
        self.client.logout()
        self.client.force_login(self.user2)
        r = self.query_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # test odc admin
        odc1 = OrgDataCenter(name='odc1', name_en='odc en', organization=None)
        odc1.save(force_insert=True)
        nt = timezone.now()
        odc_task = MonitorWebsite(
            name='test',
            scheme='https://',
            hostname='127.0.0.1:8888',
            uri='/',
            remark='', user=None, odc=odc1,
            creation=nt, modification=nt
        )
        odc_task.save(force_insert=True)
        r = self.query_response(
            website_id=odc_task.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        odc1.users.add(self.user2)
        r = self.query_response(
            website_id=odc_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

    def query_response(self, website_id: str, query_tag: str, detection_point_id: str):
        url = reverse('monitor-api:website-data-query', kwargs={'id': website_id})
        query = parse.urlencode(query={'query': query_tag, 'detection_point_id': detection_point_id})
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, website_id: str, query_tag: str, detection_point_id: str, list_len=1):
        response = self.query_response(
            website_id=website_id, query_tag=query_tag, detection_point_id=detection_point_id)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), list_len)
        data_item = response.data[0]
        self.assertKeysIn(["values", "metric"], data_item)
        self.assertEqual(self.website.full_url, data_item['metric']['url'])
        self.assertIsInstance(data_item["values"], list)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)

        return response

    def test_query_range(self):
        # query parameter test
        end = int(time.time())
        start = end - 600
        step = 300

        website = self.website
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        # NotAuthenticated
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # BadRequest, param "start"
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start='bad', end=end, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=-1, end=end, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # param "end"
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end='bad', step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=-1, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "step"
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=-1, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=0, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # param "end" >= "start" required
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=end + 1, end=end, step=step, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # 每个时间序列10000点的最大分辨率
        response = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start - 11000, end=end, step=1, detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # InvalidArgument
        r = self.query_range_response(
            website_id=website.id, query_tag='InvalidArgument', start=start, end=end, step=step,
            detection_point_id=detection_point1.id)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # NotFound
        r = self.query_range_response(
            website_id='websiteid', query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # Conflict, not set provider
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # set provider
        detection_point1.provider_id = self.provider.id
        detection_point1.save(update_fields=['provider_id'])

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)

        # NoSuchDetectionPoint
        r = self.query_range_response(
            website_id=website.id, detection_point_id='detection_point1.id',
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # Conflict, detection_point2 not enable
        r = self.query_range_response(
            website_id=website.id, detection_point_id=detection_point2.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.SUCCESS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.DURATION_SECONDS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.query_range_ok_test(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value,
            start=start, end=end, step=step, list_len=5, detection_point_id=detection_point1.id
        )

        # tcp
        nt = timezone.now()
        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1:8888',
            uri='/',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # InvalidArgument
        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.HTTP_DURATION_SECONDS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.SUCCESS.value, start=start, end=end, step=step)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])
        r = self.query_range_response(
            website_id=tcp_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value, start=start, end=end, step=step)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

        # NotFound
        self.client.logout()
        self.client.force_login(self.user2)
        r = self.query_range_response(
            website_id=website.id, query_tag=WebsiteQueryChoices.HTTP_STATUS_STATUS.value,
            start=start, end=end, step=step, detection_point_id=detection_point1.id
        )
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # test odc admin
        odc1 = OrgDataCenter(name='odc1', name_en='odc en', organization=None)
        odc1.save(force_insert=True)
        nt = timezone.now()
        odc_task = MonitorWebsite(
            name='test',
            scheme='https://',
            hostname='127.0.0.1:8888',
            uri='/',
            remark='', user=None, odc=odc1,
            creation=nt, modification=nt
        )
        odc_task.save(force_insert=True)
        r = self.query_range_response(
            website_id=odc_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value, start=start, end=end, step=step)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        odc1.users.add(self.user2)
        r = self.query_range_response(
            website_id=odc_task.id, detection_point_id=detection_point1.id,
            query_tag=WebsiteQueryChoices.DURATION_SECONDS.value, start=start, end=end, step=step)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

    def query_range_response(
            self, website_id: str, detection_point_id: str,
            query_tag: str, start: int = None, end: int = None, step: int = None,
    ):
        querys = {'detection_point_id': detection_point_id}
        if query_tag:
            querys['query'] = query_tag

        if start:
            querys['start'] = start

        if end:
            querys['end'] = end

        if query_tag:
            querys['step'] = step

        url = reverse('monitor-api:website-data-query-range', kwargs={'id': website_id})
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_range_ok_test(
            self, website_id: str, detection_point_id: str,
            query_tag: str, start: int, end: int, step: int, list_len=1
    ):
        values_len = (end - start) // step + 1
        response = self.query_range_response(
            website_id=website_id, detection_point_id=detection_point_id,
            query_tag=query_tag, start=start, end=end, step=step)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), list_len)
        data_item = response.data[0]
        self.assertKeysIn(["values", "metric"], data_item)
        self.assertEqual(self.website.full_url, data_item['metric']['url'])
        self.assertIsInstance(data_item["values"], list)
        self.assertEqual(len(data_item["values"]), values_len)
        if data_item["values"]:
            self.assertEqual(len(data_item["values"][0]), 2)

        return response

    def duration_query_response(self, start: int, end: int, detection_point_id: str):
        url = reverse('monitor-api:website-duration-distribution')
        querys = {}
        if start:
            querys['start'] = start

        if end:
            querys['end'] = end

        if detection_point_id:
            querys['detection_point_id'] = detection_point_id

        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def test_duration_distribution(self):
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True,
            provider=self.provider
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1',
            uri='/',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # NotAuthenticated
        day_ago = nt - timedelta(days=1)
        start = int(day_ago.timestamp())
        end = int(nt.timestamp())
        r = self.duration_query_response(start=start, end=end, detection_point_id='')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        # NoSuchDetectionPoint
        r = self.duration_query_response(start=start, end=end, detection_point_id='notfound')
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # Conflict, detection_point2 not enable
        r = self.duration_query_response(start=start, end=end, detection_point_id=detection_point2.id)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        r = self.duration_query_response(start=start, end=end, detection_point_id='')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        r = self.duration_query_response(start=start, end=end, detection_point_id=detection_point1.id)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)

    def _status_query_response(self, detection_point_id: str):
        url = reverse('monitor-api:website-status-overview')
        querys = {}
        if detection_point_id:
            querys['detection_point_id'] = detection_point_id

        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def test_status_overview(self):
        nt = timezone.now()
        detection_point1 = WebsiteDetectionPoint(
            name='name1', name_en='name en1', creation=nt, modification=nt, remark='remark1', enable=True,
            provider=self.provider
        )
        detection_point1.save(force_insert=True)

        nt = timezone.now()
        detection_point2 = WebsiteDetectionPoint(
            name='name2', name_en='name en1', creation=nt, modification=nt,
            remark='remark1', enable=False, provider=self.provider
        )
        detection_point2.save(force_insert=True)

        tcp_task = MonitorWebsite(
            name='test',
            scheme='tcp://',
            hostname='127.0.0.1',
            uri='/',
            remark='', user=self.user,
            creation=nt, modification=nt
        )
        tcp_task.save(force_insert=True)

        # NotAuthenticated
        r = self._status_query_response(detection_point_id='')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # NoSuchDetectionPoint
        r = self._status_query_response(detection_point_id='notfound')
        self.assertErrorResponse(status_code=404, code='NoSuchDetectionPoint', response=r)

        # 清除 可能的 探测点 缓存
        django_cache.delete(MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT)
        # Conflict, detection_point2 not enable
        r = self._status_query_response(detection_point_id=detection_point2.id)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ok
        r = self._status_query_response(detection_point_id='')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['total', 'invalid', 'valid', 'invalid_urls'], r.data)
        self.assertEqual(r.data['total'], 1)
        self.assertEqual(r.data['invalid'] + r.data['valid'], 1)
        self.assertIsInstance(r.data['invalid_urls'], list)
        self.assertEqual(len(r.data['invalid_urls']), 0)

        r = self._status_query_response(detection_point_id=detection_point1.id)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['total', 'invalid', 'valid', 'invalid_urls'], r.data)
        self.assertEqual(r.data['total'], 1)
        self.assertEqual(r.data['invalid'] + r.data['valid'], 1)
        self.assertIsInstance(r.data['invalid_urls'], list)
        self.assertEqual(len(r.data['invalid_urls']), 0)


class UnitAdminEmailTests(MyAPITestCase):
    def setUp(self):
        pass

    @staticmethod
    def _set_iprestrict_rule(ips: list):
        setattr(settings, MonitorEmailAddressIPRestrictor.SETTING_KEY_NAME, ips)
        mea_ip_rt = MonitorEmailAddressIPRestrictor()
        mea_ip_rt.reload_ip_rules()
        MonitorEmailAddressIPRestrictor.allowed_ips = mea_ip_rt.allowed_ips

    def test_list_site_emails(self):
        user = get_or_create_user(username='tom@cnic.cn', password='password')
        user2 = get_or_create_user(username='lisi@cnic.cn', password='password')
        user3 = get_or_create_user(username='zhangsan@cnic.cn', password='password')
        odc = get_or_create_org_data_center()
        odc.users.add(user)
        unit_ceph1 = MonitorJobCeph(
            name='ceph1', name_en='name_en1', job_tag='test1_ceph_metric', sort_weight=10,
            org_data_center=odc
        )
        unit_ceph1.save(force_insert=True)
        unit_ceph1.users.add(user2)
        unit_ceph2 = MonitorJobCeph(
            name='ceph2', name_en='name_en2', job_tag='test2_ceph', sort_weight=10,
            org_data_center=odc
        )
        unit_ceph2.save(force_insert=True)

        unit_server1 = MonitorJobServer(
            name='server1', name_en='name_en1', job_tag='test1_node_metric', sort_weight=10,
            org_data_center=odc
        )
        unit_server1.save(force_insert=True)
        unit_server1.users.add(user2)
        unit_server2 = MonitorJobServer(
            name='server2', name_en='name_en2', job_tag='job_node2', sort_weight=10,
            org_data_center=odc
        )
        unit_server2.save(force_insert=True)

        unit_tidb1 = MonitorJobTiDB(
            name='tidb1', name_en='name_en1', job_tag='test1_tidb_metric', sort_weight=10,
            org_data_center=odc
        )
        unit_tidb1.save(force_insert=True)
        unit_tidb1.users.add(user3)

        log_site1 = LogSite(
            name='log1', name_en='name_en1', log_type=LogSite.LogType.HTTP.value,
            site_type_id=None, job_tag='job1_log', sort_weight=10, org_data_center=None
        )
        log_site1.save(force_insert=True)
        log_site1.users.add(user3)
        log_site2 = LogSite(
            name='log22', name_en='name_en2', log_type=LogSite.LogType.HTTP.value,
            site_type_id=None, job_tag='job_taglog2', sort_weight=5,
            org_data_center=odc
        )
        log_site2.save(force_insert=True)

        self._set_iprestrict_rule(ips=[])

        base_url = reverse('monitor-api:unit-admin-email-list')
        r = self.client.get(path=base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)
        query = parse.urlencode(query={'tag': ''})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'tag': 'xxxx'})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.force_login(user)
        self._set_iprestrict_rule(ips=['127.0.0.1'])
        self.client.logout()

        # TargetNotExist
        query = parse.urlencode(query={'tag': 'xxxx'})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=r)

        # test ceph
        query = parse.urlencode(query={'tag': unit_ceph1.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['tag', 'unit', 'emails'], container=r.data)
        self.assertEqual(r.data['tag'], unit_ceph1.job_tag)
        self.assertEqual(r.data['unit']['name'], unit_ceph1.name)
        self.assertEqual(r.data['unit']['name_en'], unit_ceph1.name_en)
        self.assertEqual(len(r.data['emails']), 2)
        self.assertKeysIn(keys=[user.username, user2.username], container=r.data['emails'])

        query = parse.urlencode(query={'tag': unit_ceph2.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['tag', 'unit', 'emails'], container=r.data)
        self.assertEqual(r.data['tag'], unit_ceph2.job_tag)
        self.assertEqual(r.data['unit']['name'], unit_ceph2.name)
        self.assertEqual(r.data['unit']['name_en'], unit_ceph2.name_en)
        self.assertEqual(len(r.data['emails']), 1)
        self.assertKeysIn(keys=[user.username], container=r.data['emails'])

        # test server
        query = parse.urlencode(query={'tag': unit_server1.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['tag', 'unit', 'emails'], container=r.data)
        self.assertEqual(r.data['tag'], unit_server1.job_tag)
        self.assertEqual(r.data['unit']['name'], unit_server1.name)
        self.assertEqual(r.data['unit']['name_en'], unit_server1.name_en)
        self.assertEqual(len(r.data['emails']), 2)
        self.assertKeysIn(keys=[user.username, user2.username], container=r.data['emails'])

        query = parse.urlencode(query={'tag': unit_server2.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['tag'], unit_server2.job_tag)
        self.assertEqual(r.data['unit']['name'], unit_server2.name)
        self.assertEqual(r.data['unit']['name_en'], unit_server2.name_en)
        self.assertEqual(len(r.data['emails']), 1)
        self.assertKeysIn(keys=[user.username], container=r.data['emails'])

        # test tidb
        query = parse.urlencode(query={'tag': unit_tidb1.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['tag'], unit_tidb1.job_tag)
        self.assertEqual(r.data['unit']['name'], unit_tidb1.name)
        self.assertEqual(r.data['unit']['name_en'], unit_tidb1.name_en)
        self.assertEqual(len(r.data['emails']), 2)
        self.assertKeysIn(keys=[user.username, user3.username], container=r.data['emails'])

        # test log
        query = parse.urlencode(query={'tag': log_site1.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['tag'], log_site1.job_tag)
        self.assertEqual(r.data['unit']['name'], log_site1.name)
        self.assertEqual(r.data['unit']['name_en'], log_site1.name_en)
        self.assertEqual(len(r.data['emails']), 1)
        self.assertKeysIn(keys=[user3.username], container=r.data['emails'])

        query = parse.urlencode(query={'tag': log_site2.job_tag})
        r = self.client.get(path=f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['tag'], log_site2.job_tag)
        self.assertEqual(r.data['unit']['name'], log_site2.name)
        self.assertEqual(r.data['unit']['name_en'], log_site2.name_en)
        self.assertEqual(len(r.data['emails']), 1)
        self.assertKeysIn(keys=[user.username], container=r.data['emails'])
