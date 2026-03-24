from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import EmergencyAlert, Hospital

# SOS API
@api_view(['POST'])
def sos(request):
    vehicle = request.data.get("vehicle")

    if vehicle == "yes":
        hospitals = Hospital.objects.all()[:3]

        data = []
        for h in hospitals:
            data.append({
                "name": h.name,
                "lat": h.latitude,
                "lng": h.longitude,
                "phone": h.phone
            })

        return Response({
            "type": "hospital",
            "hospitals": data
        })

    else:
        return Response({
            "type": "ambulance",
            "message": "Ambulance alerted",
            "phone": "108"
        })


# Get Hospitals API
@api_view(['GET'])
def get_hospitals(request):
    hospitals = Hospital.objects.all()

    data = []
    for h in hospitals:
        data.append({
            "name": h.name,
            "lat": h.latitude,
            "lng": h.longitude,
            "phone": h.phone
        })

    return Response(data)

@api_view(['POST'])
def send_alert(request):
    try:
        lat = float(request.data.get("lat"))
        lng = float(request.data.get("lng"))

        alert = EmergencyAlert.objects.create(
            patient_name=request.data.get("name", ""),
            latitude=lat,
            longitude=lng,
            snake_type=request.data.get("snake_type", "unknown")
        )

        return Response({"status": "success"})

    except Exception as e:
        return Response({"error": str(e)})

import math

@api_view(['POST'])
def nearest_hospital(request):
    user_lat = float(request.data.get("lat"))
    user_lng = float(request.data.get("lng"))

    hospitals = Hospital.objects.all()

    nearest = None
    min_distance = float('inf')

    for h in hospitals:
        distance = math.sqrt(
            (h.latitude - user_lat) ** 2 +
            (h.longitude - user_lng) ** 2
        )

        if distance < min_distance:
            min_distance = distance
            nearest = h

    if nearest:
        return Response({
            "name": nearest.name,
            "lat": nearest.latitude,
            "lng": nearest.longitude,
            "phone": nearest.phone,
            "distance": round(min_distance * 111, 2)  # approx km
        })

    return Response({"error": "No hospital found"})

import math
from .models import Hospital, AmbulanceDriver, Volunteer

@api_view(['POST'])
def smart_emergency(request):
    user_lat = float(request.data.get("lat"))
    user_lng = float(request.data.get("lng"))

    # 🔥 Step 1: Find nearest hospital
    hospitals = Hospital.objects.filter(has_antivenom=True)

    nearest_hospital = None
    min_dist = float('inf')

    for h in hospitals:
        dist = math.sqrt((h.latitude - user_lat)**2 + (h.longitude - user_lng)**2)

        if dist < min_dist:
            min_dist = dist
            nearest_hospital = h

    # convert to km approx
    hospital_distance = min_dist * 111

    # 🔥 If hospital is close (<10 km)
    if nearest_hospital and hospital_distance < 10:
        return Response({
            "type": "hospital",
            "name": nearest_hospital.name,
            "lat": nearest_hospital.latitude,
            "lng": nearest_hospital.longitude,
            "distance": round(hospital_distance, 2)
        })

    # 🔥 Step 2: Find ambulance
    drivers = AmbulanceDriver.objects.all()

    nearest_driver = None
    min_driver_dist = float('inf')

    for d in drivers:
        dist = math.sqrt((d.latitude - user_lat)**2 + (d.longitude - user_lng)**2)

        if dist < min_driver_dist:
            min_driver_dist = dist
            nearest_driver = d

    if nearest_driver:
        return Response({
            "type": "ambulance",
            "name": nearest_driver.user.name,
            "phone": nearest_driver.user.phone,
            "distance": round(min_driver_dist * 111, 2)
        })

    # 🔥 Step 3: Fallback → volunteers
    volunteers = Volunteer.objects.all()

    if volunteers.exists():
        v = volunteers.first()
        return Response({
            "type": "volunteer",
            "name": v.user.name,
            "phone": v.user.phone
        })

    return Response({"error": "No help available"})