from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Upload, UploadFile, Notification

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username')

class UploadFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadFile
        fields = ('id', 'file', 'original_filename', 'size', 'status', 'uploaded_at')

class UploadSerializer(serializers.ModelSerializer):
    files = UploadFileSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Upload
        fields = ('id', 'user', 'folder_name', 'status', 'created_at', 'updated_at', 'files')
        read_only_fields = ('user', 'status', 'created_at', 'updated_at')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'title', 'message', 'type', 'created_at', 'read', 'related_upload')
        read_only_fields = ('created_at',) 