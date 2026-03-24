from urllib import request

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
    user_lat = request.data.get("lat")
    user_lng = request.data.get("lng")

    if user_lat is None or user_lng is None:
        return Response({"error": "Invalid data"})

    user_lat = float(user_lat)
    user_lng = float(user_lng)
    hospitals = Hospital.objects.all()

    if not hospitals.exists():
        return Response({"error": "No hospitals in database"})
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

@api_view(['POST'])
def smart_emergency(request):
    try:
        user_lat = request.data.get("lat")
        user_lng = request.data.get("lng")

        # ✅ check input
        if user_lat is None or user_lng is None:
            return Response({"error": "Invalid input"})

        user_lat = float(user_lat)
        user_lng = float(user_lng)

        # ✅ check hospitals
        hospitals = Hospital.objects.all()
        if not hospitals.exists():
            return Response({"error": "No hospitals in database"})

        # 🔥 find nearest hospital
        nearest = None
        min_dist = float('inf')

        for h in hospitals:
            dist = math.sqrt(
                (h.latitude - user_lat) ** 2 +
                (h.longitude - user_lng) ** 2
            )

            if dist < min_dist:
                min_dist = dist
                nearest = h

        hospital_distance = min_dist * 111

        # ✅ hospital case
        if nearest and hospital_distance < 10:
            return Response({
                "type": "hospital",
                "name": nearest.name,
                "lat": nearest.latitude,
                "lng": nearest.longitude,
                "distance": round(hospital_distance, 2)
            })

        # 🔥 ambulance fallback
        drivers = AmbulanceDriver.objects.all()
        if drivers.exists():
            d = drivers.first()
            return Response({
                "type": "ambulance",
                "name": d.user.name,
                "phone": d.user.phone
            })

        # 🔥 volunteer fallback
        volunteers = Volunteer.objects.all()
        if volunteers.exists():
            v = volunteers.first()
            return Response({
                "type": "volunteer",
                "name": v.user.name,
                "phone": v.user.phone
            })

        return Response({"error": "No help available"})

    except Exception as e:
        return Response({"error": str(e)})