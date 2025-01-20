from datetime import timedelta
from urllib import parse

from django.shortcuts import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITestCase
from apps.app_global.models import Announcement


class AnnounceTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_list(self):
        user1 = get_or_create_user(username='lisi@cnic.cn')

        anno1 = Announcement(
            name='标题1', name_en='title1', status=Announcement.Status.DRAFT.value,
            content='内容1 content1', expire_time=None, publisher=user1
        )
        anno1.save(force_insert=True)
        anno2 = Announcement(
            name='标题2', name_en='title2', status=Announcement.Status.PUBLISH.value,
            content='内容2 content2', expire_time=None, publisher=user1
        )
        anno2.save(force_insert=True)
        anno3 = Announcement(
            name='标题3', name_en='title3', status=Announcement.Status.PUBLISH.value,
            content='内容3 content3', content_en='英文3 content3', expire_time=dj_timezone.now(), publisher=user1
        )
        anno3.save(force_insert=True)
        anno4 = Announcement(
            name='标题4', name_en='title4', status=Announcement.Status.PUBLISH.value,
            content='内容4 content4', expire_time=dj_timezone.now() + timedelta(minutes=10), publisher=user1
        )
        anno4.save(force_insert=True)
        anno5 = Announcement(
            name='标题5', name_en='title5', status=Announcement.Status.REVOKED.value,
            content='内容5 content5', content_en='英文5 content5',
            expire_time=dj_timezone.now() + timedelta(days=1), publisher=user1
        )
        anno5.save(force_insert=True)

        base_url = reverse('app-global-api:announcement-list')

        # 未认证
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 1)
        self.assertEqual(r.data['page_size'], 100)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], anno4.id)
        self.assertEqual(r.data['results'][1]['id'], anno2.id)
        self.assertKeysIn(['id', 'name', 'name_en', 'status', 'content', 'creation_time', 'update_time',
                           'expire_time', 'publisher', 'content_en'], r.data['results'][0])

        # page
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['page_num'], 2)
        self.assertEqual(r.data['page_size'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], anno2.id)
