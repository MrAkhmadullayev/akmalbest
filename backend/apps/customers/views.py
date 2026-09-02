"""Customer views."""
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsCashierOrAdmin

from .models import Customer
from .serializers import CustomerDetailSerializer, CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['full_name', 'phone']
    ordering_fields = ['full_name', 'created_at']
    ordering = ['full_name']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsCashierOrAdmin()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer
