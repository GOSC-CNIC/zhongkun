def get_remote_ip(request):
    _ip = request.META.get('X_FORWARDED_FOR')
    if _ip:
        _ip = _ip.split(',')[0]
    if not _ip:
        _ip = request.META.get('REMOTE_ADDR', '')

    return _ip
