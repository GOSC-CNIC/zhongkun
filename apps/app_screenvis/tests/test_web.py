from urllib import parse

from django.urls import reverse

from apps.app_screenvis.managers import WebQueryChoices
from apps.app_screenvis.permissions import ScreenAPIIPRestrictor
from apps.app_screenvis.models import WebsiteMonitorTask
from . import MyAPITestCase, config_website_query_endpoint_url


class WebsiteTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def query_response(self, query_tag: str):
        querys = {}
        if query_tag:
            querys['query'] = query_tag

        url = reverse('screenvis-api:website-query')
        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def query_ok_test(self, query_tag: str):
        response = self.query_response(query_tag=query_tag)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertKeysIn([query_tag, "tasks"], response.data)
        tag_data = response.data[query_tag]
        if tag_data:
            data_item = tag_data[0]
            self.assertKeysIn(["metric", "value"], data_item)
            if data_item["value"] is not None:
                self.assertIsInstance(data_item["value"], list)
                self.assertEqual(len(data_item["value"]), 2)

        return response

    def test_query(self):
        config_website_query_endpoint_url()

        task = WebsiteMonitorTask(
            name='test website',
            url='https://test.com',
            is_tamper_resistant=True
        )
        task.reset_url_hash()
        task.save(force_insert=True)

        response = self.query_response(query_tag=WebQueryChoices.HTTP_STATUS_CODE.value)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ScreenAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        ScreenAPIIPRestrictor.clear_cache()

        response = self.query_response(query_tag='xxx')
        self.assertEqual(response.status_code, 400)

        r = self.query_ok_test(query_tag=WebQueryChoices.HTTP_STATUS_CODE.value)
        self.assertTrue(len(r.data[WebQueryChoices.HTTP_STATUS_CODE.value]) >= 1)
        r = self.query_ok_test(query_tag=WebQueryChoices.HTTP_DURATION_SECONDS.value)
        self.assertTrue(len(r.data[WebQueryChoices.HTTP_DURATION_SECONDS.value]) >= 5)
        r = self.query_ok_test(query_tag=WebQueryChoices.DURATION_SECONDS.value)
        self.assertTrue(len(r.data[WebQueryChoices.DURATION_SECONDS.value]) >= 1)

        # all together
        response = self.query_response(query_tag=WebQueryChoices.ALL_TOGETHER.value)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)

        tags = WebQueryChoices.values
        tags.remove(WebQueryChoices.ALL_TOGETHER.value)
        self.assertKeysIn(['id', 'name', 'url', 'url_hash', 'is_tamper_resistant'], response.data['tasks'][0])
        for tag in tags:
            self.assertIn(tag, response.data)
            tag_data = response.data[tag]
            self.assertIsInstance(tag_data, list)
            if tag_data:
                data_item = tag_data[0]
                self.assertKeysIn(["metric", "value"], data_item)
                if data_item["value"] is not None:
                    self.assertIsInstance(data_item["value"], list)
                    self.assertEqual(len(data_item["value"]), 2)
