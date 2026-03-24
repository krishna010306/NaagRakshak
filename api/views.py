import math

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AmbulanceDriver, EmergencyAlert, Hospital, User, Volunteer


FIRST_AID_STEPS = [
    "Keep the patient calm and still.",
    "Remove rings, bangles, and tight clothing near bite area.",
    "Do not cut, suck, or apply ice on the bite.",
    "Keep bitten limb below heart level and avoid walking.",
    "Reach anti-venom capable hospital immediately.",
]


def _serialize_user(user):
    return {
        "id": user.id,
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
    }


@api_view(["POST"])
def login_user(request):
    """Simple hackathon login: find user by phone, create victim profile if missing."""
    phone = str(
        request.data.get("phone")
        or request.data.get("mobile")
        or request.data.get("username")
        or ""
    ).strip()
    name = str(request.data.get("name") or request.data.get("full_name") or "").strip()
    role = str(request.data.get("role") or "victim").strip().lower()

    if not phone:
        return Response(
            {
                "status": "error",
                "message": "phone is required",
                "next_screen": "login",
                "user": None,
            }
        )

    valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
    if role not in valid_roles:
        role = "victim"

    user = User.objects.filter(phone=phone).first()
    is_new_user = False

    if not user:
        user = User.objects.create(
            name=name or "User",
            phone=phone,
            role=role,
        )
        is_new_user = True
    else:
        update_fields = []
        if name and user.name != name:
            user.name = name
            update_fields.append("name")
        if role and user.role != role:
            user.role = role
            update_fields.append("role")
        if update_fields:
            user.save(update_fields=update_fields)

    return Response(
        {
            "status": "success",
            "message": "Login successful",
            "is_new_user": is_new_user,
            "next_screen": "sos",
            "role": user.role,
            "user": _serialize_user(user),
        }
    )


@api_view(["POST"])
def register_user(request):
    """Create or update a user profile from signup flow."""
    phone = str(request.data.get("phone") or "").strip()
    name = str(request.data.get("name") or "User").strip() or "User"
    role = str(request.data.get("role") or "victim").strip().lower()

    if not phone:
        return Response({"error": "phone is required"}, status=400)

    valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
    if role not in valid_roles:
        role = "victim"

    user, created = User.objects.update_or_create(
        phone=phone,
        defaults={"name": name, "role": role},
    )

    return Response(
        {
            "status": "success",
            "created": created,
            "role": user.role,
            "user": _serialize_user(user),
        },
        status=201 if created else 200,
    )


@api_view(["POST"])
def role_lookup(request):
    """Compatibility endpoint for app login-role/user-role/role routes."""
    phone = str(request.data.get("phone") or "").strip()
    if not phone:
        return Response({"error": "phone is required"}, status=400)

    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({"message": "User not found"}, status=404)

    return Response({"status": "success", "role": user.role, "user": _serialize_user(user)})


@api_view(["GET", "POST"])
def users_endpoint(request):
    """Compatibility endpoint for /api/users/ and /api/user/by-phone/."""
    if request.method == "POST":
        return register_user(request)

    phone = str(request.query_params.get("phone") or "").strip()
    queryset = User.objects.all()
    if phone:
        queryset = queryset.filter(phone=phone)

    data = [_serialize_user(user) for user in queryset.order_by("-id")[:50]]
    return Response(data)


def _to_float(value, name):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {name}")


def _parse_vehicle(value):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"yes", "y", "true", "1"}:
        return True
    if normalized in {"no", "n", "false", "0"}:
        return False
    return None


def _distance_km(lat1, lon1, lat2, lon2):
    lat_diff = lat1 - lat2
    lon_diff = lon1 - lon2
    return math.sqrt((lat_diff ** 2) + (lon_diff ** 2)) * 111


def _nearest_hospital(user_lat, user_lng, antivenom_only=True):
    hospitals = Hospital.objects.filter(has_antivenom=True) if antivenom_only else Hospital.objects.all()
    nearest = None
    min_distance = float("inf")

    for hospital in hospitals:
        distance = _distance_km(user_lat, user_lng, hospital.latitude, hospital.longitude)
        if distance < min_distance:
            min_distance = distance
            nearest = hospital

    if nearest:
        return nearest, round(min_distance, 2)
    return None, None


def _nearest_driver(user_lat, user_lng):
    nearest = None
    min_distance = float("inf")

    for driver in AmbulanceDriver.objects.select_related("user").all():
        distance = _distance_km(user_lat, user_lng, driver.latitude, driver.longitude)
        if distance < min_distance:
            min_distance = distance
            nearest = driver

    if nearest:
        return nearest, round(min_distance, 2)
    return None, None


def _nearest_volunteer(user_lat, user_lng):
    nearest = None
    min_distance = float("inf")

    for volunteer in Volunteer.objects.select_related("user").all():
        distance = _distance_km(user_lat, user_lng, volunteer.latitude, volunteer.longitude)
        if distance < min_distance:
            min_distance = distance
            nearest = volunteer

    if nearest:
        return nearest, round(min_distance, 2)
    return None, None


def _sos_decision(payload):
    user_lat = _to_float(payload.get("lat"), "lat")
    user_lng = _to_float(payload.get("lng"), "lng")
    has_vehicle = _parse_vehicle(payload.get("vehicle"))

    if has_vehicle is None:
        raise ValueError("vehicle must be yes/no or true/false")

    nearest_hospital, hospital_distance = _nearest_hospital(user_lat, user_lng, antivenom_only=True)
    if not nearest_hospital:
        nearest_hospital, hospital_distance = _nearest_hospital(user_lat, user_lng, antivenom_only=False)

    alert = EmergencyAlert.objects.create(
        patient_name=payload.get("name", ""),
        patient_phone=payload.get("phone", ""),
        latitude=user_lat,
        longitude=user_lng,
        snake_type=payload.get("snake_type", ""),
        has_vehicle=has_vehicle,
        assigned_hospital=nearest_hospital,
    )

    if has_vehicle:
        alert.status = "hospital_routed"
        alert.save(update_fields=["status"])
        hospital_data = None
        if nearest_hospital:
            hospital_data = {
                "id": nearest_hospital.id,
                "name": nearest_hospital.name,
                "lat": nearest_hospital.latitude,
                "lng": nearest_hospital.longitude,
                "phone": nearest_hospital.phone,
                "distance_km": hospital_distance,
                "has_antivenom": nearest_hospital.has_antivenom,
            }

        return {
            "alert_id": alert.id,
            "route": "self_transport",
            "first_aid": FIRST_AID_STEPS,
            "hospital_alerted": bool(nearest_hospital),
            "hospital": hospital_data,
            "message": "Proceed to nearest anti-venom hospital using navigation.",
        }

    nearest_driver, driver_distance = _nearest_driver(user_lat, user_lng)
    if nearest_driver:
        alert.status = "ambulance_notified"
        alert.assigned_driver = nearest_driver
        alert.save(update_fields=["status", "assigned_driver"])
        return {
            "alert_id": alert.id,
            "route": "ambulance",
            "first_aid": FIRST_AID_STEPS,
            "hospital_alerted": bool(nearest_hospital),
            "hospital": {
                "id": nearest_hospital.id,
                "name": nearest_hospital.name,
                "phone": nearest_hospital.phone,
            }
            if nearest_hospital
            else None,
            "ambulance_driver": {
                "id": nearest_driver.id,
                "name": nearest_driver.user.name,
                "phone": nearest_driver.user.phone,
                "distance_km": driver_distance,
            },
            "wait_time_minutes": 15,
            "message": "Ambulance alerted. If not accepted soon, volunteer backup will be used.",
        }

    nearest_volunteer, volunteer_distance = _nearest_volunteer(user_lat, user_lng)
    if nearest_volunteer:
        alert.status = "volunteer_notified"
        alert.assigned_volunteer = nearest_volunteer
        alert.save(update_fields=["status", "assigned_volunteer"])
        return {
            "alert_id": alert.id,
            "route": "volunteer",
            "first_aid": FIRST_AID_STEPS,
            "hospital_alerted": bool(nearest_hospital),
            "hospital": {
                "id": nearest_hospital.id,
                "name": nearest_hospital.name,
                "phone": nearest_hospital.phone,
            }
            if nearest_hospital
            else None,
            "volunteer": {
                "id": nearest_volunteer.id,
                "name": nearest_volunteer.user.name,
                "phone": nearest_volunteer.user.phone,
                "distance_km": volunteer_distance,
            },
            "message": "Volunteer backup alerted due to ambulance unavailability.",
        }

    return {
        "alert_id": alert.id,
        "route": "hospital_only",
        "first_aid": FIRST_AID_STEPS,
        "hospital_alerted": bool(nearest_hospital),
        "hospital": {
            "id": nearest_hospital.id,
            "name": nearest_hospital.name,
            "phone": nearest_hospital.phone,
            "distance_km": hospital_distance,
        }
        if nearest_hospital
        else None,
        "message": "No ambulance/volunteer available right now. Move toward nearest hospital.",
    }


@api_view(["POST"])
def sos(request):
    try:
        return Response(_sos_decision(request.data))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    except Exception as exc:
        return Response({"error": f"Unexpected error: {exc}"}, status=500)


@api_view(["GET"])
def get_hospitals(request):
    hospitals = Hospital.objects.all()
    return Response(
        [
            {
                "id": h.id,
                "name": h.name,
                "lat": h.latitude,
                "lng": h.longitude,
                "phone": h.phone,
                "has_antivenom": h.has_antivenom,
            }
            for h in hospitals
        ]
    )


@api_view(["POST"])
def send_alert(request):
    try:
        payload = {
            "name": request.data.get("name", ""),
            "phone": request.data.get("phone", ""),
            "lat": request.data.get("lat"),
            "lng": request.data.get("lng"),
            "snake_type": request.data.get("snake_type", ""),
            "vehicle": request.data.get("vehicle", "no"),
        }
        result = _sos_decision(payload)
        return Response({"status": "success", **result})
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    except Exception as exc:
        return Response({"error": str(exc)}, status=500)


@api_view(["POST"])
def nearest_hospital(request):
    try:
        user_lat = _to_float(request.data.get("lat"), "lat")
        user_lng = _to_float(request.data.get("lng"), "lng")
        nearest, distance = _nearest_hospital(user_lat, user_lng, antivenom_only=True)
        if not nearest:
            nearest, distance = _nearest_hospital(user_lat, user_lng, antivenom_only=False)

        if not nearest:
            return Response({"error": "No hospital found"}, status=404)

        return Response(
            {
                "id": nearest.id,
                "name": nearest.name,
                "lat": nearest.latitude,
                "lng": nearest.longitude,
                "phone": nearest.phone,
                "distance_km": distance,
                "has_antivenom": nearest.has_antivenom,
            }
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)


@api_view(["POST"])
def smart_emergency(request):
    data = request.data.copy()

    # App may send need_ambulance without explicit vehicle flag.
    if data.get("vehicle") in (None, "") and data.get("need_ambulance"):
        data["vehicle"] = "no"

    # If volunteer escalation is requested for an existing alert, handle directly.
    if data.get("need_volunteer"):
        alert_id = data.get("id")
        try:
            alert = EmergencyAlert.objects.get(id=alert_id)
        except EmergencyAlert.DoesNotExist:
            return Response({"error": "Alert not found"}, status=404)

        nearest_volunteer, distance = _nearest_volunteer(alert.latitude, alert.longitude)
        if not nearest_volunteer:
            return Response({"message": "No volunteer available"}, status=404)

        alert.assigned_volunteer = nearest_volunteer
        alert.status = "volunteer_notified"
        alert.save(update_fields=["assigned_volunteer", "status"])
        return Response(
            {
                "status": "success",
                "type": "volunteer",
                "alert_id": alert.id,
                "volunteer": {
                    "id": nearest_volunteer.id,
                    "name": nearest_volunteer.user.name,
                    "phone": nearest_volunteer.user.phone,
                    "distance_km": distance,
                },
            }
        )

    try:
        return Response(_sos_decision(data))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    except Exception as exc:
        return Response({"error": f"Unexpected error: {exc}"}, status=500)


@api_view(["GET"])
def get_driver_requests(request):
    driver_id = request.query_params.get("driver_id")
    driver_phone = request.query_params.get("phone")
    alerts = EmergencyAlert.objects.filter(status="ambulance_notified")

    if driver_phone and not driver_id:
        driver = AmbulanceDriver.objects.select_related("user").filter(user__phone=driver_phone).first()
        if driver:
            driver_id = driver.id

    if driver_id:
        alerts = alerts.filter(assigned_driver_id=driver_id)

    alert = alerts.order_by("-timestamp").first()
    if not alert:
        return Response({"message": "No requests"})

    return Response(
        {
            "id": alert.id,
            "name": alert.patient_name,
            "phone": alert.patient_phone,
            "victim_phone": alert.patient_phone,
            "lat": alert.latitude,
            "lng": alert.longitude,
            "hospital": {
                "name": alert.assigned_hospital.name,
                "phone": alert.assigned_hospital.phone,
            }
            if alert.assigned_hospital
            else None,
        }
    )


@api_view(["GET", "POST"])
def ambulance_requests(request):
    """Compatibility endpoint for app ambulance dispatch + polling."""
    if request.method == "POST":
        data = request.data.copy()
        if data.get("vehicle") in (None, ""):
            data["vehicle"] = "no"
        data.setdefault("phone", data.get("victim_phone", ""))
        data.setdefault("name", data.get("victim_name", "User"))
        data.setdefault("snake_type", data.get("request_type", "unknown"))

        try:
            result = _sos_decision(data)
            return Response({"status": "success", **result})
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except Exception as exc:
            return Response({"error": str(exc)}, status=500)

    return get_driver_requests(request)


@api_view(["POST"])
def accept_request(request):
    alert_id = request.data.get("id")
    accepted = request.data.get("accepted", True)

    if isinstance(accepted, str):
        accepted = accepted.strip().lower() in {"yes", "true", "1"}

    try:
        alert = EmergencyAlert.objects.select_related("assigned_hospital", "assigned_driver__user").get(id=alert_id)
    except EmergencyAlert.DoesNotExist:
        return Response({"error": "Alert not found"}, status=404)

    if accepted:
        alert.status = "ambulance_accepted"
        alert.save(update_fields=["status"])
        return Response(
            {
                "message": "Accepted",
                "alert_id": alert.id,
                "patient": {
                    "name": alert.patient_name,
                    "phone": alert.patient_phone,
                    "lat": alert.latitude,
                    "lng": alert.longitude,
                },
                "hospital": {
                    "name": alert.assigned_hospital.name,
                    "phone": alert.assigned_hospital.phone,
                }
                if alert.assigned_hospital
                else None,
            }
        )

    nearest_volunteer, _ = _nearest_volunteer(alert.latitude, alert.longitude)
    if nearest_volunteer:
        alert.assigned_volunteer = nearest_volunteer
        alert.status = "volunteer_notified"
        alert.save(update_fields=["assigned_volunteer", "status"])
        return Response(
            {
                "message": "Driver declined. Volunteer alerted.",
                "volunteer": {
                    "id": nearest_volunteer.id,
                    "name": nearest_volunteer.user.name,
                    "phone": nearest_volunteer.user.phone,
                },
            }
        )

    alert.status = "pending"
    alert.save(update_fields=["status"])
    return Response({"message": "Driver declined and no volunteer available"})


@api_view(["GET"])
def volunteer_requests(request):
    volunteer_id = request.query_params.get("volunteer_id")
    alerts = EmergencyAlert.objects.filter(status="volunteer_notified")
    if volunteer_id:
        alerts = alerts.filter(assigned_volunteer_id=volunteer_id)

    alert = alerts.order_by("-timestamp").first()
    if not alert:
        return Response({"message": "No requests"})

    return Response(
        {
            "id": alert.id,
            "name": alert.patient_name,
            "phone": alert.patient_phone,
            "lat": alert.latitude,
            "lng": alert.longitude,
        }
    )


@api_view(["GET"])
def hospital_alerts(request):
    statuses = ["hospital_routed", "ambulance_notified", "ambulance_accepted", "volunteer_notified"]
    alerts = (
        EmergencyAlert.objects.filter(status__in=statuses, assigned_hospital__isnull=False)
        .select_related("assigned_hospital")
        .order_by("-timestamp")[:10]
    )

    if not alerts:
        return Response({"message": "No alerts"})

    return Response(
        [
            {
                "alert_id": alert.id,
                "status": alert.status,
                "patient_name": alert.patient_name,
                "patient_phone": alert.patient_phone,
                "lat": alert.latitude,
                "lng": alert.longitude,
                "hospital": {
                    "name": alert.assigned_hospital.name,
                    "phone": alert.assigned_hospital.phone,
                },
            }
            for alert in alerts
        ]
    )