from django.urls import path
from . import views
from ninja import NinjaAPI
from .api import api as uploader_api

api = NinjaAPI()
api.add_router('/', uploader_api)

app_name = 'uploader'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('folders/', views.get_folders, name='get_folders'),
    path('upload/', views.upload_files, name='upload_files'),
    path('upload/<int:upload_id>/status/', views.get_upload_status, name='get_upload_status'),
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('test-celery/', views.test_celery, name='test_celery'),
    path('test-result/<str:task_id>/', views.test_result, name='test_result'),
    path('api/', api.urls),  # This will include Swagger UI at /api/docs
] 