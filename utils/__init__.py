def get_remote_ip(request):
    """
    获取客户端的ip地址和代理ip

        X-Forwarded-For 可能伪造，需要在服务一级代理防范处理
        比如nginx：
        uwsgi_param X-Forwarded-For $remote_addr;     不能使用 $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-For $remote_addr;     不能使用 $proxy_add_x_forwarded_for;

    :return: (
        str,    # 客户端真实ip地址
        list    # 经过的代理ip地址列表
    )
    """
    if 'X-Forwarded-For' in request.META:
        h = request.META.get('X-Forwarded-For')
    elif 'HTTP_X-Forwarded-For' in request.META:
        h = request.META.get('HTTP_X-Forwarded-For')
    else:
        # 标头 X-Forwarded-For 不存在
        # 没有经过代理时， REMOTE_ADDR是客户端地址
        # 经过代理时，socket方式时， REMOTE_ADDR是客户端地址；http方式时，REMOTE_ADDR是代理地址（如果代理到本机，获取的ip可能是127.0.0.1）
        return request.META.get('REMOTE_ADDR', ''), []

    ips = h.split(',')
    ips = [i.strip(' ') for i in ips]
    return ips.pop(0), ips
