from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.SignInView.as_view(), name='login'),
    path('local_login/', views.LocalSignInView.as_view(), name='local_login'),
    path('logout/', views.SignOutView.as_view(), name="logout"),
    path('callback/', views.KJYLogin.as_view(), name='callback'),
    path('password/', views.ChangePasswordView.as_view(), name='password'),
    path('email/<email_id>/', views.EmailDetailView.as_view(), name='email-detail')
]
