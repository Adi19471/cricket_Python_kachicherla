import razorpay
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import TimeSlot, Booking, UserProfile
from django.utils.dateparse import parse_date
import json

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

from .forms import CustomUserCreationForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user, defaults={'phone_number': form.cleaned_data['phone_number'], 'amount': 0})
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    slots = TimeSlot.objects.all()
    today = request.GET.get('today', None)
    return render(request, "index.html", {"slots": slots, "today": today})

@require_http_methods(["GET"])
@login_required
def api_booked_slots(request, date_str):
    date = parse_date(date_str)
    if not date:
        return JsonResponse({'error': 'Invalid date'}, status=400)
    
    booked_qs = Booking.objects.filter(
        date=date, 
        is_paid=True
    ).values_list('slots__id', flat=True)
    booked_slots = list(set(booked_qs))
    return JsonResponse({'booked_slots': booked_slots})

@login_required
def book_slot(request):
    if request.method == "POST":
        date = request.POST.get("date")
        if not date:
            return JsonResponse({'error': 'Date is required'}, status=400)
        slot_ids = request.POST.get("slots", "").split(",")
        slot_ids = [sid for sid in slot_ids if sid.isdigit()]
        
        # Check availability
        booked_on_date = set(Booking.objects.filter(
            date=date, is_paid=True
        ).values_list('slots__id', flat=True))
        
        available_slots = [sid for sid in slot_ids if sid not in booked_on_date]
        if len(available_slots) != len(slot_ids):
            return JsonResponse({'error': 'Some slots already booked'}, status=400)
        
        total_amount = len(available_slots) * 500
        
        booking = Booking.objects.create(
            user=request.user,
            date=date,
            amount=500,
            total_amount=total_amount
        )
        for slot_id in available_slots:
            booking.slots.add(slot_id)
        booking.save()
        
        order = client.order.create({
            'amount': int(total_amount * 100),
            'currency': 'INR',
        })
        booking.razorpay_order_id = order['id']
        booking.save()
        
        return JsonResponse({
            'success': True,
            'order_id': order['id'],
            'amount': total_amount,
            'key': settings.RAZORPAY_KEY_ID,
            'booking_id': booking.id
        })
    
    return redirect("home")

@csrf_exempt
@login_required
def payment_success(request):
    if request.method == "POST":
        import razorpay
        order_id = request.POST.get("razorpay_order_id")
        payment_id = request.POST.get("razorpay_payment_id")
        signature = request.POST.get("razorpay_signature")
        
        booking = Booking.objects.get(razorpay_order_id=order_id)
        
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            booking.is_paid = True
            booking.save()
            return JsonResponse({'success': True})
        except Exception:
            return JsonResponse({'success': False, 'error': 'Verification failed'})
    
    return JsonResponse({'success': False})

from django.utils import timezone

@login_required
def history(request):
    from django.utils import timezone
    search_date_str = request.GET.get('date')
    bookings = Booking.objects.filter(user=request.user)
    if search_date_str:
        search_date = parse_date(search_date_str)
        if search_date:
            bookings = bookings.filter(date=search_date)
    today = timezone.now().date()
    return render(request, "history.html", {"bookings": bookings, "search_date": search_date_str, "today": today})
