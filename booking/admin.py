from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import TimeSlot, Booking, UserProfile


admin.site.site_header = "CRICKET BOOKING"
admin.site.site_title = "Cricket Admin"
admin.site.index_title = "Welcome to Cricket Booking Dashboard 7801019106/9704723840"

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time')
    list_per_page = 20

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'slots_count', 'total_amount', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'date', 'created_at')
    search_fields = ('user__username', 'razorpay_order_id')
    readonly_fields = ('created_at',)

    def slots_count(self, obj):
        return obj.slots.count()
    slots_count.short_description = 'Slots Count'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'amount')
    search_fields = ('user__username', 'phone_number')
    list_filter = ('amount',)

admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
