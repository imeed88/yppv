from django.db import models 
from django.contrib.auth.models import User



class equipment(models.Model):
    inventorynr = models.IntegerField()
    nomenclature = models.CharField(max_length=250, blank=True)
    modelnumber = models.CharField(max_length=200, blank=True)
    manufactserialnr = models.CharField(max_length=200, blank=True)
    inventoryref =  models.CharField(max_length=25, blank=True)
    functlocation = models.JSONField(blank=True, null=True)
    def __str__(self):
        return str(self.inventorynr)



class order(models.Model):
    docinfo = models.CharField(max_length=100, blank=True)
    status = models.BooleanField(default=False)
    issuer = models.CharField(max_length=200, blank=True)
    orderref = models.IntegerField()
    personorderd = models.IntegerField(default=0)
    grouporderd = models.IntegerField(default=0)
    week = models.IntegerField(default=0)
    ordertype = models.CharField(max_length=100, blank=True)
    startdate = models.DateField(null=True, blank=True)
    enddate = models.DateField(null=True, blank=True)
    submitdate = models.DateField(null=True, blank=True)
    equipment = models.ForeignKey(equipment, on_delete=models.CASCADE)
    plannedtime = models.CharField(max_length=25, blank=True)
    pmplannergrp = models.CharField(max_length=25, blank=True)
    inspectionlot = models.CharField(max_length=10, blank=True)
    instructions = models.JSONField(blank=True, null=True)
    extension = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.docinfo

 

class group(models.Model):
    groupid = models.CharField(max_length=25, blank=True)
    description = models.TextField(max_length=800, blank=True)
    def __str__(self):
        return self.groupid






class userprofile(models.Model):
    user =models.OneToOneField(User, on_delete=models.CASCADE)
    is_issuer = models.BooleanField(default=False)
    fname = models.CharField(max_length=100, blank=True)
    lname = models.CharField(max_length=100, blank=True)
    group = models.JSONField(blank=True, null=True)


    def __str__(self):
        return self.user.username