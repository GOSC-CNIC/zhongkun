from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from utils.model import PayType, OwnerType
from apps.servers.models import Disk
from apps.servers.tests.test_disk import create_disk_metadata
from utils.test import get_or_create_user, MyAPITestCase
from apps.vo.models import VirtualOrganization, VoMember
from apps.app_wallet.managers.payment import PaymentManager
from apps.order.managers import OrderManager
from apps.order.models import Order, ResourceType
from apps.order.managers.instance_configs import ServerConfig


class VoTests(MyAPITestCase):
    def setUp(self):
        user = get_or_create_user(password='password')
        self.client.force_login(user=user)
        self.user = user
        self.user2_username = 'user2'
        self.user2_password = 'user2password'
        self.user2 = get_or_create_user(username=self.user2_username, password=self.user2_password)

    @staticmethod
    def create_vo_response(client, name, company, description):
        url = reverse('vo-api:vo-list')
        data = {
            'name': name,
            'company': company,
            'description': description
        }
        return client.post(url, data=data)

    @staticmethod
    def update_vo_response(client, vo_id: str, data):
        url = reverse('vo-api:vo-detail', kwargs={'id': vo_id})
        return client.patch(url, data=data)

    @staticmethod
    def delete_vo_response(client, vo_id: str):
        url = reverse('vo-api:vo-detail', kwargs={'id': vo_id})
        return client.delete(url)

    @staticmethod
    def list_response(client, queries: dict):
        url = reverse('vo-api:vo-list')
        if queries:
            query = parse.urlencode(queries, doseq=True)
            url = f'{url}?{query}'

        return client.get(url)

    @staticmethod
    def add_members_response(client, vo_id: str, usernames: list):
        url = reverse('vo-api:vo-vo-add-members', kwargs={'id': vo_id})
        return client.post(url, data={'usernames': usernames})

    @staticmethod
    def list_vo_members_response(client, vo_id: str):
        url = reverse('vo-api:vo-vo-list-members', kwargs={'id': vo_id})
        return client.get(url)

    @staticmethod
    def remove_members_response(client, vo_id: str, usernames: list):
        url = reverse('vo-api:vo-vo-remove-members', kwargs={'id': vo_id})
        return client.post(url, data={'usernames': usernames})

    @staticmethod
    def change_member_role_response(client, member_id: str, role: str):
        url = reverse('vo-api:vo-vo-members-role', kwargs={'member_id': member_id, 'role': role})
        return client.post(url)

    def test_create_update_delete(self):
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['id', 'name', 'company', 'description', 'creation_time',
                                'owner', 'status'], container=response.data)
        sub = {'status': 'active'}
        sub.update(data)
        self.assert_is_subdict_of(sub=sub, d=response.data)
        self.assert_is_subdict_of(sub={'id': self.user.id, 'username': self.user.username},
                                  d=response.data['owner'])
        vo_id = response.data['id']

        # update
        update_data = {
            'name': 'vo1', 'company': '网络中心', 'description': '测试666'
        }
        response = self.update_vo_response(client=self.client, vo_id=vo_id, data=update_data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=['id', 'name', 'company', 'description', 'creation_time',
                                'owner', 'status'], container=response.data)
        self.assert_is_subdict_of(sub=update_data, d=response.data)

        vo = VirtualOrganization.objects.select_related('owner').filter(id=vo_id).first()
        self.assertEqual(vo.deleted, False)
        self.assertEqual(vo.name, update_data['name'])
        self.assertEqual(vo.company, update_data['company'])
        self.assertEqual(vo.description, update_data['description'])

        # delete
        vo_account = PaymentManager.get_vo_point_account(vo_id=vo_id)
        vo_account.balance = Decimal('-1')
        vo_account.save(update_fields=['balance'])
        response = self.delete_vo_response(client=self.client, vo_id=vo_id)
        self.assertErrorResponse(status_code=409, code='BalanceArrearage', response=response)

        vo_account.balance = Decimal('0')
        vo_account.save(update_fields=['balance'])
        response = self.delete_vo_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 204)
        vo.refresh_from_db()
        self.assertEqual(vo.deleted, True)

    def test_list(self):
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)

        # list
        response = self.list_response(client=self.client, queries={})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(keys=['id', 'name', 'company', 'description', 'creation_time',
                                'owner', 'status'], container=response.data['results'][0])

        # list as member
        response = self.list_response(client=self.client, queries={'member': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # list as owner
        response = self.list_response(client=self.client, queries={'owner': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

        # list as owner and member
        response = self.list_response(client=self.client, queries={'owner': '', 'member': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

        # query "name"
        response = self.list_response(client=self.client, queries={'name': 'ss'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        response = self.list_response(client=self.client, queries={'name': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

        # --------admin test----------
        self.client.logout()
        self.client.force_login(self.user2)
        response = self.list_response(client=self.client, queries={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        response = self.list_response(client=self.client, queries={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user2.set_federal_admin()
        response = self.list_response(client=self.client, queries={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_owner_members_action(self):
        """
        组长管理组测试
        """
        usernames = ['user-test1', 'user-test2']
        get_or_create_user(username=usernames[0], password='password')
        get_or_create_user(username=usernames[1], password='password')

        owner = self.user
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)
        vo_id = response.data['id']

        # add members
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames + [owner.username])
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames + ['notfound'])
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['success', 'failed'], response.data)
        self.assertIsInstance(response.data['success'], list)
        self.assertEqual(len(response.data['success']), 2)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data['success'][0])
        self.assertIn(response.data['success'][0]['user']['username'], usernames)
        self.assertEqual(response.data['success'][0]['role'], VoMember.Role.MEMBER)
        self.assertEqual(response.data['success'][0]['inviter'], owner.username)

        self.assertIsInstance(response.data['failed'], list)
        self.assertEqual(len(response.data['failed']), 1)
        self.assertEqual(response.data['failed'][0]['username'], 'notfound')

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertIsInstance(response.data['members'], list)
        self.assertEqual(len(response.data['members']), 2)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data['members'][0])
        self.assertEqual(response.data['owner'], {'id': owner.id, 'username': owner.username})

        # remove members
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[0:1])
        self.assertEqual(response.status_code, 204)

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertEqual(len(response.data['members']), 1)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data['members'][0])
        self.assertEqual(response.data['members'][0]['user']['username'], usernames[1])
        self.assert_is_subdict_of(sub={'role': VoMember.Role.MEMBER, 'inviter': owner.username},
                                  d=response.data['members'][0])

    def test_role_members_actions(self):
        """
        组角色管理组测试
        """
        usernames = ['user-test1', 'user-test2']
        get_or_create_user(username=usernames[0], password='password')
        get_or_create_user(username=usernames[1], password='password')

        owner = self.user
        data = {
            'name': 'test vo',
            'company': 'cnic',
            'description': '测试'
        }
        response = self.create_vo_response(client=self.client, name=data['name'],
                                           company=data['company'], description=data['description'])
        self.assertEqual(response.status_code, 200)
        vo_id = response.data['id']

        # add member user2
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=[self.user2.username])
        self.assertEqual(response.status_code, 200)
        user2_member_id = response.data['success'][0]['id']

        # add member test1
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames[0:1])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['success']), 1)
        test1_member_id = response.data['success'][0]['id']

        # member role no permission add member
        # login user2
        self.client.logout()
        self.client.force_login(self.user2)
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames)
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')

        # user2 no permission set leader role
        response = self.change_member_role_response(client=self.client, member_id=user2_member_id,
                                                    role=VoMember.Role.LEADER)
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')
        # login owner
        self.client.logout()
        self.client.force_login(owner)
        # owner set user2 leader role
        response = self.change_member_role_response(client=self.client, member_id=user2_member_id,
                                                    role=VoMember.Role.LEADER)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'user', 'role', 'join_time', 'inviter'], response.data)
        self.assertEqual(response.data['role'], VoMember.Role.LEADER)

        # owner set test1 role leader
        response = self.change_member_role_response(client=self.client, member_id=test1_member_id,
                                                    role=VoMember.Role.LEADER)
        self.assertEqual(response.status_code, 200)

        # login leader user
        self.client.logout()
        self.client.force_login(self.user2)

        # leader role add member test2
        response = self.add_members_response(client=self.client, vo_id=vo_id,
                                             usernames=usernames[1:2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['success']), 1)
        self.assertEqual(len(response.data['failed']), 0)

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertEqual(len(response.data['members']), 3)
        member_usernames = usernames + [self.user2.username]
        for m in response.data['members']:
            un = m['user']['username']
            self.assertIn(un, member_usernames)
            member_usernames.remove(un)
        self.assertFalse(member_usernames)

        # leader role no permission remove leader role member test1
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[0:1])
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')

        # leader role remove member test2
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[1:2])
        self.assertEqual(response.status_code, 204)

        # owner remove leader role member test1
        # login owner
        self.client.logout()
        self.client.force_login(owner)
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=usernames[0:1])
        self.assertEqual(response.status_code, 204)

        # list members
        response = self.list_vo_members_response(client=self.client, vo_id=vo_id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['members', 'owner'], response.data)
        self.assertEqual(len(response.data['members']), 1)
        self.assertEqual(response.data['members'][0]['user']['username'], self.user2.username)

        # owner remove owner
        response = self.remove_members_response(client=self.client, vo_id=vo_id,
                                                usernames=[owner.username])
        self.assertErrorResponse(response=response, status_code=403, code='AccessDenied')

    def test_vo_statistic(self):
        vo1 = VirtualOrganization(
            name='test vo1', owner=self.user2
        )
        vo1.save(force_insert=True)

        url = reverse('vo-api:vo-vo-statistic', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        url = reverse('vo-api:vo-vo-statistic', kwargs={'id': vo1.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        member = VoMember(user_id=self.user.id, vo_id=vo1.id, role=VoMember.Role.LEADER.value)
        member.save(force_insert=True)

        url = reverse('vo-api:vo-vo-statistic', kwargs={'id': vo1.id})
        r = self.client.get(url)
        self.assertKeysIn(keys=[
            'vo', 'member_count', 'server_count', 'order_count', 'coupon_count', 'balance'], container=r.data)
        self.assertEqual(r.data['vo']['id'], vo1.id)
        self.assertEqual(r.data['member_count'], 2)
        self.assertEqual(r.data['server_count'], 0)
        self.assertEqual(r.data['order_count'], 0)
        self.assertEqual(r.data['coupon_count'], 0)
        self.assertEqual(r.data['balance'], '0.00')

        vo1_account = PaymentManager.get_vo_point_account(vo_id=vo1.id)
        vo1_account.balance = Decimal('-1.23')
        vo1_account.save(update_fields=['balance'])

        order_instance_config = ServerConfig(
            vm_cpu=2, vm_ram=2048, systemdisk_size=100, public_ip=True,
            image_id='image_id', image_name='', network_id='network_id', network_name='',
            azone_id='azone_id', azone_name='azone_name', flavor_id=''
        )
        OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id='test',
            service_id='test',
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.POSTPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )

        OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id='test',
            service_id='test',
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.POSTPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=vo1.id, vo_name=vo1.name,
            owner_type=OwnerType.VO.value
        )

        create_disk_metadata(
            service_id=None, azone_id='2', disk_size=88, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )
        create_disk_metadata(
            service_id=None, azone_id='1', disk_size=886, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value, user_id=self.user2.id, vo_id=vo1.id,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )

        url = reverse('vo-api:vo-vo-statistic', kwargs={'id': vo1.id})
        r = self.client.get(url)
        self.assertKeysIn(keys=[
            'vo', 'member_count', 'server_count', 'order_count', 'coupon_count', 'balance',
            'my_role', 'disk_count'
        ], container=r.data)
        self.assertEqual(r.data['vo']['id'], vo1.id)
        self.assertEqual(r.data['member_count'], 2)
        self.assertEqual(r.data['server_count'], 0)
        self.assertEqual(r.data['order_count'], 1)
        self.assertEqual(r.data['coupon_count'], 0)
        self.assertEqual(r.data['balance'], '-1.23')
        self.assertEqual(r.data['my_role'], VoMember.Role.LEADER.value)
        self.assertEqual(r.data['disk_count'], 1)

    def test_devolve_vo_owner(self):
        user3 = get_or_create_user(username='zhangsan@cnic.cn')
        vo1 = VirtualOrganization(name='vo1', owner=self.user)
        vo1.save(force_insert=True)
        vo1_member1 = VoMember(vo=vo1, user=self.user2)
        vo1_member1.save(force_insert=True)
        vo1_member2 = VoMember(vo=vo1, user=user3)
        vo1_member2.save(force_insert=True)

        vo2 = VirtualOrganization(name='vo2', owner=self.user2)
        vo2.save(force_insert=True)
        vo2_member1 = VoMember(vo=vo2, user=user3)
        vo2_member1.save(force_insert=True)

        self.client.logout()
        base_url = reverse('vo-api:vo-devolve', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'member_id': vo1_member1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='VoNotExist', response=response)

        query = parse.urlencode(query={'member_id': vo1_member1.id, 'username': user3.username})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # user, vo1 member_id
        base_url = reverse('vo-api:vo-devolve', kwargs={'id': vo1.id})
        query = parse.urlencode(query={'member_id': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'member_id': vo2_member1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # vo1 owner user -> user2
        query = parse.urlencode(query={'member_id': vo1_member1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'company', 'description', 'creation_time', 'owner', 'status'], container=response.data)
        self.assertEqual(response.data['owner']['username'], self.user2.username)

        vo1.refresh_from_db()
        self.assertEqual(vo1.owner_id, self.user2.id)
        self.assertEqual(vo1.owner.username, self.user2.username)
        self.assertEqual(VoMember.objects.filter(vo_id=vo1.id).count(), 2)
        member: VoMember = VoMember.objects.filter(vo_id=vo1.id, user__username=self.user.username).first()
        self.assertEqual(member.role, VoMember.Role.LEADER.value)
        member = VoMember.objects.filter(vo_id=vo1.id, user__username=self.user2.username).first()
        self.assertIsNone(member)

        query = parse.urlencode(query={'member_id': vo1_member2.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo2, username
        base_url = reverse('vo-api:vo-devolve', kwargs={'id': vo2.id})
        query = parse.urlencode(query={'username': self.user.username})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'username': user3.username})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(self.user2)

        # vo2 owner user2 -> user3
        query = parse.urlencode(query={'username': user3.username})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'name', 'company', 'description', 'creation_time', 'owner', 'status'], container=response.data)
        self.assertEqual(response.data['owner']['username'], user3.username)

        vo2.refresh_from_db()
        self.assertEqual(vo2.owner_id, user3.id)
        self.assertEqual(vo2.owner.username, user3.username)
        self.assertEqual(VoMember.objects.filter(vo_id=vo2.id).count(), 1)
        member: VoMember = VoMember.objects.filter(vo_id=vo2.id, user__username=self.user2.username).first()
        self.assertEqual(member.role, VoMember.Role.LEADER.value)
        member = VoMember.objects.filter(vo_id=vo2.id, user__username=user3.username).first()
        self.assertIsNone(member)
