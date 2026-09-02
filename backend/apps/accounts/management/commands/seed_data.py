"""Management command to seed development data."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import User, UserRole
from apps.customers.models import Customer
from apps.expenses.models import ExpenseCategory
from apps.inventory.models import Inventory
from apps.products.models import Brand, Category, Product
from apps.suppliers.models import Supplier


class Command(BaseCommand):
    help = 'Seed development data for Alkagol Store'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Users
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', password='admin123456',
                first_name='Admin', last_name='Adminov',
                role=UserRole.SUPER_ADMIN, email='admin@alkagol.uz'
            )
            self.stdout.write('  [+] Super Admin: admin / admin123456')

        users_data = [
            {'username': 'manager', 'first_name': 'Sardor', 'last_name': 'Karimov',
             'role': UserRole.ADMIN, 'phone': '+998901234567'},
            {'username': 'kassir1', 'first_name': 'Bobur', 'last_name': 'Aliyev',
             'role': UserRole.CASHIER, 'phone': '+998901234568'},
            {'username': 'kassir2', 'first_name': 'Jasur', 'last_name': 'Rahimov',
             'role': UserRole.CASHIER, 'phone': '+998901234569'},
            {'username': 'ombor', 'first_name': 'Anvar', 'last_name': 'Toshmatov',
             'role': UserRole.WAREHOUSE_MANAGER, 'phone': '+998901234570'},
        ]
        for ud in users_data:
            if not User.objects.filter(username=ud['username']).exists():
                User.objects.create_user(password='pass123456', **ud)
                self.stdout.write(f"  [+] {ud['role']}: {ud['username']} / pass123456")

        # Categories
        categories_data = ['Vodka', 'Viski', 'Pivo', 'Vino', 'Shampan', 'Konyak', 'Rom', 'Boshqa']
        categories = {}
        for name in categories_data:
            cat, _ = Category.objects.get_or_create(name=name)
            categories[name] = cat
        self.stdout.write(f'  [+] {len(categories)} categories created')

        # Brands
        brands_data = [
            'Absolut', 'Smirnoff', 'Grey Goose', 'Beluga', 'Jack Daniels',
            'Johnnie Walker', 'Jameson', 'Hennessy', 'Bacardi', 'Captain Morgan',
            'Corona', 'Heineken', 'Baltika', 'Efes', 'Moet & Chandon',
        ]
        brands = {}
        for name in brands_data:
            br, _ = Brand.objects.get_or_create(name=name)
            brands[name] = br
        self.stdout.write(f'  [+] {len(brands)} brands created')

        # Suppliers
        suppliers_data = [
            {'name': 'AlcoDist UZ', 'contact_person': 'Rustam Saidov', 'phone': '+998901111111'},
            {'name': 'Premium Drinks', 'contact_person': 'Dilshod Umarov', 'phone': '+998902222222'},
            {'name': 'BeerHouse', 'contact_person': 'Timur Ergashev', 'phone': '+998903333333'},
        ]
        suppliers = []
        for sd in suppliers_data:
            s, _ = Supplier.objects.get_or_create(name=sd['name'], defaults=sd)
            suppliers.append(s)
        self.stdout.write(f'  [+] {len(suppliers)} suppliers created')

        # Products
        products_data = [
            {'name': 'Absolut Vodka 0.5L', 'barcode': '7312040017072', 'category': 'Vodka', 'brand': 'Absolut', 'volume': '0.50', 'purchase_price': '85000', 'selling_price': '110000', 'stock': 25},
            {'name': 'Absolut Vodka 1L', 'barcode': '7312040017089', 'category': 'Vodka', 'brand': 'Absolut', 'volume': '1.00', 'purchase_price': '150000', 'selling_price': '195000', 'stock': 15},
            {'name': 'Smirnoff Red 0.5L', 'barcode': '5410316960014', 'category': 'Vodka', 'brand': 'Smirnoff', 'volume': '0.50', 'purchase_price': '55000', 'selling_price': '75000', 'stock': 30},
            {'name': 'Smirnoff Red 1L', 'barcode': '5410316960021', 'category': 'Vodka', 'brand': 'Smirnoff', 'volume': '1.00', 'purchase_price': '95000', 'selling_price': '125000', 'stock': 20},
            {'name': 'Grey Goose 0.7L', 'barcode': '3558270110013', 'category': 'Vodka', 'brand': 'Grey Goose', 'volume': '0.70', 'purchase_price': '280000', 'selling_price': '350000', 'stock': 8},
            {'name': 'Beluga Noble 0.5L', 'barcode': '4603928000013', 'category': 'Vodka', 'brand': 'Beluga', 'volume': '0.50', 'purchase_price': '180000', 'selling_price': '230000', 'stock': 12},
            {'name': 'Jack Daniels 0.7L', 'barcode': '5099873006504', 'category': 'Viski', 'brand': 'Jack Daniels', 'volume': '0.70', 'purchase_price': '220000', 'selling_price': '290000', 'stock': 10},
            {'name': 'Jack Daniels 1L', 'barcode': '5099873006511', 'category': 'Viski', 'brand': 'Jack Daniels', 'volume': '1.00', 'purchase_price': '320000', 'selling_price': '410000', 'stock': 7},
            {'name': 'Johnnie Walker Red 0.7L', 'barcode': '5000267014203', 'category': 'Viski', 'brand': 'Johnnie Walker', 'volume': '0.70', 'purchase_price': '190000', 'selling_price': '250000', 'stock': 15},
            {'name': 'Johnnie Walker Black 0.7L', 'barcode': '5000267024400', 'category': 'Viski', 'brand': 'Johnnie Walker', 'volume': '0.70', 'purchase_price': '350000', 'selling_price': '440000', 'stock': 6},
            {'name': 'Jameson 0.7L', 'barcode': '5011007003234', 'category': 'Viski', 'brand': 'Jameson', 'volume': '0.70', 'purchase_price': '200000', 'selling_price': '260000', 'stock': 12},
            {'name': 'Hennessy VS 0.7L', 'barcode': '3245995817012', 'category': 'Konyak', 'brand': 'Hennessy', 'volume': '0.70', 'purchase_price': '450000', 'selling_price': '560000', 'stock': 5},
            {'name': 'Bacardi White 0.7L', 'barcode': '5010677014205', 'category': 'Rom', 'brand': 'Bacardi', 'volume': '0.70', 'purchase_price': '170000', 'selling_price': '220000', 'stock': 14},
            {'name': 'Captain Morgan 0.7L', 'barcode': '5000281005218', 'category': 'Rom', 'brand': 'Captain Morgan', 'volume': '0.70', 'purchase_price': '160000', 'selling_price': '210000', 'stock': 18},
            {'name': 'Corona Extra 0.33L', 'barcode': '7501064191107', 'category': 'Pivo', 'brand': 'Corona', 'volume': '0.33', 'purchase_price': '12000', 'selling_price': '18000', 'stock': 48},
            {'name': 'Heineken 0.5L', 'barcode': '8710964470005', 'category': 'Pivo', 'brand': 'Heineken', 'volume': '0.50', 'purchase_price': '14000', 'selling_price': '20000', 'stock': 60},
            {'name': 'Baltika 7 0.5L', 'barcode': '4600610012408', 'category': 'Pivo', 'brand': 'Baltika', 'volume': '0.50', 'purchase_price': '8000', 'selling_price': '13000', 'stock': 72},
            {'name': 'Efes Pilsener 0.5L', 'barcode': '8690503001012', 'category': 'Pivo', 'brand': 'Efes', 'volume': '0.50', 'purchase_price': '9000', 'selling_price': '14000', 'stock': 48},
            {'name': 'Moet & Chandon Brut 0.75L', 'barcode': '3185370000014', 'category': 'Shampan', 'brand': 'Moet & Chandon', 'volume': '0.75', 'purchase_price': '650000', 'selling_price': '790000', 'stock': 4},
            {'name': 'Pivo nomalum 0.5L', 'barcode': '4780000000001', 'category': 'Pivo', 'brand': 'Efes', 'volume': '0.50', 'purchase_price': '7000', 'selling_price': '12000', 'stock': 3},
        ]

        created_count = 0
        for pd in products_data:
            if not Product.objects.filter(barcode=pd['barcode']).exists():
                product = Product.objects.create(
                    name=pd['name'],
                    barcode=pd['barcode'],
                    category=categories[pd['category']],
                    brand=brands.get(pd['brand']),
                    volume=Decimal(pd['volume']),
                    unit='bottle',
                    purchase_price=Decimal(pd['purchase_price']),
                    selling_price=Decimal(pd['selling_price']),
                    current_stock=pd['stock'],
                    supplier=suppliers[0] if pd['category'] in ('Vodka', 'Viski', 'Konyak', 'Rom') else suppliers[2],
                    min_stock=5,
                    warning_stock=10,
                    max_stock=100,
                )
                Inventory.objects.get_or_create(
                    product=product,
                    defaults={'quantity': pd['stock']}
                )
                created_count += 1
        self.stdout.write(f'  [+] {created_count} products created')

        # Customers
        customers_data = [
            {'full_name': 'Akbar Xolmatov', 'phone': '+998901001001'},
            {'full_name': 'Dilshod Normatov', 'phone': '+998901001002'},
            {'full_name': 'Farhod Sultonov', 'phone': '+998901001003'},
            {'full_name': 'Islom Karimov', 'phone': '+998901001004'},
            {'full_name': 'Mirzo Ulugbek', 'phone': '+998901001005'},
        ]
        for cd in customers_data:
            Customer.objects.get_or_create(full_name=cd['full_name'], defaults=cd)
        self.stdout.write(f'  [+] {len(customers_data)} customers created')

        # Expense Categories
        expense_cats = ['Ijara', 'Elektr energiya', 'Oylik', 'Yetkazib berish', 'Boshqa']
        for name in expense_cats:
            ExpenseCategory.objects.get_or_create(name=name)
        self.stdout.write(f'  [+] {len(expense_cats)} expense categories created')

        self.stdout.write('Seed data created successfully!')
        self.stdout.write('Login credentials: admin / admin123456')
