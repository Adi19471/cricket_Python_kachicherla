from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'."
            )
        ]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"


class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    
    # Admin can customize amount per slot
    isa = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Custom amount for this specific slot (overrides default)"
    )

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"

    @property
    def is_available(self):
        return not self.is_booked

    @property
    def get_amount(self):
        """Returns custom amount if set, otherwise returns None (will use default)"""
        return self.isa

    def mark_as_booked(self):
        self.is_booked = True
        self.save()

    def mark_as_available(self):
        self.is_booked = False
        self.save()


class Booking(models.Model):
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    slots = models.ManyToManyField(TimeSlot)
    
    # Admin can modify amount at time of booking
    amount_per_slot = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Amount per slot (admin can modify)"
    )
    
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Admin can modify timing after booking
    modified_start_time = models.TimeField(blank=True, null=True)
    modified_end_time = models.TimeField(blank=True, null=True)
    modification_reason = models.TextField(blank=True, help_text="Reason for timing modification")

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username}"

    def calculate_total(self):
        """Calculate total based on amount per slot and number of slots"""
        if self.amount_per_slot and self.slots.exists():
            self.total_amount = self.amount_per_slot * self.slots.count()
            return self.total_amount
        return None

    def clean(self):
        """Validate that slots are not already booked for the same date"""
        for slot in self.slots.all():
            existing_bookings = Booking.objects.filter(
                date=self.date,
                slots=slot,
                is_paid=True,
                status__in=['confirmed', 'completed']
            ).exclude(pk=self.pk)

            if existing_bookings.exists():
                raise ValidationError(f"Time slot {slot.start_time} - {slot.end_time} is already booked on {self.date}!")

    def save(self, *args, **kwargs):
        """Auto-calculate total before saving"""
        if not self.total_amount and self.amount_per_slot:
            self.calculate_total()
        super().save(*args, **kwargs)

    def confirm_booking(self):
        """Confirm booking after payment"""
        if self.is_paid and self.status == 'pending':
            self.status = 'confirmed'
            self.save()
            # Mark slots as booked
            for slot in self.slots.all():
                slot.mark_as_booked()
            return True
        return False

    def mark_as_completed(self):
        """Mark booking as completed"""
        if self.status == 'confirmed':
            self.status = 'completed'
            self.save()
            return True
        return False

    def cancel_booking(self):
        """Cancel booking and free up slots"""
        if self.status in ['pending', 'confirmed']:
            self.status = 'cancelled'
            # Free up the slots
            for slot in self.slots.all():
                slot.mark_as_available()
            self.save()
            return True
        return False
    
    def modify_timing(self, new_start_time, new_end_time, reason=""):
        """Admin can modify timing of existing booking"""
        self.modified_start_time = new_start_time
        self.modified_end_time = new_end_time
        self.modification_reason = reason
        self.save()
        return True
    
    def update_amount(self, new_amount_per_slot):
        """Admin can modify amount even after booking"""
        self.amount_per_slot = new_amount_per_slot
        self.calculate_total()
        self.save()
        return self.total_amount

    @property
    def get_effective_timing(self):
        """Returns modified timing if available, otherwise original slot timing"""
        if self.modified_start_time and self.modified_end_time:
            return self.modified_start_time, self.modified_end_time
        elif self.slots.exists():
            first_slot = self.slots.first()
            return first_slot.start_time, first_slot.end_time
        return None, None

    class Meta:
        ordering = ['-created_at']