"""
Account views for authentication and user management.
"""
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    MeSerializer,
)
from .permissions import IsSuperAdmin, IsAdmin


class LoginView(TokenObtainPairView):
    """JWT Login endpoint."""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class RefreshTokenView(TokenRefreshView):
    """JWT Token refresh endpoint."""
    permission_classes = [AllowAny]


class LogoutView(generics.GenericAPIView):
    """Blacklist refresh token on logout."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"success": True, "message": "Tizimdan chiqildi."},
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"success": True, "message": "Tizimdan chiqildi."},
                status=status.HTTP_200_OK
            )


class MeView(generics.RetrieveAPIView):
    """Get current authenticated user profile."""
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    """User CRUD management - Super Admin only."""
    queryset = User.objects.all()
    permission_classes = [IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'phone', 'email']
    ordering_fields = ['created_at', 'username', 'first_name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.id == request.user.id:
            return Response(
                {"success": False, "message": "O'zingizni o'chira olmaysiz.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Soft delete
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response(
            {"success": True, "message": "Foydalanuvchi o'chirildi."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        """Admin change user password."""
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {"success": True, "message": "Parol o'zgartirildi."},
            status=status.HTTP_200_OK
        )
