"""
Account serializers for authentication and user management.
"""
from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import MODULES, User


class ModulePermissionsField(serializers.JSONField):
    """{"reports": true, "pos": false} ko'rinishidagi ruxsatlar xaritasi.

    DRF `ModelSerializer` o'zi tanimagan maydonlarni JIMGINA tashlab yuboradi,
    shuning uchun bu maydon aniq e'lon qilinadi va qiymati qat'iy tekshiriladi:
    noto'g'ri modul nomi yozilsa xato qaytadi, "saqlandi" deb aldamaydi.
    """

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if not isinstance(data, dict):
            raise serializers.ValidationError("Ruxsatlar obyekt (dict) bo'lishi kerak.")

        unknown = sorted(set(data) - set(MODULES))
        if unknown:
            raise serializers.ValidationError(
                f"Noma'lum modul(lar): {', '.join(unknown)}. "
                f"Ruxsat etilganlar: {', '.join(MODULES)}."
            )
        return {module: bool(value) for module, value in data.items()}


def _user_payload(user):
    """Login javobida qaytadigan foydalanuvchi ma'lumoti."""
    return {
        'id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'role': user.role,
        'email': user.email or '',
        'phone': user.phone or '',
        'is_active': user.is_active,
        'permissions': user.permissions or {},
        'effective_permissions': user.effective_permissions,
    }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user info in response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = _user_payload(self.user)
        return data


class UserSerializer(serializers.ModelSerializer):
    """User serializer for list and detail views."""
    full_name = serializers.ReadOnlyField()
    effective_permissions = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'role', 'is_active',
            'permissions', 'effective_permissions',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""
    password = serializers.CharField(
        write_only=True, validators=[django_validate_password],
    )
    password_confirm = serializers.CharField(write_only=True)
    permissions = ModulePermissionsField(required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active', 'permissions',
            'password', 'password_confirm',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({"password_confirm": "Parollar mos kelmadi."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profiles.

    Parol ixtiyoriy: yuborilsa almashtiriladi, yuborilmasa tegilmaydi.
    """
    permissions = ModulePermissionsField(required=False)
    # Bo'sh satr kelishi mumkin ("parolni o'zgartirmayman"), shuning uchun
    # `validators=` emas, qo'lda tekshiramiz — aks holda '' murakkablik
    # tekshiruvidan o'ta olmay xato beradi.
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
    )
    password_confirm = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone',
            'role', 'is_active', 'permissions',
            'password', 'password_confirm',
        ]

    def validate_password(self, value):
        if value:
            django_validate_password(value)
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)

        if not password:
            # Bo'sh parol = "o'zgartirmang". Validatorlar bo'sh satrga tushmasin.
            attrs.pop('password', None)
            return attrs

        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Parollar mos kelmadi."})
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[django_validate_password],
    )
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Yangi parollar mos kelmadi."})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Joriy parol noto'g'ri.")
        return value


class MeSerializer(serializers.ModelSerializer):
    """Serializer for authenticated user's own profile."""
    full_name = serializers.ReadOnlyField()
    effective_permissions = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'role', 'is_active',
            'permissions', 'effective_permissions',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
