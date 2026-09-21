from rest_framework import serializers

from .models import (
    Announcement,
    Conversation,
    ConversationMessage,
    FAQ,
    Invitation,
    Notification,
    Report,
    SupportMessage,
    SupportTicket,
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "category", "title", "message", "link",
            "event", "booking", "is_read", "created_at",
        ]
        read_only_fields = fields


class ConversationMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    mine = serializers.SerializerMethodField()

    class Meta:
        model = ConversationMessage
        fields = ["id", "sender", "sender_name", "body", "is_read", "created_at", "mine"]
        read_only_fields = ["id", "sender", "sender_name", "created_at", "mine"]

    def get_sender_name(self, obj):
        return (obj.sender.get_full_name() or obj.sender.email).strip()

    def get_mine(self, obj):
        request = (self.context or {}).get("request")
        return bool(request and request.user.is_authenticated and obj.sender_id == request.user.id)


class ConversationSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    organizer_name = serializers.SerializerMethodField()
    event_title = serializers.CharField(source="event.title", read_only=True, default=None)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "customer", "customer_name", "organizer", "organizer_name",
            "event", "event_title", "booking", "subject", "topic", "status",
            "created_at", "updated_at", "unread_count",
        ]
        read_only_fields = ["id", "customer", "organizer", "created_at", "updated_at", "unread_count"]

    def get_customer_name(self, obj):
        return (obj.customer.get_full_name() or obj.customer.email).strip()

    def get_organizer_name(self, obj):
        return (obj.organizer.get_full_name() or obj.organizer.email).strip()

    def get_unread_count(self, obj):
        request = (self.context or {}).get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.exclude(sender=request.user).filter(is_read=False).count()


class ConversationCreateSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    booking_id = serializers.IntegerField(required=False, allow_null=True)
    subject = serializers.CharField(max_length=200)
    topic = serializers.ChoiceField(choices=Conversation.Topic.choices, default=Conversation.Topic.GENERAL)
    body = serializers.CharField()


class InvitationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)
    event_id = serializers.IntegerField(source="event.id", read_only=True)

    class Meta:
        model = Invitation
        fields = [
            "id", "event", "event_id", "event_title", "email", "message",
            "token", "status", "expires_at", "responded_at", "created_at",
        ]
        read_only_fields = ["id", "event_id", "event_title", "token", "status", "expires_at", "responded_at", "created_at"]


class InvitationCreateSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    email = serializers.EmailField(required=False)
    user_id = serializers.IntegerField(required=False)
    message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("user_id"):
            raise serializers.ValidationError("Provide an email address or a user.")
        return attrs


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "event", "title", "message", "send_email", "send_in_app", "created_at"]
        read_only_fields = ["id", "created_at"]


class BroadcastSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    audience = serializers.ChoiceField(choices=["event", "selected"], default="event")
    user_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    subject = serializers.CharField(max_length=200)
    body = serializers.CharField()
    send_email = serializers.BooleanField(default=True)


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    mine = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ["id", "sender", "sender_name", "body", "created_at", "mine"]
        read_only_fields = ["id", "sender", "sender_name", "created_at", "mine"]

    def get_sender_name(self, obj):
        return (obj.sender.get_full_name() or obj.sender.email).strip()

    def get_mine(self, obj):
        request = (self.context or {}).get("request")
        return bool(request and request.user.is_authenticated and obj.sender_id == request.user.id)


class SupportTicketSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id", "user", "user_email", "subject", "category", "description",
            "priority", "status", "assigned_to", "created_at", "updated_at", "reply_count",
        ]
        read_only_fields = ["id", "user", "user_email", "created_at", "updated_at", "reply_count"]

    def get_reply_count(self, obj):
        return obj.messages.count()


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["subject", "category", "description", "priority"]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "category", "question", "answer", "order"]
        read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id", "category", "subject", "description",
            "event", "booking", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
