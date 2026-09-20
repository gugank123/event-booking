from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "role", "is_active", "date_joined"]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = (instance.get_full_name() or instance.email).strip()
        data["status"] = "active" if instance.is_active else "suspended"
        return data


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=[User.Role.ATTENDEE, User.Role.ORGANIZER], default=User.Role.ATTENDEE)

    class Meta:
        model = User
        fields = ["name", "email", "password", "role"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with that email already exists.")
        return value

    def create(self, validated_data):
        name = validated_data.pop("name").strip()
        first_name, _, last_name = name.partition(" ")
        email = validated_data["email"]
        user = User(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=validated_data.get("role", User.Role.ATTENDEE),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        user = authenticate(username=email, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Incorrect email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been suspended.")
        attrs["user"] = user
        return attrs
