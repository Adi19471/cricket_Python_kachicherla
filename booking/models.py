from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


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

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"

    @property
    def is_available(self):
        return not self.is_booked

    def mark_as_booked(self):
        self.is_booked = True
        self.save()

    def mark_as_available(self):
        self.is_booked = False
        self.save()

    def get_duration(self):
        from datetime import datetime
        start = datetime.strptime(str(self.start_time), "%H:%M:%S")
        end = datetime.strptime(str(self.end_time), "%H:%M:%S")
        duration = end - start
        return duration.total_seconds() / 3600


class Booking(models.Model):
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    slots = models.ManyToManyField(TimeSlot)
    amount = models.IntegerField(default=500)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.id}"

    def calculate_total(self):
        if not self.total_amount:
            self.total_amount = self.amount * self.slots.count()

    def clean(self):
        from django.core.exceptions import ValidationError
        for slot in self.slots.all():
            existing_bookings = Booking.objects.filter(
                date=self.date,
                slots=slot,
                is_paid=True
            ).exclude(pk=self.pk)

            if existing_bookings.exists():
                raise ValidationError(f"Slot {slot} already booked on {self.date}!")

    def mark_as_completed(self):
        if self.is_paid:
            self.status = 'completed'
            self.calculate_total()
            self.save()

            for slot in self.slots.all():
                slot.is_booked = True
                slot.save()
