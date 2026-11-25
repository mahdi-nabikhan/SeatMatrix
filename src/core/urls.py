from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Swagger / OpenAPI URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/accounts/', include('accounts.api.v1.urls', namespace='accounts-v1')),
    path('api/v1/profiles/', include('profiles.api.v1.urls')),
    path('api/v1/cinemas/', include('cinemas.api.v1.urls')),
    path('api/v1/operations/', include('operations.api.v1.urls')),
    path('api/v1/orders/', include('orders.api.v1.urls')),
    
]