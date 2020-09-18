from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.SignInView.as_view(), name='login'),
    path('logout/', views.SignOutView.as_view(), name="logout"),
    path('callback/', views.KJYLogin.as_view(), name='callback'),
    path('password/', views.ChangePasswordView.as_view(), name='password')
]
