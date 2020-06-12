from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Article, VPNAuth


def usage(request, *args, **kwags):
    """
    vpn使用说明视图
    """
    article_usage = Article.objects.filter(topic=Article.TOPIC_VPN_USAGE).first()
    return render(request, 'article.html', context={'article': article_usage})


@login_required()
def vpn(request, *args, **kwargs):
    user = request.user
    vpn, created = VPNAuth.objects.get_or_create(user=user)
    return render(request, 'vpn.html', context={'vpn': vpn})





