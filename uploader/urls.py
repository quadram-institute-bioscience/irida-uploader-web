from django.urls import path
from . import views
from .api import api

app_name = 'uploader'

urlpatterns = [
    # API URLs
    path('api/', api.urls),  # This will include Swagger UI at /api/docs
    
    # Template URLs
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('folders/', views.get_folders, name='get_folders'),
    path('upload/', views.upload_files, name='upload_files'),
    path('upload/<int:upload_id>/status/', views.get_upload_status, name='get_upload_status'),
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
] 