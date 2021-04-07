from .models import ApplyQuota


class ApplyQuotaManager:
    @staticmethod
    def get_apply_queryset():
        return ApplyQuota.objects.filter(deleted=False).all()

    def get_user_apply_queryset(self, user):
        qs = self.get_apply_queryset()
        return qs.filter(user=user)

