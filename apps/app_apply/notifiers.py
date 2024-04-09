from core import taskqueue, site_configs_manager as site_configs
from apps.app_apply.models import CouponApply
from users import managers as user_manager
from users.models import Email


class CouponApplyEmailNotifier:
    @staticmethod
    def thread_send_email(subject: str, receivers: list, message: str):
        email = Email.send_email(
            subject=subject, receivers=receivers, message=message, save_db=True, tag=Email.Tag.COUPON.value)
        return email

    @staticmethod
    def website_url_join(sub_url: str):
        base = site_configs.website_url.rstrip('/')
        sub_url = sub_url.lstrip('/')
        return f'{base}/{sub_url}'

    @staticmethod
    def build_apply_message(apply: CouponApply):
        apply_msg = f'服务类型为 {apply.get_service_type_display()}，服务单元为 {apply.service_name}，' \
                     f'申请点数为 {apply.face_value}，申请人为 {apply.username}'
        if apply.is_owner_vo():
            apply_msg = f'{apply_msg}，为项目组“{apply.vo_name}”申请。'
        else:
            apply_msg = apply_msg + '，个人申请。'

        if apply.apply_desc:
            apply_msg += '\n申请描述：' + apply.apply_desc

        return apply_msg

    @staticmethod
    def new_apply_notice(apply: CouponApply):
        if apply.service_type in [CouponApply.ServiceType.SCAN.value, CouponApply.ServiceType.MONITOR_SITE.value]:
            user_qs = user_manager.filter_user_queryset(is_federal_admin=True)
            receivers = user_qs.values_list('username', flat=True)   # [u.username for u in user_qs]
        else:
            receivers = apply.odc.users.values_list('username', flat=True)

        if not receivers:
            return None

        subject = f'{apply.service_name}，{apply.get_service_type_display()} {apply.face_value}点券申请'
        if apply.is_owner_vo():
            subject += f'({apply.vo_name})'
        else:
            subject += f'({apply.username})'

        apply_message = CouponApplyEmailNotifier.build_apply_message(apply=apply)
        web_url = CouponApplyEmailNotifier.website_url_join(sub_url='/my/wallet/manage/application')

        message = f"""
您好：

用户 {apply.username} 提交了一个资源券申请。

{apply_message}


祝好
{site_configs.website_brand}({web_url})
        """

        future = taskqueue.submit_task(
            CouponApplyEmailNotifier.thread_send_email,
            kwargs={
                'subject': subject, 'receivers': receivers, 'message': message
            }
        )
        return future

    @staticmethod
    def new_status_notice(apply: CouponApply, receivers: list = None):
        if not receivers:
            receivers = [apply.username]

        subject = f'{apply.service_name}，{apply.get_service_type_display()}券申请'
        apply_message = CouponApplyEmailNotifier.build_apply_message(apply=apply)
        web_url = CouponApplyEmailNotifier.website_url_join(sub_url='my/wallet/voucher/application')
        if apply.status == CouponApply.Status.PASS.value:
            status_msg = '申请通过'
            subject += ' 通过'
        elif apply.status == CouponApply.Status.REJECT.value:
            status_msg = f'申请被拒绝，原因：{apply.reject_reason}'
            subject += ' 驳回'
        else:
            return None

        message = f"""
您好：

资源券申请有了新的动态:
  {status_msg}

申请信息：
  {apply_message}


祝好
{site_configs.website_brand}({web_url})
            """
        future = taskqueue.submit_task(
            CouponApplyEmailNotifier.thread_send_email,
            kwargs={
                'subject': subject, 'receivers': receivers, 'message': message
            }
        )
        return future
