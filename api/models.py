from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
        ("victim", "Victim"),
        ("driver", "Ambulance Driver"),
        ("volunteer", "Volunteer"),
        ("hospital", "Hospital"),
    ]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Victim(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class AmbulanceDriver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"Driver: {self.user.name}"


class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"Volunteer: {self.user.name}"


class Hospital(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    has_antivenom = models.BooleanField(default=True)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name


class EmergencyAlert(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("hospital_routed", "Hospital Routed"),
        ("ambulance_notified", "Ambulance Notified"),
        ("ambulance_accepted", "Ambulance Accepted"),
        ("volunteer_notified", "Volunteer Notified"),
        ("completed", "Completed"),
    ]

    patient_name = models.CharField(max_length=100, blank=True)
    patient_phone = models.CharField(max_length=15, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    snake_type = models.CharField(max_length=100, blank=True)
    has_vehicle = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    assigned_hospital = models.ForeignKey(Hospital, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_driver = models.ForeignKey(AmbulanceDriver, null=True, blank=True, on_delete=models.SET_NULL)
    assigned_volunteer = models.ForeignKey(Volunteer, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert #{self.id} ({self.status})"