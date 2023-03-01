from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required

from version import __version__, __git_tagset__, __git_changeset__


@login_required()
def home(request, *args, **kwargs):
    return redirect(to=reverse('servers:server-list'))


def about(request):
    return render(request, 'about.html', context={
        'version': __version__, 'git_tagset': __git_tagset__,
        'git_changeset': __git_changeset__
    })
