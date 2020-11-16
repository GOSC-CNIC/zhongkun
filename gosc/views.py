from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required


@login_required()
def home(request, *args, **kwargs):
    return redirect(to=reverse('servers:server-list'))

