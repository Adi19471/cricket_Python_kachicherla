import razorpay
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib import messages
from .models import TimeSlot, Booking, UserProfile
from .forms import CustomUserCreationForm
import json
from datetime import datetime, timedelta

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ==================== AUTHENTICATION VIEWS ====================

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(
                user=user, 
                defaults={
                    'phone_number': form.cleaned_data['phone_number'], 
                    'amount': 0
                }
            )
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully')
    return redirect('login')

@login_required
def home(request):
    slots = TimeSlot.objects.all()
    today = timezone.now().date()
    return render(request, "index.html", {"slots": slots, "today": today})

# ==================== API ENDPOINTS ====================

@require_http_methods(["GET"])
@login_required
def api_booked_slots(request, date_str):
    """Get booked and blocked slots for a specific date"""
    date = parse_date(date_str)
    if not date:
        return JsonResponse({'error': 'Invalid date'}, status=400)
    
    # Get booked slots (paid and confirmed/completed)
    booked_qs = Booking.objects.filter(
        date=date, 
        is_paid=True,
        status__in=['confirmed', 'completed']
    ).values_list('slots__id', flat=True)
    booked_slots = list(set(booked_qs))
    
    # CRITICAL FIX: Also block slots that have pending bookings to prevent duplicate bookings
    pending_booked_qs = Booking.objects.filter(
        date=date,
        status='pending',
        is_paid=False
    ).values_list('slots__id', flat=True)
    pending_booked_slots = list(set(pending_booked_qs))
    
    # Combine all blocked slots (paid + pending)
    all_blocked_slots = list(set(booked_slots + pending_booked_slots))
    
    # Get cancelled/pending bookings to block
    cancelled_qs = Booking.objects.filter(
        date=date,
        status='cancelled'
    ).values_list('slots__id', flat=True)
    
    # Get confirmed/completed bookings
    completed_booking_exists = Booking.objects.filter(
        date=date, 
        status__in=['confirmed', 'completed']
    ).exists()
    
    blocked_empty_slots = []
    if completed_booking_exists:
        completed_booking_slots = set(Booking.objects.filter(
            date=date,
            status__in=['confirmed', 'completed']
        ).values_list('slots__id', flat=True))
        
        all_slots = set(TimeSlot.objects.values_list('id', flat=True))
        blocked_empty_slots = list(all_slots - completed_booking_slots)
    
    return JsonResponse({
        'booked_slots': all_blocked_slots,  # Now includes pending bookings
        'blocked_empty_slots': blocked_empty_slots,
        'cancelled_slots': list(cancelled_qs),
        'pending_booked_slots': pending_booked_slots  # Also send this for debugging
    })

# ==================== BOOKING VIEWS ====================

@login_required
@require_http_methods(["GET", "POST"])
def book_slot(request):
    """Create a new booking with custom amount"""
    if request.method == "GET":
        date = request.GET.get("date")
        slot_ids = request.GET.getlist("slots")
        return render(request, "book_slot.html", {
            "date": date,
            "slot_ids": slot_ids,
            "slots": TimeSlot.objects.filter(id__in=slot_ids)
        })
    
    elif request.method == "POST":
        try:
            date = request.POST.get("date")
            if not date:
                return JsonResponse({'error': 'Date is required'}, status=400)
            
            slot_ids = request.POST.get("slots", "").split(",")
            slot_ids = [sid for sid in slot_ids if sid.isdigit()]
            
            if not slot_ids:
                return JsonResponse({'error': 'No slots selected'}, status=400)
            
# Get custom amount from form or use slot-specific amount
            custom_amount = request.POST.get("custom_amount")
            
            # Always fetch the slots first
            slots = TimeSlot.objects.filter(id__in=slot_ids)
            
            # Default price per slot if no custom amount specified
            DEFAULT_PRICE = 250
            
# Check slot availability first - NOW also checks for pending bookings (not just paid ones)
            available_slots = []
            conflicting_slots = []
            
            for slot_id in slot_ids:
                # Check for PAID + Confirmed/Completed bookings
                existing_paid_booking = Booking.objects.filter(
                    date=date,
                    slots__id=slot_id,
                    is_paid=True,
                    status__in=['confirmed', 'completed']
                ).exists()
                
                # CRITICAL FIX: Also check for ANY pending booking (unpaid)
                existing_pending_booking = Booking.objects.filter(
                    date=date,
                    slots__id=slot_id,
                    status='pending',
                    is_paid=False
                ).exists()
                
                if not existing_paid_booking and not existing_pending_booking:
                    available_slots.append(slot_id)
                else:
                    conflicting_slots.append(slot_id)
            
            if len(available_slots) != len(slot_ids):
                # Provide more specific error message
                if conflicting_slots:
                    return JsonResponse({
                        'error': f'Some slots are already booked or have pending bookings. Please select different slots.'
                    }, status=400)
                else:
                    return JsonResponse({
                        'error': f'{len(conflicting_slots)} slot(s) already booked on this date. Please select different slots.'
                    }, status=400)
            
            # Calculate total by summing each slot's individual price (ISA field)
            total_amount = 0
            amount_per_slot = DEFAULT_PRICE  # Default fallback
            
            if custom_amount:
                # Use custom amount for all slots
                amount_per_slot = float(custom_amount)
                total_amount = len(available_slots) * amount_per_slot
            else:
                # Sum each slot's individual ISA price
                for slot in slots:
                    if slot.isa is not None:
                        total_amount += float(slot.isa)
                    else:
                        total_amount += DEFAULT_PRICE
            
            # If only one slot and using default, set amount_per_slot accordingly
            if len(available_slots) == 1:
                slot = slots.first()
                amount_per_slot = float(slot.isa) if slot.isa else DEFAULT_PRICE
            
            # Create booking
            booking = Booking(
                user=request.user,
                date=date,
                amount_per_slot=amount_per_slot,
                total_amount=total_amount,
                status='pending'
            )
            
            booking.save()
            for slot_id in available_slots:
                booking.slots.add(slot_id)
            
            # Create Razorpay order
            order = client.order.create({
                'amount': int(total_amount * 100),
                'currency': 'INR',
                'receipt': f'booking_{booking.id}'
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
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@login_required
def payment_success(request):
    """Handle successful payment"""
    if request.method == "POST":
        order_id = request.POST.get("razorpay_order_id")
        payment_id = request.POST.get("razorpay_payment_id")
        signature = request.POST.get("razorpay_signature")
        
        try:
            booking = Booking.objects.get(razorpay_order_id=order_id)
            
            # Verify payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            
            # Update booking
            booking.is_paid = True
            booking.confirm_booking()  # This will mark as confirmed and book slots
            booking.save()
            
            messages.success(request, 'Payment successful! Your booking is confirmed.')
            return JsonResponse({'success': True, 'redirect_url': f'/booking/{booking.id}/'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False})

@login_required
def payment_failed(request):
    """Handle failed payment"""
    booking_id = request.GET.get('booking_id')
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        booking.cancel_booking()
        messages.error(request, 'Payment failed. Your booking has been cancelled.')
    except Booking.DoesNotExist:
        pass
    return redirect('home')

# ==================== BOOKING MANAGEMENT VIEWS ====================

@login_required
def history(request):
    """View user's booking history"""
    search_date_str = request.GET.get('date')
    status_filter = request.GET.get('status')
    
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    if search_date_str:
        search_date = parse_date(search_date_str)
        if search_date:
            bookings = bookings.filter(date=search_date)
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    today = timezone.now().date()
    return render(request, "history.html", {
        "bookings": bookings, 
        "search_date": search_date_str,
        "status_filter": status_filter,
        "today": today
    })

@login_required
def booking_detail(request, booking_id):
    """View booking details"""
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        return render(request, 'booking_detail.html', {'booking': booking})
    except Booking.DoesNotExist:
        return render(request, 'error.html', {'error': 'Booking not found'}, status=404)

@login_required
@require_POST
def cancel_booking(request, booking_id):
    """Cancel an existing booking"""
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        
        # Check if booking can be cancelled (not completed)
        if booking.status == 'completed':
            return JsonResponse({'error': 'Cannot cancel completed booking'}, status=400)
        
        # Check cancellation time limit (e.g., 24 hours before)
        if booking.date <= timezone.now().date():
            return JsonResponse({'error': 'Cannot cancel booking on or after the booking date'}, status=400)
        
        booking.cancel_booking()
        messages.success(request, f'Booking #{booking.id} cancelled successfully!')
        return JsonResponse({'success': True})
        
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

@login_required
@require_POST
def reschedule_booking(request, booking_id):
    """Reschedule booking to different date/slots"""
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        
        # Check if booking can be rescheduled
        if booking.status == 'completed':
            return JsonResponse({'error': 'Cannot reschedule completed booking'}, status=400)
        
        new_date = request.POST.get('new_date')
        new_slot_ids = request.POST.getlist('new_slots')
        
        if not new_date or not new_slot_ids:
            return JsonResponse({'error': 'New date and slots are required'}, status=400)
        
        # Check availability of new slots
        for slot_id in new_slot_ids:
            existing = Booking.objects.filter(
                date=new_date,
                slots__id=slot_id,
                is_paid=True,
                status__in=['confirmed', 'completed']
            ).exclude(id=booking.id).exists()
            
            if existing:
                return JsonResponse({'error': 'Selected slots are not available'}, status=400)
        
        # Cancel old booking and free slots
        booking.cancel_booking()
        
        # Create new booking
        new_booking = Booking(
            user=request.user,
            date=new_date,
            amount_per_slot=booking.amount_per_slot,
            status='pending',
            is_paid=False
        )
        new_booking.save()
        for slot_id in new_slot_ids:
            new_booking.slots.add(slot_id)
        
        new_booking.calculate_total()
        new_booking.save()
        
        # Create new payment order
        order = client.order.create({
            'amount': int(new_booking.total_amount * 100),
            'currency': 'INR',
        })
        new_booking.razorpay_order_id = order['id']
        new_booking.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Please complete payment for rescheduled booking',
            'order_id': order['id'],
            'amount': new_booking.total_amount,
            'booking_id': new_booking.id
        })
        
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

# ==================== ADMIN/EXTRA FEATURES ====================

@login_required
def upcoming_bookings(request):
    """View upcoming bookings"""
    today = timezone.now().date()
    bookings = Booking.objects.filter(
        user=request.user,
        date__gte=today,
        status__in=['confirmed', 'pending']
    ).order_by('date', 'created_at')
    
    return render(request, 'upcoming_bookings.html', {'bookings': bookings})

@login_required
def modify_booking_amount(request, booking_id):
    """Allow admin to modify booking amount"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            booking = Booking.objects.get(id=booking_id)
            new_amount = float(request.POST.get('amount'))
            
            booking.update_amount(new_amount)
            messages.success(request, f'Amount updated to ₹{new_amount}')
            return JsonResponse({'success': True, 'new_amount': booking.total_amount})
            
        except Booking.DoesNotExist:
            return JsonResponse({'error': 'Booking not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def modify_booking_timing(request, booking_id):
    """Allow admin to modify booking timing"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            booking = Booking.objects.get(id=booking_id)
            new_start = request.POST.get('start_time')
            new_end = request.POST.get('end_time')
            reason = request.POST.get('reason', '')
            
            if new_start and new_end:
                booking.modify_timing(new_start, new_end, reason)
                messages.success(request, f'Timing modified for booking #{booking.id}')
                return JsonResponse({'success': True})
            
            return JsonResponse({'error': 'Invalid timing'}, status=400)
            
        except Booking.DoesNotExist:
            return JsonResponse({'error': 'Booking not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def my_profile(request):
    """View and update user profile"""
    profile = request.user.userprofile
    
    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        if phone:
            profile.phone_number = phone
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('my_profile')
    
    return render(request, 'profile.html', {'profile': profile})

# ==================== LOGIN VIEW ====================

def login_view(request):
    from django.contrib.auth import login as auth_login
    from django.contrib.auth import authenticate
    
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            if remember:
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)  # Session expires on browser close
            
            next_url = request.GET.get('next', 'home')
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'registration/login.html')
