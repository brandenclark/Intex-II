from django.db import models, transaction
from django.conf import settings
from django.forms.models import model_to_dict
from polymorphic.models import PolymorphicModel
from decimal import Decimal
from datetime import datetime
import stripe


class Category(models.Model):
    Name = models.TextField()
    Description = models.TextField()
    CreateDate = models.DateTimeField(auto_now_add=True)
    LastModified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Name

# products[0].__class__.__name__ = 'BulkProdcut'
# pip3 install django-polymorphic
class Product(PolymorphicModel):
    TYPE_CHOICES = (
    ('BulkProduct', 'Bulk Product'),
    ('IndividualProduct', 'Individual Product'),
    ('RentalProduct', 'Rental Product'),
    )

    STATUS_CHOICES = (
    ('A', 'Active'),
    ('I', 'Inactive'),
    )

    Name = models.TextField()
    Description = models.TextField()
    Category = models.ForeignKey(Category, on_delete=models.CASCADE)
    Price = models.DecimalField(max_digits=8, decimal_places=2)
    CreateDate = models.DateTimeField(auto_now_add=True)
    LastModified = models.DateTimeField(auto_now=True)
    Status = models.TextField(choices=STATUS_CHOICES, default='A')

    def new_object(self, name = '', description = '', category = None, price = 0, status = 'A'):
        self.Name = name
        self.Description = description
        self.Category = category
        self.Price = price
        self.Status = status

    # convenience method
    def image_url(self, id):
        ''' Always return an image '''
        product = ProductImage.objects.all().filter(Product_id = id).first()
        if product is not None:
            url = '/static/catalog/media/products/' + product.Filename
        else:
            url = '/static/catalog/media/products/image_unavailable.gif'
        return url

    def image_urls(self, id):
        '''Returns a list of all images for that product'''
        product = Product.objects.all().filter(id = id).first()
        urls = []
        if product is not None:
            for i in product.images.all():
                urls.append('/static/catalog/media/products/' + i.Filename)
        else:
            urls.append('/static/catalog/media/products/image_unavailable.gif')
        return urls

class BulkProduct(Product):
    TITLE = 'BulkProduct'
    Quantity = models.IntegerField()
    ReorderTrigger = models.IntegerField()
    ReorderQuantity = models.IntegerField()

class IndividualProduct(Product):
    TITLE = 'IndividualProduct'
    ItemID = models.TextField()

class RentalProduct(Product):
    TITLE = 'RentalProduct'
    ItemID = models.TextField()
    MaxRental = models.IntegerField()
    RetireDate = models.DateTimeField(null=True, blank=True)

class ProductImage(models.Model):
    Filename = models.TextField()
    Product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    CreateDate = models.DateTimeField(auto_now_add=True)
    LastModified = models.DateTimeField(auto_now=True)


#######################################################################
###   Products

# various product models go here


#######################################################################
###   Orders

class Order(models.Model):
    '''An order in the system'''
    STATUS_CHOICES = (
        ( 'cart', 'Shopping Cart' ),
        ( 'payment', 'Payment Processing' ),
        ( 'sold', 'Finalized Sale' ),
    )
    order_date = models.DateTimeField(null=True, blank=True)
    name = models.TextField(blank=True, default="Shopping Cart")
    status = models.TextField(choices=STATUS_CHOICES, default='cart', db_index=True)
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0) # max number is 999,999.99
    user = models.ForeignKey('account.User', related_name='orders',  on_delete=models.CASCADE)
    # shipping information
    ship_date = models.DateTimeField(null=True, blank=True)
    ship_tracking = models.TextField(null=True, blank=True)
    ship_name = models.TextField(null=True, blank=True)
    ship_address = models.TextField(null=True, blank=True)
    ship_city = models.TextField(null=True, blank=True)
    ship_state = models.TextField(null=True, blank=True)
    ship_zip_code = models.TextField(null=True, blank=True)

    def __str__(self):
        '''Prints for debugging purposes'''
        return 'Order {}: {}: {}'.format(self.id, self.user.get_full_name(), self.total_price)


    def active_items(self, include_tax_item=True):
        '''Returns the active items on this order'''
        # create a query object (filter to status='active')

        # if we aren't including the tax item, alter the
        # query to exclude that OrderItem
        # I simply used the product name (not a great choice,
        # but it is acceptable for credit)


    def get_item(self, product, create=False):
        '''Returns the OrderItem object for the given product'''
        item = OrderItem.objects.filter(order=self, product=product).first()
        if item is None and create:
            item = OrderItem.objects.create(order=self, product=product, price=product.price, quantity=0)
        elif create and item.status != 'active':
            item.status = 'active'
            item.quantity = 0
        item.recalculate()
        item.save()
        return item


    def num_items(self):
        '''Returns the number of items in the cart'''
        return sum(self.active_items(include_tax_item=False).values_list('quantity', flat=True))


    def recalculate(self):
        '''
        Recalculates the total price of the order,
        including recalculating the taxable amount.

        Saves this Order and all child OrderLine objects.
        '''
        # iterate the order items (not including tax item) and get the total price
        # call recalculate on each item

        # update/create the tax order item (calculate at 7% rate)

        # update the total and save


    def finalize(self, stripe_charge_token):
        '''Runs the payment and finalizes the sale'''
        with transaction.atomic():
            # recalculate just to be sure everything is updated

            # check that all products are available

            # contact stripe and run the payment (using the stripe_charge_token)

            # finalize (or create) one or more payment objects

            # set order status to sold and save the order

            # update product quantities for BulkProducts
            # update status for IndividualProducts


class OrderItem(PolymorphicModel):
    '''A line item on an order'''
    STATUS_CHOICES = (
        ( 'active', 'Active' ),
        ( 'deleted', 'Deleted' ),
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    status = models.TextField(choices=STATUS_CHOICES, default='active', db_index=True)
    product = models.ForeignKey(Product, null=True, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0) # max number is 999,999.99
    quantity = models.IntegerField(default=0)
    extended = models.DecimalField(max_digits=8, decimal_places=2, default=0) # max number is 999,999.99

    def __str__(self):
        '''Prints for debugging purposes'''
        return 'OrderItem {}: {}: {}'.format(self.id, self.product.name, self.extended)


    def recalculate(self):
        '''Updates the order item's price, quantity, extended'''
        # update the price if it isn't already set and we have a product

        # default the quantity to 1 if we don't have a quantity set

        # calculate the extended (price * quantity)

        # save the changes


class Payment(models.Model):
    '''A payment on a sale'''
    order = models.ForeignKey(Order, null=True, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(blank=True, null=True, max_digits=8, decimal_places=2) # max number is 999,999.99
    validation_code = models.TextField(null=True, blank=True)
