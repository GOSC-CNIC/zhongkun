from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from servers.models import Flavor, Server
from service.managers import UserQuotaManager
from utils.test import get_or_create_user, get_or_create_service


def set_auth_header(test_case: APITestCase):
    user = get_or_create_user()
    token = AccessToken.for_user(user)
    test_case.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
    test_case.user = user


class FlavorTests(APITestCase):
    def setUp(self):
        set_auth_header(self)

    def test_get_flavor(self):
        f = Flavor(vcpus=1, ram=1024, enable=True)
        f.save()
        url = reverse('api:flavor-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'flavors': [{
            'id': f.id, 'vcpus': f.vcpus, 'ram': 1024
        }]})


class UserQuotaTests(APITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def assertKeysIn(self, keys: list, container):
        for k in keys:
            self.assertIn(k, container)

    def test_get_quota(self):
        mgr = UserQuotaManager()
        old_quota = mgr.get_base_quota_queryset(user=self.user).first()
        if not old_quota:
            mgr._create_quota(user=self.user, service=self.service)

        url = reverse('api:user-quota-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results', "next", "previous"], response.data)
        self.assertKeysIn(["id", "tag", "user", "service", "private_ip_total",
                           "private_ip_used", "public_ip_total", "public_ip_used",
                           "vcpu_total", "vcpu_used", "ram_total", "ram_used",
                           "disk_size_total", "disk_size_used", "expiration_time",
                           "deleted", "display"], response.data['results'][0])


class ServersTests(APITestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        server = Server(service=self.service,
                        instance_id='test',
                        remarks='',
                        user=self.user,
                        vcpus=2,
                        ram=1024,
                        task_status=Server.TASK_IN_CREATING,
                        user_quota=None,
                        public_ip=False)
        server.save()
        self.server = server

    def test_server_remark(self):
        url = reverse('api:servers-server-remark', kwargs={'id': self.server.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 400)

        url = reverse('api:servers-server-remark', kwargs={'id': '00'})
        url += f'?remark=ss'
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 404)

        remark = 'test-remarks'
        url = reverse('api:servers-server-remark', kwargs={'id': self.server.id})
        url += f'?remark={remark}'
        response = self.client.patch(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.server.refresh_from_db()
        self.assertEqual(remark, self.server.remarks)



