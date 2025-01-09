from django.contrib import admin
from .models import User, Upload, Notification

class UploadAdmin(admin.ModelAdmin):
    list_display = ('folder_name', 'project_name', 'user', 'status', 'sample_count', 'uploaded_samples','irida_project_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('folder_name', 'project_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'task_id', 'sample_count', 'irida_project_id')

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)

admin.site.register(User)
admin.site.register(Upload, UploadAdmin)
admin.site.register(Notification, NotificationAdmin)
