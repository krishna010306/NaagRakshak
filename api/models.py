from django.db import models

# Create your models here.

from django.db import models

from django.db import models

# 🔥 COMMON USER MODEL
class User(models.Model):
    ROLE_CHOICES = [
        ('victim', 'Victim'),
        ('driver', 'Ambulance Driver'),
        ('volunteer', 'Volunteer'),
        ('hospital', 'Hospital'),
    ]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.role})"


# 🔥 VICTIM (basic)
class Victim(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


# 🔥 AMBULANCE DRIVER
class AmbulanceDriver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()


# 🔥 VOLUNTEER
class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()


# 🔥 HOSPITAL
class Hospital(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    has_antivenom = models.BooleanField(default=True)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name


# 🔥 EMERGENCY ALERT
class EmergencyAlert(models.Model):
    patient_name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert at {self.latitude}, {self.longitude}"
    
class Hospital(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    has_antivenom = models.BooleanField(default=True)  # 👈 ADD THIS
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name
    
class EmergencyAlert(models.Model):
    patient_name = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    snake_type = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert at {self.latitude}, {self.longitude}"