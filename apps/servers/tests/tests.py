from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, get_or_create_service, MyAPITestCase


class ImageTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_service()

    def test_list_image(self):
        url = reverse('servers-api:images-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url += f'?service_id={self.service.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertKeysIn(["id", "name", "system", "system_type",
                           "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb", "min_ram_mb"
                           ], response.data[0])

        # image detail
        image_id = response.data[0]['id']
        url = reverse('servers-api:images-detail', kwargs={'id': image_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url = reverse('servers-api:images-detail', kwargs={'id': image_id})
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "name", "system_type", "release", "version", "architecture",
                           "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb", "min_ram_mb"
                           ], response.data)

    def test_list_image_paginate(self):
        url = reverse('servers-api:images-paginate-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "count", "page_num", "page_size", "results"
        ], response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertKeysIn([
            "id", "name", "release", "version", "architecture", "system_type",
            "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb",
            "min_ram_mb"
        ], response.data['results'][0])

        default_get_length = len(response.data['results'])

        # query "page_size"
        page_size = max(default_get_length - 1, 1)
        url = reverse('servers-api:images-paginate-list')
        query = parse.urlencode(query={
            'service_id': self.service.id, 'page_num': 1,
            'page_size': page_size
        })
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "count", "page_num", "page_size", "results"
        ], response.data)
        self.assertIsInstance(response.data['results'], list)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertKeysIn([
            "id", "name", "release", "version", "architecture", "system_type",
            "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb",
            "min_ram_mb"
        ], response.data['results'][0])

        # image detail
        image_id = response.data['results'][0]['id']
        url = reverse('servers-api:images-detail', kwargs={'id': image_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        url = reverse('servers-api:images-detail', kwargs={'id': image_id})
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            "id", "name", "release", "version", "architecture", "system_type",
            "creation_time", "desc", "default_user", "default_password", "min_sys_disk_gb",
            "min_ram_mb"
        ], response.data)


class NetworkTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_service()

    def test_list_network(self):
        base_url = reverse('servers-api:networks-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

        query = parse.urlencode({"azone_id": ''})
        url = f'{base_url}?{query}'
        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        url = f'{base_url}?service_id={self.service.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        if response.data:
            self.assertKeysIn(["id", "name", "public", "segment"], response.data[0])

            network_id = response.data[0]['id']
            url = reverse('servers-api:networks-detail', kwargs={'network_id': network_id})
            response = self.client.get(url)
            self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

            url += f'?service_id={self.service.id}'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertKeysIn(["id", "name", "public", "segment"], response.data)
        else:
            network_id = '1'        # 不确定是否存在
            url = reverse('servers-api:networks-detail', kwargs={'network_id': network_id})
            response = self.client.get(url)
            self.assertErrorResponse(status_code=400, code='NoFoundArgument', response=response)

            url += f'?service_id={self.service.id}'
            response = self.client.get(url)
            if response.status_code == 200:
                self.assertKeysIn(["id", "name", "public", "segment"], response.data)
            else:
                self.assertEqual(response.status_code, 500)


class AvailabilityZoneTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_service()

    def test_list_azones(self):
        url = reverse('servers-api:availability-zone-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 400)

        query = parse.urlencode(query={'service_id': self.service.id})
        url = f'{url}?{query}'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        zones = response.data['zones']
        if zones:
            self.assertKeysIn(keys=['id', 'name', 'available'], container=zones[0])
