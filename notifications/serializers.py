from rest_framework import serializers
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from .models import Notification, NotificationPreference, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'notification_type_display',
            'title', 'message', 'priority', 'priority_display', 'is_read', 'read_at',
            'created_at', 'content_type', 'object_id', 'action_url', 'data'
        ]
        read_only_fields = ['created_at', 'read_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications."""
    content_type_model = serializers.CharField(write_only=True, required=False)
    object_id = serializers.IntegerField(required=False)
    
    class Meta:
        model = Notification
        fields = [
            'user', 'notification_type', 'title', 'message', 'priority',
            'content_type_model', 'object_id', 'action_url', 'data'
        ]
    
    def validate(self, data):
        content_type_model = data.pop('content_type_model', None)
        object_id = data.get('object_id')
        
        if content_type_model and object_id:
            try:
                app_label, model = content_type_model.split('.')
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                data['content_type'] = content_type
            except (ValueError, ContentType.DoesNotExist):
                raise serializers.ValidationError({
                    'content_type_model': 'Invalid content type format. Use "app_label.model_name"'
                })
        elif (content_type_model and not object_id) or (not content_type_model and object_id):
            raise serializers.ValidationError({
                'content_type_model': 'Both content_type_model and object_id must be provided together'
            })
        
        return data


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'email_notifications', 'push_notifications', 'sms_notifications',
            'system_notifications', 'inquiry_notifications', 'listing_notifications',
            'review_notifications', 'message_notifications', 'subscription_notifications',
            'account_notifications', 'marketing_emails', 'newsletter_subscription'
        ]
        read_only_fields = ['user']
    
    def create(self, validated_data):
        user = self.context['request'].user
        # Check if preferences already exist for this user
        try:
            preferences = NotificationPreference.objects.get(user=user)
            # Update existing preferences
            for attr, value in validated_data.items():
                setattr(preferences, attr, value)
            preferences.save()
            return preferences
        except NotificationPreference.DoesNotExist:
            # Create new preferences
            return NotificationPreference.objects.create(user=user, **validated_data)


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for device tokens."""
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'user', 'token', 'device_type', 'device_name',
            'is_active', 'created_at', 'last_used_at'
        ]
        read_only_fields = ['user', 'created_at', 'last_used_at']
    
    def create(self, validated_data):
        user = self.context['request'].user
        token = validated_data.get('token')
        
        # Check if token already exists
        try:
            device_token = DeviceToken.objects.get(token=token)
            # Update existing token if it belongs to the same user
            if device_token.user == user:
                for attr, value in validated_data.items():
                    setattr(device_token, attr, value)
                device_token.save()
                return device_token
            else:
                # Token exists but belongs to another user, deactivate old one and create new
                device_token.is_active = False
                device_token.save()
        except DeviceToken.DoesNotExist:
            pass
        
        # Create new token
        return DeviceToken.objects.create(user=user, **validated_data)


class MarkNotificationsReadSerializer(serializers.Serializer):
    """Serializer for marking multiple notifications as read."""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    
    def validate(self, data):
        user = self.context['request'].user
        notification_ids = data.get('notification_ids', [])
        
        # Verify all notifications belong to the user
        notifications = Notification.objects.filter(id__in=notification_ids)
        if notifications.exclude(user=user).exists():
            raise serializers.ValidationError({
                'notification_ids': 'You can only mark your own notifications as read'
            })
        
        return data