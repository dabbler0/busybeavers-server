from django.db import models

# Create your models here.
class ApprovalRecord(models.Model):
    kerberos = models.CharField(max_length=64)
    discord_server = models.IntegerField()
    discord_id = models.IntegerField()
    discord_name = models.CharField(max_length=64)
    token = models.CharField(max_length=64)
    approved = models.BooleanField()
    approval_received = models.BooleanField()
    timestamp = models.DateField()

class ClassException(models.Model):
    kerberos = models.CharField(max_length=64)
    manual_year = models.CharField(max_length=1)
