from django.urls import path
from .views import (
    UserRegistrationApiView,EmailJwtLoginApiView,UsernameJwtLoginAPIview
    ,CheckUserLoginApiview,LogoutApiView)


app_name = 'accounts-v1'

urlpatterns = [
    path('register/user', UserRegistrationApiView.as_view(), name='user-register'),
    path('login/email',EmailJwtLoginApiView.as_view(),name='login-email'),
    path('login/username/', UsernameJwtLoginAPIview.as_view(), name='login-username'),
    path('check/auth',CheckUserLoginApiview.as_view(),name='check'),
    path('logout/', LogoutApiView.as_view(), name='logout'),

]



