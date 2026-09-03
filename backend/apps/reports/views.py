"""Reports views - analytics and dashboard data from real database."""
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.debts.models import Debt, DebtStatus
from apps.expenses.models import Expense
from apps.products.models import Product
from apps.sales.models import Sale, SaleItem, SaleStatus


class DashboardView(APIView):
    """Dashboard statistics - all data from database."""
    required_module = 'dashboard'
    permission_classes = [HasModulePermission]

    def get(self, request):
        today = timezone.now().date()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Today's sales
        today_sales = Sale.objects.filter(
            created_at__gte=today_start,
            status=SaleStatus.COMPLETED
        )
        today_sales_total = today_sales.aggregate(total=Sum('total'))['total'] or Decimal('0')
        today_sales_count = today_sales.count()
        today_profit = today_sales.aggregate(total=Sum('profit'))['total'] or Decimal('0')

        # Today's sales by payment method
        today_cash = today_sales.filter(payment_method='CASH').aggregate(total=Sum('total'))['total'] or Decimal('0')
        today_card = today_sales.filter(payment_method='CARD').aggregate(total=Sum('total'))['total'] or Decimal('0')
        today_debt = today_sales.filter(payment_method='DEBT').aggregate(total=Sum('total'))['total'] or Decimal('0')

        # Today's expenses
        today_expenses = Expense.objects.filter(
            expense_date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Debts
        total_debt = Debt.objects.exclude(
            status=DebtStatus.PAID
        ).aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0')

        overdue_debt = Debt.objects.filter(
            status=DebtStatus.OVERDUE
        ).aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0')

        overdue_count = Debt.objects.filter(status=DebtStatus.OVERDUE).count()

        # Stock
        low_stock_count = Product.objects.filter(
            is_active=True, current_stock__lte=F('min_stock'), current_stock__gt=0
        ).count()

        out_of_stock_count = Product.objects.filter(
            is_active=True, current_stock__lte=0
        ).count()

        total_products = Product.objects.filter(is_active=True).count()

        # Stock values by payment method
        from apps.inventory.models import InventoryBatch
        batches = InventoryBatch.objects.filter(current_quantity__gt=0)

        inventory_debt_value = batches.filter(payment_method='DEBT').annotate(
            value=F('current_quantity') * F('purchase_price')
        ).aggregate(total=Sum('value'))['total'] or Decimal('0')

        inventory_cash_value = batches.filter(payment_method='CASH').annotate(
            value=F('current_quantity') * F('purchase_price')
        ).aggregate(total=Sum('value'))['total'] or Decimal('0')

        # Recent sales
        recent_sales = Sale.objects.select_related('cashier', 'customer').order_by('-created_at')[:10]
        recent_sales_data = [
            {
                'id': str(s.id),
                'sale_number': s.sale_number,
                'cashier': s.cashier.full_name,
                'customer': s.customer.full_name if s.customer else '',
                'total': str(s.total),
                'payment_method': s.payment_method,
                'status': s.status,
                'created_at': s.created_at.isoformat(),
            }
            for s in recent_sales
        ]

        # Low stock products
        low_stock_products = Product.objects.filter(
            is_active=True, current_stock__lte=F('warning_stock')
        ).order_by('current_stock')[:10]
        low_stock_data = [
            {
                'id': str(p.id),
                'name': p.name,
                'barcode': p.barcode,
                'current_stock': p.current_stock,
                'min_stock': p.min_stock,
                'stock_status': p.stock_status,
            }
            for p in low_stock_products
        ]

        # Overdue debts
        overdue_debts = Debt.objects.filter(
            status=DebtStatus.OVERDUE
        ).select_related('customer').order_by('due_date')[:10]
        overdue_data = [
            {
                'id': str(d.id),
                'customer': d.customer.full_name,
                'phone': d.customer.phone,
                'remaining_amount': str(d.remaining_amount),
                'due_date': str(d.due_date),
            }
            for d in overdue_debts
        ]

        return Response({
            'today_sales_total': str(today_sales_total),
            'today_sales_count': today_sales_count,
            'today_cash_sales': str(today_cash),
            'today_card_sales': str(today_card),
            'today_debt_sales': str(today_debt),
            'today_profit': str(today_profit),
            'today_expenses': str(today_expenses),
            'total_debt': str(total_debt),
            'overdue_debt': str(overdue_debt),
            'overdue_count': overdue_count,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'total_products': total_products,
            'inventory_debt_value': str(inventory_debt_value),
            'inventory_cash_value': str(inventory_cash_value),
            'recent_sales': recent_sales_data,
            'low_stock_products': low_stock_data,
            'overdue_debts': overdue_data,
        })


class SalesReportView(APIView):
    """Sales report with date range filtering."""
    required_module = 'reports'
    permission_classes = [HasModulePermission]

    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        qs = Sale.objects.filter(status=SaleStatus.COMPLETED)

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        stats = qs.aggregate(
            total_revenue=Sum('total'),
            total_profit=Sum('profit'),
            total_sales=Count('id'),
            total_discount=Sum('discount'),
        )

        # Sales by payment method
        by_method = qs.values('payment_method').annotate(
            count=Count('id'), total=Sum('total')
        )

        # Sales by day
        daily = qs.extra(
            select={'day': "DATE(created_at)"}
        ).values('day').annotate(
            total=Sum('total'), profit=Sum('profit'), count=Count('id')
        ).order_by('day')

        # Top products
        top_products = SaleItem.objects.filter(
            sale__in=qs
        ).values(
            'product__name', 'product__barcode'
        ).annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum('subtotal'),
            total_profit=Sum('profit'),
        ).order_by('-total_qty')[:10]

        return Response({
            'summary': {
                'total_revenue': str(stats['total_revenue'] or 0),
                'total_profit': str(stats['total_profit'] or 0),
                'total_sales': stats['total_sales'] or 0,
                'total_discount': str(stats['total_discount'] or 0),
            },
            'by_payment_method': list(by_method),
            'daily': list(daily),
            'top_products': list(top_products),
        })


class ProfitReportView(APIView):
    """Profit report."""
    required_module = 'reports'
    permission_classes = [HasModulePermission]

    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        sales_qs = Sale.objects.filter(status=SaleStatus.COMPLETED)
        expenses_qs = Expense.objects.all()

        if date_from:
            sales_qs = sales_qs.filter(created_at__date__gte=date_from)
            expenses_qs = expenses_qs.filter(expense_date__gte=date_from)
        if date_to:
            sales_qs = sales_qs.filter(created_at__date__lte=date_to)
            expenses_qs = expenses_qs.filter(expense_date__lte=date_to)

        revenue = sales_qs.aggregate(total=Sum('total'))['total'] or Decimal('0')
        gross_profit = sales_qs.aggregate(total=Sum('profit'))['total'] or Decimal('0')
        total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        net_profit = gross_profit - total_expenses

        return Response({
            'revenue': str(revenue),
            'gross_profit': str(gross_profit),
            'total_expenses': str(total_expenses),
            'net_profit': str(net_profit),
        })


class InventoryReportView(APIView):
    """Inventory report."""
    required_module = 'reports'
    permission_classes = [HasModulePermission]

    def get(self, request):
        products = Product.objects.filter(is_active=True)

        total_products = products.count()
        total_stock_value = sum(
            p.current_stock * p.purchase_price for p in products
        )
        total_retail_value = sum(
            p.current_stock * p.selling_price for p in products
        )
        low_stock = products.filter(current_stock__lte=F('min_stock'), current_stock__gt=0).count()
        out_of_stock = products.filter(current_stock__lte=0).count()

        return Response({
            'total_products': total_products,
            'total_stock_value': str(total_stock_value),
            'total_retail_value': str(total_retail_value),
            'low_stock_count': low_stock,
            'out_of_stock_count': out_of_stock,
        })


class DebtReportView(APIView):
    """Debt report."""
    required_module = 'reports'
    permission_classes = [HasModulePermission]

    def get(self, request):
        debts = Debt.objects.exclude(status=DebtStatus.PAID)

        total_debt = debts.aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0')
        active_count = debts.filter(status=DebtStatus.ACTIVE).count()
        overdue_count = debts.filter(status=DebtStatus.OVERDUE).count()
        partially_paid = debts.filter(status=DebtStatus.PARTIALLY_PAID).count()

        # Top debtors
        from apps.customers.models import Customer
        top_debtors = Customer.objects.filter(
            debts__status__in=[DebtStatus.ACTIVE, DebtStatus.PARTIALLY_PAID, DebtStatus.OVERDUE]
        ).annotate(
            total_remaining=Sum('debts__remaining_amount')
        ).order_by('-total_remaining')[:10]

        top_debtors_data = [
            {
                'id': str(c.id),
                'name': c.full_name,
                'phone': c.phone,
                'total_remaining': str(c.total_remaining),
            }
            for c in top_debtors
        ]

        return Response({
            'total_debt': str(total_debt),
            'active_count': active_count,
            'overdue_count': overdue_count,
            'partially_paid_count': partially_paid,
            'top_debtors': top_debtors_data,
        })
