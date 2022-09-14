from django.utils.translation import gettext as _
from django.utils import timezone

from core import errors
from storage.models import Bucket


class BucketManager:
    @staticmethod
    def get_bucket_queryset():
        return Bucket.objects.all()

    @staticmethod
    def get_bucket_by_id(_id: str):
        """
        :return: None or ObjectsService()
        """
        return Bucket.objects.filter(id=_id).first()

    @staticmethod
    def get_bucket(service_id: str, bucket_name: str):
        """
        :raises: BucketNotExist
        """
        bucket = Bucket.objects.select_related('service').filter(service_id=service_id, name=bucket_name).first()
        if not bucket:
            raise errors.BucketNotExist(_('存储桶不存在'))

        return bucket

    @staticmethod
    def create_bucket(bucket_name, bucket_id: str, user_id: str, service_id: str) -> Bucket:
        """
        :param bucket_name: 桶名称
        :param bucket_id: 对象存储服务单元中bucket id
        :param user_id: 桶拥有者id
        :param service_id: 桶所在服务单元id
        """
        bucket = Bucket(
            name=bucket_name, bucket_id=bucket_id, user_id=user_id,
            service_id=service_id, creation_time=timezone.now()
        )
        bucket.save(force_insert=True)
        return bucket
