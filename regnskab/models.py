import collections
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from regnskab import config
from tkweb.apps.idm.models import (
    tk_prefix, parse_bestfu_alias,
)


class Profile(models.Model):
    name = models.CharField(max_length=50, verbose_name="Navn")
    email = models.EmailField(max_length=50, blank=True,
                              verbose_name="Emailadresse")

    class Meta:
        ordering = ['name']
        verbose_name = 'person'
        verbose_name_plural = verbose_name + 'er'

    def __str__(self):
        return str(self.name)


class SheetStatus(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)

    def since(self):
        if self.end_time:
            return 'ikke siden %s' % (self.end_time.date(),)
        else:
            return 'siden %s' % (self.start_time.date(),)


class Title(models.Model):
    BEST, FU, EFU = 'BEST', 'FU', 'EFU'
    KIND = [(BEST, 'BEST'), (FU, 'FU'), (EFU, 'EFU')]

    profile = models.ForeignKey('Profile')
    period = models.IntegerField(verbose_name='Årgang')
    root = models.CharField(max_length=10, verbose_name='Titel')
    kind = models.CharField(max_length=10, choices=KIND, verbose_name='Slags')

    def age(self, gfyear=None):
        if gfyear is None:
            gfyear = config.GFYEAR
        return gfyear - self.period

    def display_root(self):
        return self.root.replace('KASS', 'KA$$')

    def display_title(self, gfyear=None):
        return '%s%s' % (tk_prefix(self.age(gfyear)), self.display_root())

    def input_title(self, gfyear=None):
        # The title as it would be typed
        return '%s%s' % (tk_prefix(self.age(gfyear), sup_fn=str), self.root)

    def display_title_and_year(self, gfyear=None):
        return '%s (%02d/%02d)' % (self.display_title(gfyear),
                                   self.period % 100, (self.period+1) % 100)

    def ascii_root(self):
        tr = {197: 'AA', 198: 'AE', 216: 'OE', 229: 'aa', 230: 'ae', 248: 'oe'}
        return self.root.translate(tr)

    def email_local_part(self, gfyear=None):
        return '%s%s' % (tk_prefix(self.age(gfyear), sup_fn=str),
                         self.ascii_root())

    @classmethod
    def parse(cls, title, gfyear, **kwargs):
        kind, root, period = parse_bestfu_alias(title, gfyear)
        return cls(period=period, root=root, kind=kind, **kwargs)

    class Meta:
        ordering = ['-period', 'kind', 'root']
        verbose_name = 'titel'
        verbose_name_plural = 'titler'

    def __str__(self):
        return '%s %s' % (self.display_title(), getattr(self, 'profile', ''))


class Alias(models.Model):
    profile = models.ForeignKey(Profile)
    period = models.IntegerField(blank=True, null=True, verbose_name='Årgang')
    root = models.CharField(max_length=10, verbose_name='Titel')
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)

    def age(self, gfyear=None):
        if gfyear is None:
            gfyear = config.GFYEAR
        return gfyear - self.period

    def display_root(self):
        return self.root

    def display_title(self, gfyear=None):
        return '%s%s' % (tk_prefix(self.age(gfyear)), self.display_root())

    def input_title(self, gfyear=None):
        # The title as it would be typed
        if self.period is None:
            return self.root
        return '%s%s' % (tk_prefix(self.age(gfyear), sup_fn=str), self.root)

    class Meta:
        ordering = ['period', 'root']
        verbose_name = 'alias'
        verbose_name_plural = verbose_name + 'er'

    def __str__(self):
        return self.display_title()


class Payment(models.Model):
    profile = models.ForeignKey(Profile)
    time = models.DateTimeField()
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%.2f kr.' % self.amount


class Sheet(models.Model):
    name = models.CharField(max_length=200, blank=True,
                            help_text='f.eks. HSTR, revy, matlabotanisk have')
    start_date = models.DateField()
    end_date = models.DateField()
    period = models.IntegerField(verbose_name='Årgang')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)

    def rows(self):
        r = []
        kinds = list(self.purchasekind_set.all())
        for row in self.sheetrow_set.all():
            purchases = {
                p.kind_id: p
                for p in row.purchase_set.all()
            }
            purchase_list = [
                purchases.get(kind.id, Purchase(row=row, kind=kind, count=0))
                for kind in kinds
            ]
            for p in purchase_list:
                if p.count % 1 == 0:
                    p.counter = range(int(p.count))
                else:
                    p.counter = None
            r.append(dict(
                profile=row.profile,
                position=row.position,
                name=row.name,
                kinds=purchase_list,
            ))
        return r

    class Meta:
        ordering = ['start_date']
        verbose_name = 'krydsliste'
        verbose_name_plural = verbose_name + 'r'

    def __str__(self):
        s = '%s %s-%s' % (self.name, self.start_date, self.end_date)
        return s.strip()


class PurchaseKind(models.Model):
    sheet = models.ForeignKey(Sheet)
    position = models.PositiveIntegerField()
    name = models.CharField(max_length=200,
                            help_text='f.eks. guldøl, guldølskasser')
    price = models.DecimalField(max_digits=12, decimal_places=2,
                                help_text='f.eks. 8, 10, 13, 200, 250')

    class Meta:
        ordering = ['sheet', 'position']
        verbose_name = 'prisklasse'
        verbose_name_plural = verbose_name + 'r'

    def __str__(self):
        return str(self.name)


class SheetRow(models.Model):
    sheet = models.ForeignKey(Sheet)
    position = models.PositiveIntegerField()
    name = models.CharField(max_length=200, blank=False, null=True)
    profile = models.ForeignKey(Profile, blank=False, null=True)

    class Meta:
        ordering = ['sheet', 'position']
        verbose_name = 'krydslisteindgang'
        verbose_name_plural = verbose_name + 'e'

    def __str__(self):
        return self.name or str(self.profile)


class Purchase(models.Model):
    row = models.ForeignKey(SheetRow)
    kind = models.ForeignKey(PurchaseKind)
    count = models.DecimalField(max_digits=9, decimal_places=4,
                                help_text='antal krydser eller brøkdel')

    def __str__(self):
        return '%g× %s' % (self.count, self.kind)

    class Meta:
        ordering = ['row', 'kind']
        verbose_name = 'krydser'
        verbose_name_plural = verbose_name


def compute_balance():
    balance = collections.defaultdict(Decimal)
    purchase_qs = Purchase.objects.all()
    purchase_qs = purchase_qs.annotate(profile_id=F('row__profile_id'))
    purchase_qs = purchase_qs.annotate(amount=F('count') * F('kind__price'))
    purchase_qs = purchase_qs.values_list('profile_id', 'amount')
    for profile, amount in purchase_qs:
        balance[profile] += amount
    payment_qs = Payment.objects.all()
    payment_qs = payment_qs.values_list('profile_id', 'amount')
    for profile, amount in payment_qs:
        balance[profile] -= amount
    return balance


class EmailTemplate(models.Model):
    POUND = 'pound'
    FORMAT = [(POUND, 'pound')]

    name = models.CharField(max_length=255, blank=True)
    subject = models.TextField(blank=False)
    body = models.TextField(blank=False)
    format = models.CharField(max_length=10, choices=FORMAT)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or str(self.created_time)


class EmailBatch(models.Model):
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL,
                                 null=True, blank=False)
    send_time = models.DateTimeField(null=True, blank=True)
    sheet_set = models.ManyToManyField(Sheet, blank=True,
                                       verbose_name='krydslister')
    payment_set = models.ManyToManyField(Payment, blank=True,
                                         verbose_name='betalinger')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=False)
    created_time = models.DateTimeField(auto_now_add=True)

    @property
    def sent(self):
        return bool(self.send_time)

    def regenerate_emails(self):
        if self.template is None:
            raise ValidationError("template required to generate emails")
        payments = self.payment_set.all()
        sheets = self.sheet_set.all()
        # TODO


class Email(models.Model):
    batch = models.ForeignKey(EmailBatch, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL,
                                null=True, blank=False, related_name='+')
    subject = models.TextField(blank=False)
    body = models.TextField(blank=False)
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.CharField(max_length=255)

    def __str__(self):
        return '%s <%s>' % (self.recipient_name, self.recipient_email)
