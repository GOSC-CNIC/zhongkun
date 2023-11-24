from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from version import __version__, __git_tagset__, __git_changeset__


@login_required()
def home(request, *args, **kwargs):
    return redirect(to=reverse('servers:server-list'))


def get_about_context():
    _version = __version__.lower()
    if not _version.startswith('v'):
        _version = 'v' + _version

    current_tag = None
    if __git_tagset__:
        v = __git_tagset__[0][0]
        if _version == v:
            current_tag = __git_tagset__.pop(0)

    if current_tag is None:
        current_tag = [_version, None, '', '', '']
        if __git_changeset__:
            current_tag[1] = __git_changeset__.get('timestamp')
            current_tag[2] = __git_changeset__.get('author')

    return {
        'current_tag': current_tag, 'git_tagset': __git_tagset__
    }


__about_context__ = get_about_context()


@cache_page(60 * 60)
def about(request):
    return render(request, 'about.html', context=__about_context__)
