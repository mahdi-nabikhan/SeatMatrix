
from django.urls import path, include
app_name = 'profile-v1'

urlpatterns = [
    path('customer/', include('profiles.api.v1.customer.urls')),
    path('manager/', include('profiles.api.v1.manager.urls')),


]