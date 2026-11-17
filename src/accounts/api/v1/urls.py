from django.urls import path
from .views import (
    UserRegistrationApiView,EmailJwtLoginApiView,
    UsernameJwtLoginAPIview,CheckUserLoginApiview,
    LogoutApiView,RequestOTPApiView,VerifyOTPLoginApiView)


app_name = 'accounts-v1'

urlpatterns = [
    path('register/user', UserRegistrationApiView.as_view(), name='user-register'),
    path('login/email',EmailJwtLoginApiView.as_view(),name='login-email'),
    path('login/username/', UsernameJwtLoginAPIview.as_view(), name='login-username'),
    path('check/auth',CheckUserLoginApiview.as_view(),name='check'),
    path('logout/', LogoutApiView.as_view(), name='logout'),
    path('login/otp/request/', RequestOTPApiView.as_view(), name='otp_request'),
    path('login/otp/verify/', VerifyOTPLoginApiView.as_view(), name='otp_verify'),

]



