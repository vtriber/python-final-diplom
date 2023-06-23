from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator



STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)

DELIVERY_METHOD_CHOICES = (
    ('Почта России'),
    ('ТК КИТ'),
    ('ТК СДЭК'),
    ('ТК Деловые линии'),
)

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)

class UserManager(BaseUserManager):

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('Необходимо указать адрес электронной почты')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Не более 150 символов. Только латинские буквы, цифры и @/./+/-/_.'),
        validators=[username_validator],
        error_messages={
            'unique': _("Пользователь с таким именем уже существует."),
        },
    )
    is_active = models.BooleanField(_('active'), default=False,)
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')
    vk_id = models.CharField(max_length=50, verbose_name='ID страницы VK', blank=True)
    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)

    def __str__(self):
        return self.username

class Shop(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка на сайт', null=True, blank=True)
    state = models.BooleanField(verbose_name='Cтатус получения заказов', default=True)
    user = models.OneToOneField(User, verbose_name='Пользователь',
                                blank=True, null=True,
                                on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=250, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазин')

    def __str__(self):
        return self.name

class Subcategory(models.Model):
    name = models.CharField(max_length=250, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='subcategories',
                                 on_delete=models.CASCADE, blank=True)

    def __str__(self):
        return  self.name

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products',
                                 on_delete=models.CASCADE, blank=True)
    subcategory = models.ForeignKey(Category, verbose_name='Подкатегория', related_name='products',
                                    on_delete=models.CASCADE, blank=True)
    def __str__(self):
        return  self.name


class Unit(models.Model):
    name = models.CharField(max_length=10, verbose_name='Единица измерения')

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    product = models.ForeignKey(Product)
    shop = models.ForeignKey(Shop)
    name = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Количество')
    unit = models.ForeignKey(Unit, default='шт.', verbose_name='Единица измерения')
    weight = models.DecimalField(max_digits=10,decimal_places=2, verbose_name='Вес единицы, кг')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендованная цена')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = 'Информационный список о продуктах'


class Parameter(models.Model):
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name

class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='product_parameters', blank=True, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.CharField(max_length=250)


class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=10, verbose_name='Дом')
    structure = models.CharField(max_length=10, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=10, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=10, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    def __str__(self):
        return f'{self.city}{self.street}{self.house}'

class DeliveryMethod(models.Model):
    name = models.CharField(max_length=250, choices=DELIVERY_METHOD_CHOICES)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True)
    state = models.CharField(verbose_name='Статус', choices=STATE_CHOICES, max_length=15, null=True, blank=True)
    contact = models.ForeignKey(Contact, verbose_name='Адрес доставки', blank=True, null=True, on_delete=models.CASCADE)
    delivery_method = models.ForeignKey(DeliveryMethod, verbose_name='Способ доставки', blank=True, null=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='Заказы', related_name='order_items',
                              blank=True, on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте', related_name='order_items',
                                     blank=True, null=True, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Количество')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.product_info.model)

class ConfirmEmailToken(models.Model):
    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

        @staticmethod
        def generate_key():
            return get_token_generator().geneate_token()

        user = models.ForeignKey(User, related_name='Подтверждение токена электронной почты',
                                 on_delete=models.CASCADE,
                                 verbose_name='Пользователь, связанный с этим токеном сброса пароля')
        created_at = models.DateTimeField(auto_now_add=True, verbose_name='Когда был сгенерирован этот токен')
        key = models.CharField(
            _("Key"),
            max_length=64,
            db_index=True,
            unique=True
        )

        def save(self, *args, **kwargs):
            if not self.key:
                self.key = self.generate_key()
            return super(ConfirmEmailToken, self).save(*args, **kwargs)

        def __str__(self):
            return "Токен сброса пароля для пользователя {user}".format(user=self.user)





