"""Customer views."""
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.accounts.permissions import HasModulePermission, IsCashierOrAdmin

from .models import Customer
from .serializers import CustomerDetailSerializer, CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    required_module = 'customers'
    queryset = Customer.objects.all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['full_name', 'phone']
    ordering_fields = ['full_name', 'created_at']
    ordering = ['full_name']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [HasModulePermission()]
        return [HasModulePermission(), IsCashierOrAdmin()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer
