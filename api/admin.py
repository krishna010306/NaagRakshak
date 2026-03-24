from django.contrib import admin

# Register your models here.
from .models import Hospital, EmergencyAlert

from .models import *

admin.site.register(User)
admin.site.register(Victim)
admin.site.register(AmbulanceDriver)
admin.site.register(Volunteer)
admin.site.register(Hospital)
admin.site.register(EmergencyAlert)