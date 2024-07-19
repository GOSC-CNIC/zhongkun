from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from utils.test import get_or_create_user
from utils.test import MyAPITestCase
from utils.test import MyAPITransactionTestCase
from apps.app_alert.permission import AlertAPIIPRestrictor
from apps.users.models import UserProfile
from apps.app_alert.models import AlertModel


class ReceiverAPITests(MyAPITransactionTestCase):
    def setUp(self):
        self.super_user1, _ = UserProfile.objects.get_or_create(
            username='superuser1@cnic.cn',
            password="password",
            company="cnic",
            is_active=True,
            is_superuser=True
        )
        self.user1, _ = UserProfile.objects.get_or_create(
            username='user1@cnic.cn',
            password="password",
            company="cnic",
            is_active=True,
            is_superuser=False
        )

    def test_create(self):
        base_url = reverse('alert-api:alert-receiver')
        data = [
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.1', 'monitor': 'xinxihua',
                     'monitor_cluster': 'aiops_log', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '1source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 2/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.2', 'monitor': 'xinxihua',
                     'monitor_cluster': 'aiops_log', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '2source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 1/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },

        ]
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "AccessDenied")
        self.assertEqual(response.data["message"], "此API拒绝从IP地址'127.0.0.1'访问")
        # 添加ip 白名单
        AlertAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.2')
        AlertAPIIPRestrictor.clear_cache()  # 有缓存，需要清除缓存
        response = self.client.post(base_url, data=data)

        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "AccessDenied")
        self.assertEqual(response.data["message"], "此API拒绝从IP地址'127.0.0.1'访问")
        # 添加ip 白名单
        AlertAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        AlertAPIIPRestrictor.clear_cache()  # 有缓存，需要清除缓存
        response = self.client.post(base_url, data=data)

        self.assertKeysIn(['status'], response.data)
        self.assertEqual(response.status_code, 200)
        data = [
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.1', 'monitor': 'xinxihua',
                     'monitor_cluster': '', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '1source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 2/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.2', 'monitor': 'xinxihua',
                     'monitor_cluster': '', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '2source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 1/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },

        ]
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "InvalidArgument")
        data = [
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.1', 'monitor': 'xinxihua',
                     'monitor_cluster': 'test', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '1source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 2/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.2', 'monitor': 'xinxihua',
                     'monitor_cluster': 'test', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '2source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 1/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },

        ]
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "InvalidArgument")

    def test_list(self):
        data = [
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.1', 'monitor': 'xinxihua',
                     'monitor_cluster': 'aiops_log', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '1source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 2/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },
            {
                'labels':
                    {'alertname': 'error log', 'group': 'web', 'instance': '192.168.0.2', 'monitor': 'xinxihua',
                     'monitor_cluster': 'aiops_log', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '2source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'PHY_UPDOWN: Physical state on the interface 1/0/10 changed to down'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },

            {
                'labels':
                    {'alertname': 'high cpu', 'group': 'web', 'instance': '192.168.0.2', 'monitor': 'xinxihua',
                     'monitor_cluster': 'aiops_metric', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '2source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': 'cpu使用率过高'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },

            {
                'labels':
                    {'alertname': 'high memory', 'group': 'web', 'instance': '192.168.0.2', 'monitor': 'xinxihua',
                     'monitor_cluster': 'aiops_metric', 'receive_cluster': 'aiops_ceph_metric', 'receive_replica': '0',
                     'replica': 'A', 'severity': 'error', 'tenant_id': 'default-tenant',
                     },
                'annotations':
                    {
                        'description': '2source: mail_log level: error content: Apr 25 05:34:52 Mail_Teste interface status changes.',
                        'summary': '内存使用率过高'},
                'startsAt': '2024-04-29T11:20:14.752651787Z', 'endsAt': '2024-04-07T08:19:44.752651787Z',
                'generatorURL': 'http://xxx:9096/graph?g0.expr=probe_http_status_code+%21%3D+200&g0.tab=1'
            },

        ]
        receiver_url = reverse('alert-api:alert-receiver')
        response = self.client.post(receiver_url, data=data)
        self.assertKeysIn(['status'], response.data)
        self.assertEqual(response.status_code, 200)

        query_api = reverse('alert-api:alert-list')
        response = self.client.get(query_api)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

        self.client.force_login(self.user1)
        response = self.client.get(query_api)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])
        self.client.logout()

        self.client.force_login(self.super_user1)
        response = self.client.get(query_api)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 4)
        results = response.data['results']
        self.assertKeysIn(
            ['id', 'start', "end", "alertname", "alert_type", 'timestamp', 'startsAt', 'monitor_cluster',
             'fingerprint', 'name', 'type', 'instance', 'port', 'cluster', 'severity', 'summary', 'description',
             'status', 'count', 'creation', 'modification'
             ], results[0])
        self.assertKeysIn(
            ['id', 'start', "end", "alertname", "alert_type", 'timestamp', 'startsAt', 'monitor_cluster',
             'fingerprint', 'name', 'type', 'instance', 'port', 'cluster', 'severity', 'summary', 'description',
             'status', 'count', 'creation', 'modification'
             ], results[-1])
        self.assertTrue(isinstance(results[-1].get('id'), str))
        self.assertTrue(isinstance(results[-1].get('start'), int))
        self.assertTrue(isinstance(results[-1].get('end'), int))
        self.assertTrue(isinstance(results[-1].get('alertname'), str))
        self.assertTrue(isinstance(results[-1].get('alert_type'), str))
        self.assertTrue(isinstance(results[-1].get('timestamp'), int))
        self.assertTrue(isinstance(results[-1].get('startsAt'), str))
        self.assertTrue(isinstance(results[-1].get('monitor_cluster'), str))
        self.assertTrue(isinstance(results[-1].get('fingerprint'), str))
        self.assertTrue(isinstance(results[-1].get('name'), str))
        self.assertTrue(isinstance(results[-1].get('type'), str))
        self.assertTrue(isinstance(results[-1].get('instance'), str))
        self.assertTrue(isinstance(results[-1].get('port'), str))
        self.assertTrue(isinstance(results[-1].get('cluster'), str))
        self.assertTrue(isinstance(results[-1].get('severity'), str))
        self.assertTrue(isinstance(results[-1].get('summary'), str))
        self.assertTrue(isinstance(results[-1].get('description'), str))
        self.assertTrue(isinstance(results[-1].get('status'), str))
        self.assertTrue(isinstance(results[-1].get('count'), int))
        self.assertTrue(isinstance(results[-1].get('creation'), float))
        self.assertTrue(isinstance(results[-1].get('modification'), int))
        self.assertTrue(results[1].get('status') == AlertModel.AlertStatus.FIRING.value)
        self.assertTrue(results[1].get('count') == 1)
        receiver_url = reverse('alert-api:alert-receiver')
        response = self.client.post(receiver_url, data=data)
        self.assertKeysIn(['status'], response.data)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(query_api)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 4)
        results = response.data['results']
        self.assertTrue(isinstance(results[-1].get('id'), str))
        self.assertTrue(isinstance(results[-1].get('start'), int))
        self.assertTrue(isinstance(results[-1].get('end'), int))
        self.assertTrue(isinstance(results[-1].get('alertname'), str))
        self.assertTrue(isinstance(results[-1].get('alert_type'), str))
        self.assertTrue(isinstance(results[-1].get('timestamp'), int))
        self.assertTrue(isinstance(results[-1].get('startsAt'), str))
        self.assertTrue(isinstance(results[-1].get('monitor_cluster'), str))
        self.assertTrue(isinstance(results[-1].get('fingerprint'), str))
        self.assertTrue(isinstance(results[-1].get('name'), str))
        self.assertTrue(isinstance(results[-1].get('type'), str))
        self.assertTrue(isinstance(results[-1].get('instance'), str))
        self.assertTrue(isinstance(results[-1].get('port'), str))
        self.assertTrue(isinstance(results[-1].get('cluster'), str))
        self.assertTrue(isinstance(results[-1].get('severity'), str))
        self.assertTrue(isinstance(results[-1].get('summary'), str))
        self.assertTrue(isinstance(results[-1].get('description'), str))
        self.assertTrue(isinstance(results[-1].get('status'), str))
        self.assertTrue(isinstance(results[-1].get('count'), int))
        self.assertTrue(isinstance(results[-1].get('creation'), float))
        self.assertTrue(isinstance(results[-1].get('modification'), int))
        self.assertTrue(results[1].get('status') == AlertModel.AlertStatus.FIRING.value)
        self.assertTrue(results[1].get('count') == 2)

        response = self.client.get(query_api, data={'status': AlertModel.AlertStatus.RESOLVED.value})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["results"], [])

        # 更新end
        AlertModel.objects.all().update(end=123)

        response = self.client.post(receiver_url, data={})
        self.assertKeysIn(['status'], response.data)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(query_api)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)
        results = response.data['results']
        self.assertTrue(isinstance(results[-1].get('id'), str))
        self.assertTrue(isinstance(results[-1].get('start'), int))
        self.assertTrue(isinstance(results[-1].get('end'), int))
        self.assertTrue(isinstance(results[-1].get('alertname'), str))
        self.assertTrue(isinstance(results[-1].get('alert_type'), str))
        self.assertTrue(isinstance(results[-1].get('timestamp'), int))
        self.assertTrue(isinstance(results[-1].get('startsAt'), str))
        self.assertTrue(isinstance(results[-1].get('monitor_cluster'), str))
        self.assertTrue(isinstance(results[-1].get('fingerprint'), str))
        self.assertTrue(isinstance(results[-1].get('name'), str))
        self.assertTrue(isinstance(results[-1].get('type'), str))
        self.assertTrue(isinstance(results[-1].get('instance'), str))
        self.assertTrue(isinstance(results[-1].get('port'), str))
        self.assertTrue(isinstance(results[-1].get('cluster'), str))
        self.assertTrue(isinstance(results[-1].get('severity'), str))
        self.assertTrue(isinstance(results[-1].get('summary'), str))
        self.assertTrue(isinstance(results[-1].get('description'), str))
        self.assertTrue(isinstance(results[-1].get('status'), str))
        self.assertTrue(isinstance(results[-1].get('count'), int))
        self.assertTrue(isinstance(results[-1].get('creation'), float))
        self.assertTrue(isinstance(results[-1].get('modification'), int))
        self.assertTrue(results[1].get('status') == AlertModel.AlertStatus.RESOLVED.value)
        self.assertTrue(results[1].get('count') == 2)

        response = self.client.get(query_api, data={'status': AlertModel.AlertStatus.FIRING.value})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["results"], [])

        response = self.client.get(query_api, data={'status': AlertModel.AlertStatus.RESOLVED.value})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)

        response = self.client.get(query_api,
                                   data={'status': AlertModel.AlertStatus.RESOLVED.value, 'cluster': "aiops_metric"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)

        response = self.client.get(query_api,
                                   data={'status': AlertModel.AlertStatus.RESOLVED.value, 'cluster': "aiops_log"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)

        response = self.client.get(query_api,
                                   data={'status': AlertModel.AlertStatus.RESOLVED.value, 'name': "error log"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)

        response = self.client.get(query_api,
                                   data={'status': AlertModel.AlertStatus.RESOLVED.value, 'instance': "192.168.0.2"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)

        response = self.client.get(query_api,
                                   data={'status': AlertModel.AlertStatus.RESOLVED.value, 'type': "metric"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "previous", "next", "results"], response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["next"], None)

        choice_api = reverse('alert-api:alert-choice')
        response = self.client.get(choice_api)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', "cluster"], response.data)
        name = response.data['name']
        cluster = response.data['cluster']
        self.assertKeysIn(['error log', 'high cpu', 'high memory'], name)
        self.assertKeysIn(['aiops_log', 'aiops_metric'], cluster)
