from django.shortcuts import render
from django.views import View
from django.http.response import JsonResponse, HttpResponse
from django.template import loader

from utils.paginators import NumsPaginator
from apps.app_report.workers.server_notifier import ServerNotifier, PersonalServersNotifier
from apps.servers.models import ServiceConfig
from .managers import ServerManager


def to_int_or_default(val, default=None):
    if not val:
        return default

    try:
        return int(val)
    except ValueError:
        return default


class ServerView(View):
    NUM_PER_PAGE = 20       # Show num per page

    def get(self, request, *args, **kwargs):
        service_id = request.GET.get('service')
        user = request.user

        if service_id:
            service = ServiceConfig.objects.filter(id=service_id).first()
            is_need_vpn = service.is_need_vpn()
        else:
            is_need_vpn = False

        servers_qs = ServerManager().get_user_servers_queryset(user=user, service_id=service_id)
        # 分页显示
        paginator = NumsPaginator(request, servers_qs, self.NUM_PER_PAGE)
        page_num = request.GET.get(paginator.page_query_name, 1)  # 获取页码参数，没有参数默认为1
        servers_page = paginator.get_page(page_num)
        page_nav = paginator.get_page_nav(servers_page)
        context = {
            'active_service': service_id,
            'is_need_vpn': is_need_vpn,
            'servers': servers_page,
            'page_nav': page_nav,
            'count': paginator.count
        }
        return render(request, 'server_list.html', context=context)


class ServerCreateView(View):
    def get(self, request, *args, **kwargs):
        # service_id = kwargs.get('service_id')
        return render(request, 'create.html')


class VmwareConsoleView(View):
    def get(self, request, *args, **kwargs):
        vm_url = request.GET.get('vm_url')
        server_name = request.GET.get('server-name', '')
        return render(request, 'console.html', context={'vm_url': vm_url, 'server_name': server_name})


class ServerExpiredEmailView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        after_days = request.GET.get('after_days')
        tag = request.GET.get('tag')

        if after_days:
            after_days = int(after_days)
        else:
            after_days = 0

        if not tag:
            tag = 'user_vo'

        if tag == 'user':
            context = PersonalServersNotifier(filter_out_notified=False).get_personal_expired_servers_context(
                user_id=user.id, username=user.username, after_days=after_days)
        elif tag == 'user_vo':
            context = ServerNotifier(filter_out_notified=False).get_personal_vo_expired_servers_context(
                user_id=user.id, username=user.username, after_days=after_days)
        else:
            return JsonResponse(
                data={'message': f'tag参数值无效，可选[user, user_vo]'},
                json_dumps_params={'ensure_ascii': False}
            )

        content = loader.render_to_string('server_expired.html', context=context, request=request, using=None)
        content = ServerNotifier.html_minify(content)
        return HttpResponse(content)
