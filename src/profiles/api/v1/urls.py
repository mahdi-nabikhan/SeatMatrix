
from django.urls import path, include

urlpatterns = [

    path('customer/', include('profiles.api.v1.customer.urls')),
    


]