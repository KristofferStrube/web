from django.db import models
import subprocess
from django.core.files.storage import FileSystemStorage
from django.core.files import File


class Drink(models.Model):
    name = models.CharField(max_length=30)
    serving = models.CharField(max_length=50)
    soda = models.CharField(max_length=50)
    price = models.IntegerField()

    def __str__(self):
        return self.name

class Sprut(models.Model):
    drink = models.ForeignKey(Drink, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    amount = models.IntegerField()

    def __str__(self):
        return self.name

class Barcard(models.Model):
    name = models.CharField(max_length=30)
    drinks = models.ManyToManyField(Drink)
    barcardFile = models.FileField(blank=True, upload_to='barcard') 
    mixingFile = models.FileField(blank=True, upload_to='mixing') 
    
    def __str__(self):
        return self.name

    def generateFiles(self):
        # todo: function for converting model to drinks.txt
        # and overwrite  drinkskort/drinks.txt
        bashCommand = 'make -C tkweb/apps/drinks/drinkskort/'
        subprocess.call(bashCommand, shell=True)
        
        barFile = open('tkweb/apps/drinks/drinkskort/bar_drinks.pdf', mode='rb')
        mixFile = open('tkweb/apps/drinks/drinkskort/mixing_drinks.pdf', mode='rb' )
        self.barcardFile.save(self.name+'_barcard',File(barFile))
        self.mixingFile.save(self.name+'_mixing',File(mixFile))
