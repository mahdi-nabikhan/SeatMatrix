from django.urls import path
from .views import (
    UserRegistrationApiView,)


app_name = 'accounts-v1'

urlpatterns = [
    path('register/user', UserRegistrationApiView.as_view(), name='user-register'),

]



