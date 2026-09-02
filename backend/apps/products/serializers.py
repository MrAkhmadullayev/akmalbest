"""
Product serializers.
"""
from rest_framework import serializers

from .models import Brand, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'is_active', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_product_count(self, obj):
        return obj.products.count() if hasattr(obj, 'products') else 0


class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ['id', 'name', 'description', 'is_active', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_product_count(self, obj):
        return obj.products.count() if hasattr(obj, 'products') else 0


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product lists."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, default='')
    stock_status = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category', 'category_name',
            'brand', 'brand_name', 'volume', 'unit',
            'purchase_price', 'selling_price', 'profit_margin',
            'current_stock', 'min_stock', 'warning_stock', 'max_stock',
            'stock_status', 'is_active', 'created_at',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for single product view."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, default='')
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default='')
    stock_status = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category', 'category_name',
            'brand', 'brand_name', 'volume', 'unit',
            'purchase_price', 'selling_price', 'profit_margin',
            'min_stock', 'warning_stock', 'max_stock', 'current_stock',
            'stock_status', 'supplier', 'supplier_name',
            'expiration_date', 'image', 'description',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'current_stock', 'created_at', 'updated_at']


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating products."""
    brand_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    initial_stock = serializers.IntegerField(write_only=True, required=False, default=0, min_value=0)
    payment_method = serializers.ChoiceField(
        write_only=True, required=False, choices=[('CASH', 'Naqd'), ('DEBT', 'Nasiya')], default='CASH'
    )

    class Meta:
        model = Product
        fields = [
            'name', 'barcode', 'category', 'brand', 'brand_name', 'volume', 'unit',
            'purchase_price', 'selling_price',
            'min_stock', 'warning_stock', 'max_stock',
            'expiration_date', 'image', 'description', 'is_active',
            'initial_stock', 'payment_method'
        ]
        extra_kwargs = {
            'brand': {'required': False, 'allow_null': True}
        }

    def validate_barcode(self, value):
        """Ensure barcode is unique (excluding current instance on update)."""
        instance = self.instance
        qs = Product.objects.filter(barcode=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu shtrix-kod allaqachon mavjud.")
        return value

    def validate(self, attrs):
        # Handle dynamic brand creation from brand_name
        brand_name = attrs.pop('brand_name', None)
        if brand_name:
            brand, _ = Brand.objects.get_or_create(name=brand_name.strip())
            attrs['brand'] = brand

        purchase = attrs.get('purchase_price', getattr(self.instance, 'purchase_price', 0))
        selling = attrs.get('selling_price', getattr(self.instance, 'selling_price', 0))
        if selling < purchase:
            raise serializers.ValidationError({
                "selling_price": "Sotish narxi sotib olish narxidan kam bo'lishi mumkin emas."
            })
        return attrs


class ProductBarcodeLookupSerializer(serializers.ModelSerializer):
    """Fast barcode lookup result for POS."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True, default='')
    stock_status = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category_name', 'brand_name',
            'volume', 'unit', 'selling_price', 'current_stock',
            'stock_status', 'image',
        ]
