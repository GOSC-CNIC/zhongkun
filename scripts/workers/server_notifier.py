from datetime import timedelta, datetime

from django.utils import timezone
from django.db.models import F
from django.template.loader import get_template
from django.conf import settings
from django.core.mail import send_mail

from servers.models import Server
from users.models import Email, UserProfile
from vo.models import VirtualOrganization, VoMember
from utils.model import PayType
from . import config_logger


class ServerQuerier:
    def __init__(self, filter_out_notified: bool):
        """
        filter_out_notified: True: 给定期限之后已发过通知的过滤掉不返回； False: 不考虑是否发过通知，返回所有满足指定期限的server
        """
        if filter_out_notified is not None:
            self.is_filter_out_notified = filter_out_notified

    def get_expired_servers_queryset(
            self, after_days: int, creation_time_gt: datetime = None, filter_out_notified: bool = None
    ):
        """
        查询指定天数后即将过期的server

        :param after_days: 指定天数后过期， 0 当前已过期
        :param creation_time_gt: 创建时间大于此时间的server
        :param filter_out_notified: 默认None: 按 IS_FILTER_OUT_NOTIFIED
                                    True: 给定期限之后已发过通知的过滤掉不返回；
                                    False: 不考虑是否发过通知，返回所有满足指定期限的server
        """
        nt = timezone.now()
        will_expiration_time = nt + timedelta(days=after_days)
        lookups = {}
        if creation_time_gt:
            lookups['creation_time__gt'] = creation_time_gt

        qs = Server.objects.select_related('user', 'vo').filter(
            expiration_time__lt=will_expiration_time, pay_type=PayType.PREPAID.value,
            **lookups
        ).order_by('creation_time')

        if filter_out_notified is None:
            filter_out_notified = self.is_filter_out_notified
        if filter_out_notified:
            qs = qs.exclude(  # == email_lasttime (is null | < server.expiration_time)
                email_lasttime__gte=F('expiration_time')
            )

        return qs

    def get_personal_expired_server_queryset(
            self, after_days: int, creation_time_gt: datetime = None, user_id: str = None
    ):
        """
        查询所有用户或指定用户的指定天数后即将过期server

        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        :param user_id: 查询指定用户的；None（查所有用户）
        """
        qs = self.get_expired_servers_queryset(
            after_days=after_days, creation_time_gt=creation_time_gt
        )

        lookups = {'classification': Server.Classification.PERSONAL.value}
        if user_id:
            lookups['user_id'] = user_id

        qs = qs.filter(**lookups)
        return qs

    def get_vo_expired_server_queryset(
            self, after_days: int, creation_time_gt: datetime = None, vo_ids: list = None,
            filter_out_notified: bool = None
    ):
        """
        查询所有vo或指定vo的指定天数后即将过期server

        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        :param vo_ids: 查询指定vo的；None（查所有vo）
        :param filter_out_notified: 默认None: 按 IS_FILTER_OUT_NOTIFIED
                                    True: 给定期限之后已发过通知的过滤掉不返回；
                                    False: 不考虑是否发过通知，返回所有满足指定期限的server
        """
        qs = self.get_expired_servers_queryset(
            after_days=after_days, creation_time_gt=creation_time_gt,
            filter_out_notified=filter_out_notified
        )

        lookups = {'classification': Server.Classification.VO.value}
        if vo_ids is not None:
            if len(vo_ids) == 1:
                lookups['vo_id'] = vo_ids[0]
            else:
                lookups['vo_id__in'] = vo_ids

        qs = qs.filter(**lookups)
        return qs

    def get_expired_servers(self, after_days: int, creation_time_gt: datetime = None, limit: int = 100):
        """
        查询指定天数后即将过期的server

        :param after_days: 指定天数后过期， 0 当前已过期
        :param creation_time_gt: 创建时间大于此时间的server
        :param limit: 指定返回server数量
        """
        qs = self.get_expired_servers_queryset(after_days=after_days, creation_time_gt=creation_time_gt)
        return qs[:limit]

    def get_user_expired_servers(
            self, user_id: str, after_days: int,
            creation_time_gt: datetime = None
    ):
        """
        查询用户的指定天数后即将过期server

        :param user_id:
        :param after_days: 指定天数后过期
        :param creation_time_gt: 创建时间大于此时间的券
        """
        qs = self.get_personal_expired_server_queryset(
            after_days=after_days, creation_time_gt=creation_time_gt, user_id=user_id
        )

        return list(qs)

    def get_personal_expired_server_users(self, after_days: int) -> dict:
        """
        属于个人的过期的server关联的所有用户
        :return: [
            {'user_id': 'username'}
        ]
        """
        qs = self.get_personal_expired_server_queryset(
            after_days=after_days, creation_time_gt=None, user_id=None
        )
        users = qs.values('user_id', 'user__username')
        return {u['user_id']: u['user__username'] for u in users}

    def get_personal_vo_expired_server_users(self, after_days: int) -> dict:
        """
        所有的过期的server关联的所有个人用户和vo组的用户
        :return: {'user_id': 'username'}
        """
        qs = self.get_personal_expired_server_queryset(
            after_days=after_days, creation_time_gt=None, user_id=None
        )
        personals = qs.values('user_id', 'user__username')
        qs = self.get_vo_expired_server_queryset(after_days=after_days, vo_ids=None)
        vo_ids = qs.values_list('vo_id', flat=True)
        vo_ids = set(vo_ids)
        vo_users = VoMember.objects.filter(vo_id__in=vo_ids).values('user_id', 'user__username')
        vo_owners = VirtualOrganization.objects.filter(
            id__in=vo_ids, deleted=False).values('owner_id', 'owner__username')
        user_map = {}
        for u in personals:
            user_map[u['user_id']] = u['user__username']

        for u in vo_users:
            user_map[u['user_id']] = u['user__username']

        for u in vo_owners:
            user_map[u['owner_id']] = u['owner__username']

        return user_map

    def get_vo_expired_server_vos(self, after_days: int):
        """
        属于vo的过期的server关联的所有vo
        :return: [
            {'vo_id': 'xx', 'vo_name': 'xx'}
        ]
        """
        qs = self.get_vo_expired_server_queryset(
            after_days=after_days, creation_time_gt=None
        )
        return qs.values('vo_id', 'vo__name')

    @staticmethod
    def get_users_of_vos(vo_ids: list):
        """
        指定所有vo的用户
        :return: [{user_id: username}]
        """
        owners = VirtualOrganization.objects.select_related(
            'owner').filter(id__in=vo_ids, deleted=False).values('owner_id', 'owner__username')
        users = VoMember.objects.select_related(
            'user').filter(vo_id__in=vo_ids).values('user_id', 'user__username')

        user_dict = {}
        for u in owners:
            user_dict[u['owner_id']] = u['owner__username']

        for u in users:
            user_dict[u['user_id']] = u['user__username']

        return user_dict

    @staticmethod
    def set_servers_notice_time(
            server_ids: list, expire_notice_time: datetime
    ):
        r = Server.objects.filter(id__in=server_ids).update(email_lasttime=expire_notice_time)
        return r

    def set_vo_servers_notice_time(
            self, after_days: int, expire_notice_time: datetime
    ):
        qs = self.get_vo_expired_server_queryset(after_days=after_days, filter_out_notified=True)
        r = qs.update(email_lasttime=expire_notice_time)
        return r

    def is_need_expired_notice(self, server: Server, after_days: int):
        """
        param after_days: >= 0, 几天后会到期
        """
        nt = timezone.now()
        will_expiration_time = nt + timedelta(days=after_days)

        if server.expiration_time is None:
            return False

        # server 已过期
        if server.expiration_time <= nt:
            if self.is_filter_out_notified is False:    # 不排除通知过的
                return True

            if server.email_lasttime is None:   # 未通知过
                return True
            elif server.email_lasttime <= server.expiration_time:   # 过期后未通知
                return True
            else:
                return False

        # server 未过期
        if server.expiration_time < will_expiration_time:   # 指定天数后即将过期
            if server.email_lasttime is None:  # 未通知过
                return True
            elif server.expiration_time - server.email_lasttime < timedelta(days=after_days):  # 距过期after_days之内通知过
                if self.is_filter_out_notified is False:  # 不排除通知过的
                    return True

                return False
            else:
                return True
        else:
            return False


class ServersSorter:
    def __init__(self, servers: list, after_days: int, filter_out_notified: bool):
        """
        param after_days: >= 0, 几天后会到期
        """
        self.__servers = servers
        self.after_days = after_days
        self.expired_servers = self.sort_servers(
            servers, after_days=after_days, filter_out_notified=filter_out_notified)

    def notice_servers(self):
        return self.expired_servers

    def expire_server_ids(self):
        return [s.id for s in self.expired_servers]

    @staticmethod
    def sort_servers(servers, after_days: int, filter_out_notified: bool):
        sq = ServerQuerier(filter_out_notified=filter_out_notified)
        expire_servers = []
        for sv in servers:
            is_exp = sq.is_need_expired_notice(server=sv, after_days=after_days)
            if is_exp:
                expire_servers.append(sv)

        return expire_servers


class BaseNotifier:
    def __init__(self, filter_out_notified: bool, log_stdout: bool = False):
        self.logger = config_logger(name='server-logger', filename="server_notice.log", stdout=log_stdout)
        self.querier = ServerQuerier(filter_out_notified=filter_out_notified)

    def do_email_notice(self, subject: str, html_message: str, username: str):
        html_message = self.html_minify(html_message)
        # 先保存邮件记录
        try:
            email = Email(
                subject=subject, receiver=username, message=html_message,
                sender=settings.EMAIL_HOST_USER,
                email_host=settings.EMAIL_HOST,
                tag=Email.Tag.RES_EXP.value, is_html=True,
                status=Email.Status.WAIT.value, status_desc='', success_time=None
            )
            email.save(force_insert=True)
        except Exception as exc:
            self.logger.warning(
                f"User {username} servers expired email save to db failed {str(exc)}.")
            return False

        try:
            ok = send_mail(
                subject=subject,
                message='',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[username],
                html_message=html_message,
                fail_silently=False,
            )
            if ok == 0:
                raise Exception('failed')
        except Exception as exc:
            email.set_send_failed(desc=str(exc), save_db=True)
            return False

        try:
            email.set_send_success(desc='', save_db=True)
        except Exception as exc:
            pass

        return True

    @staticmethod
    def html_minify(_html: str):
        """
        去除html空行或每行前面的空格
        """
        lines = _html.split('\n')
        new_lines = []
        for line in lines:
            line = line.lstrip(' ')
            if line:
                new_lines.append(line)

        return '\n'.join(new_lines)


class PersonalServersNotifier(BaseNotifier):
    def __init__(self, filter_out_notified: bool, log_stdout: bool = False):
        super().__init__(log_stdout=log_stdout, filter_out_notified=filter_out_notified)
        self.expired_template = get_template('server_expired.html')

    def run(self):
        self.loop_already_expired_personal()

    def loop_already_expired_personal(self):
        """
        只查询个人已经过期的云主机（不含vo组的）进行过期通知
        """
        self.logger.warning('开始个人云主机过期通知。')
        after_days = 0
        users = self.querier.get_personal_expired_server_users(
            after_days=after_days
        )
        for user_id, username in users.items():
            try:
                self.notice_personal_expired_servers(user_id=user_id, username=username)
            except Exception as exc:
                msg = f'个人云主机过期通知错误，{str(exc)}'
                self.logger.warning(msg)

        self.logger.warning('结束云主机过期通知。')

    def get_personal_expired_servers_context(self, user_id: str, username: str, after_days: int = 0):
        servers = self.querier.get_personal_expired_server_queryset(
            after_days=after_days, user_id=user_id
        )
        if len(servers) <= 0:
            notice_servers = []
        else:
            sorter = ServersSorter(
                servers=servers, after_days=after_days, filter_out_notified=self.querier.is_filter_out_notified)
            notice_servers = sorter.notice_servers()

        return {
            'username': username,
            'user_servers': notice_servers,
            'now_time': timezone.now()
        }

    def notice_personal_expired_servers(self, user_id: str, username: str):
        context = self.get_personal_expired_servers_context(user_id=user_id, username=username)
        if not context['user_servers']:
            return True

        server_ids = [s.id for s in context['user_servers']]
        html_message = self.expired_template.render(context, request=None)
        subject = '云服务器过期提醒（一体化云服务平台）'
        if self.do_email_notice(subject=subject, html_message=html_message, username=username):
            self.querier.set_servers_notice_time(server_ids=server_ids, expire_notice_time=timezone.now())
            return True

        return False


class ServerNotifier(BaseNotifier):
    def __init__(
            self, log_stdout: bool = False, is_update_server_email_time: bool = True,
            filter_out_notified: bool = True
    ):
        """
        is_update_server_email_time: True,邮件通知成功后，更新server邮件通知时间
        filter_out_notified: True: 给定期限之后已发过通知的过滤掉； False: 不考虑是否发过通知，所有满足指定期限的server
        """
        super().__init__(log_stdout=log_stdout, filter_out_notified=filter_out_notified)
        self.expired_template = get_template('server_expired.html')
        self.is_update_server_email_time = is_update_server_email_time

    def run(self, after_days: int = 0):
        """
        after_days: 多少天后过期的云主机
        """
        # ok_count, failed_count = self.loop_all_users(after_days=after_days)
        ok_count, failed_count = self.notice_only_need_users(after_days=after_days)
        print(f'OK email: {ok_count}, failed email: {failed_count}.')

        # 统一更新vo组的server邮件发送时间
        if self.is_update_server_email_time:
            self.set_vo_servers_email_lasttime(after_days=after_days, expire_notice_time=timezone.now())

    def notice_only_need_users(self, after_days: int):
        """
        通过过期的云主机获取所有需要通知的用户，再循环通知
        """
        ok_notice_user_count = 0
        failed_notice_user_count = 0
        user_map = self.querier.get_personal_vo_expired_server_users(after_days=after_days)
        for user_id, username in user_map.items():
            try:
                print(username)
                try:
                    ok = self.notice_personal_vo_expired_servers(
                        user_id=user_id, username=username, after_days=after_days
                    )
                except Exception as exc:
                    self.logger.error(f'loop user({username}) error, {str(exc)}')
                    failed_notice_user_count += 1
                    continue

                if ok is True:
                    ok_notice_user_count += 1
                elif ok is False:
                    failed_notice_user_count += 1
            except Exception as exc:
                failed_notice_user_count += 1
                self.logger.error(f'error, {str(exc)}')

        return ok_notice_user_count, failed_notice_user_count

    def loop_all_users(self, after_days: int, limit: int = 100):
        """
        循环所有的用户，查询用户是否有过期的云主机，然后通知
        """
        self.logger.warning('Start loop user.')
        last_joined_time = None
        ok_notice_user_count = 0
        failed_notice_user_count = 0
        while True:
            try:
                users = self.get_users(limit=limit, time_joined_gt=last_joined_time)
                if len(users) <= 0:
                    break

                for user in users:
                    print(f'{user.username}')
                    try:
                        ok = self.notice_personal_vo_expired_servers(
                            user_id=user.id, username=user.username, after_days=after_days
                        )
                    except Exception as exc:
                        last_joined_time = user.date_joined
                        self.logger.error(f'loop user({user.username}) error, {str(exc)}')
                        failed_notice_user_count += 1
                        continue

                    last_joined_time = user.date_joined
                    if ok is True:
                        ok_notice_user_count += 1
                    elif ok is False:
                        failed_notice_user_count += 1
            except Exception as exc:
                self.logger.error(f'error, {str(exc)}')

        self.logger.warning('End loop user.')
        return ok_notice_user_count, failed_notice_user_count

    @staticmethod
    def get_users(limit: int, time_joined_gt=None):
        qs = UserProfile.objects.filter(
            is_active=True
        ).order_by('date_joined')

        if time_joined_gt:
            qs = qs.filter(date_joined__gt=time_joined_gt)

        return qs[0:limit]

    @staticmethod
    def get_vos_of_user(user_id: str):
        """
        :return: {
            'vo_id': {'vo': , 'own_role': 'xxx'}
        }
        """
        v_members = VoMember.objects.select_related('vo', 'vo__owner').filter(user_id=user_id).all()  # 在别人的vo组
        vos = VirtualOrganization.objects.select_related('owner').filter(owner_id=user_id, deleted=False)  # 自己的vo组
        vos_dict = {}
        for m in v_members:
            vo = m.vo
            if not vo:
                continue

            own_role = '管理员' if m.role == VoMember.Role.LEADER.value else '组员'
            vos_dict[vo.id] = {
                'vo': vo,
                'own_role': own_role
            }

        for vo in vos:
            vos_dict[vo.id] = {
                'vo': vo,
                'own_role': '组长'
            }

        return vos_dict

    def notice_personal_vo_expired_servers(self, user_id: str, username: str, after_days: int = 0):
        """
        用户个人和vo组的过期云主机邮件通知
        :return:
            True    # ok
            False   # failed
            None    # 没有过期资源，不需要通知
        """
        context = self.get_personal_vo_expired_servers_context(
            user_id=user_id, username=username, after_days=after_days)
        if not context['user_servers'] and not context['vo_servers']:
            return None

        user_server_ids = [s.id for s in context['user_servers']]
        html_message = self.expired_template.render(context, request=None)
        subject = '云服务器过期提醒（中国科技云一体化云服务平台）'
        if self.do_email_notice(subject=subject, html_message=html_message, username=username):
            self.set_servers_email_lasttime(server_ids=user_server_ids, expire_notice_time=timezone.now())
            return True

        return False

    def get_personal_vo_expired_servers_context(self, user_id: str, username: str, after_days: int):
        # 个人的
        servers = self.querier.get_personal_expired_server_queryset(
            after_days=after_days, user_id=user_id
        )

        sorter = ServersSorter(
            servers=servers, after_days=after_days, filter_out_notified=self.querier.is_filter_out_notified)
        user_notice_servers = sorter.notice_servers()

        # vo的
        vo_map = self.get_vos_of_user(user_id=user_id)
        vo_ids = list(vo_map.keys())
        if vo_ids:
            vo_servers = self.querier.get_vo_expired_server_queryset(
                after_days=after_days, vo_ids=vo_ids
            )

            sorter = ServersSorter(
                servers=vo_servers, after_days=after_days, filter_out_notified=self.querier.is_filter_out_notified)
            vo_notice_servers = sorter.notice_servers()
        else:
            vo_notice_servers = []

        return {
            'username': username,
            'user_servers': user_notice_servers,
            'vo_servers': vo_notice_servers,
            'now_time': timezone.now()
        }

    def set_servers_email_lasttime(
            self, server_ids: list, expire_notice_time: datetime
    ):
        if not server_ids:
            return 0

        if self.is_update_server_email_time:
            try:
                r = self.querier.set_servers_notice_time(
                    server_ids=server_ids, expire_notice_time=expire_notice_time)
            except Exception as exc:
                r = -1
        else:
            r = 0

        return r

    def set_vo_servers_email_lasttime(
            self, after_days: int, expire_notice_time: datetime
    ):
        try:
            r = self.querier.set_vo_servers_notice_time(after_days=after_days, expire_notice_time=expire_notice_time)
        except Exception as exc:
            return -1

        return r
