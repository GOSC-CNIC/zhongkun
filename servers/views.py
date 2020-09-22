from django.shortcuts import render
from django.views import View

from utils.paginators import NumsPaginator
from .models import ServiceConfig, Server


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
        service_id = to_int_or_default(kwargs.get('service_id'), default=None)
        user = request.user

        if service_id:
            servers_qs = Server.objects.filter(service=service_id, user=user).all()
        else:
            servers_qs = Server.objects.filter(user=user).all()

        # 分页显示
        paginator = NumsPaginator(request, servers_qs, self.NUM_PER_PAGE)
        page_num = request.GET.get(paginator.page_query_name, 1)  # 获取页码参数，没有参数默认为1
        servers_page = paginator.get_page(page_num)
        page_nav = paginator.get_page_nav(servers_page)
        context = {
            'active_service': service_id,
            'servers': servers_page,
            'page_nav': page_nav,
            'count': paginator.count
        }
        return render(request, 'server_list.html', context=context)


class ServerCreateView(View):
    def get(self, request, *args, **kwargs):
        service_id = kwargs.get('service_id')
        return render(request, 'create.html', context={'service_id': service_id})
