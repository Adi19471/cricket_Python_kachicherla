from django.contrib import admin
from .models import TimeSlot, Booking, UserProfile

# Admin Header Customization
admin.site.site_header = "Booking System Admin"
admin.site.site_title = "Booking Admin"
admin.site.index_title = "Welcome to Booking Dashboard"


# ✅ TIMESLOT ADMIN
@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time', 'is_booked', 'isa')
    list_filter = ('is_booked',)
    list_editable = ('is_booked', 'isa')
    list_per_page = 20
    search_fields = ('start_time', 'end_time')


# ✅ INLINE SLOT DISPLAY IN BOOKING
class SlotInline(admin.TabularInline):
    model = Booking.slots.through
    extra = 0
    readonly_fields = ('timeslot_id',)
    
    def timeslot_id(self, obj):
        return obj.timeslot.id
    timeslot_id.short_description = 'Slot ID'


# ✅ BOOKING ADMIN
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'date',
        'slots_count',
        'amount_per_slot',
        'total_amount',
        'is_paid',
        'status',
        'created_at'
    )

    list_filter = ('is_paid', 'status', 'date', 'created_at')
    search_fields = ('user__username', 'razorpay_order_id', 'id')
    readonly_fields = ('created_at', 'total_amount')
    filter_horizontal = ('slots',)
    inlines = [SlotInline]
    list_editable = ('amount_per_slot', 'status')
    list_per_page = 20

    # ✅ Slot Count Display
    def slots_count(self, obj):
        return obj.slots.count()
    slots_count.short_description = 'Number of Slots'

    # ✅ Save Model with Auto Total Calculation
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.save()  # Save first for M2M
        if obj.amount_per_slot and obj.slots.exists():
            obj.total_amount = obj.amount_per_slot * obj.slots.count()
        super().save_model(request, obj, form, change)

    # ✅ Admin Actions
    actions = ['confirm_bookings', 'mark_as_completed', 'cancel_bookings']

    def confirm_bookings(self, request, queryset):
        for booking in queryset:
            booking.is_paid = True
            booking.confirm_booking()
        self.message_user(request, f"{queryset.count()} booking(s) confirmed successfully.")
    confirm_bookings.short_description = "Confirm selected bookings (Mark as paid)"

    def mark_as_completed(self, request, queryset):
        for booking in queryset:
            booking.mark_as_completed()
        self.message_user(request, f"{queryset.count()} booking(s) marked as completed.")
    mark_as_completed.short_description = "Mark selected bookings as completed"

    def cancel_bookings(self, request, queryset):
        for booking in queryset:
            booking.cancel_booking()
        self.message_user(request, f"{queryset.count()} booking(s) cancelled.")
    cancel_bookings.short_description = "Cancel selected bookings"

    # ✅ Custom Timing Modification Action
    actions.append('modify_timing_action')
    
    def modify_timing_action(self, request, queryset):
        for booking in queryset:
            # Example: modify timing by 1 hour (you can customize this)
            from datetime import datetime, timedelta
            if booking.modified_start_time:
                new_start = (datetime.combine(datetime.today(), booking.modified_start_time) + timedelta(hours=1)).time()
                new_end = (datetime.combine(datetime.today(), booking.modified_end_time) + timedelta(hours=1)).time()
                booking.modify_timing(new_start, new_end, "Admin bulk timing modification")
        self.message_user(request, f"Timing modified for {queryset.count()} booking(s).")
    modify_timing_action.short_description = "Modify timing (+1 hour) for selected bookings"


# ✅ USER PROFILE ADMIN
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'amount')
    search_fields = ('user__username', 'phone_number', 'user__email')
    list_filter = ('amount',)
    list_editable = ('amount',)
    readonly_fields = ('user',)
    
    def has_add_permission(self, request):
        return False  # UserProfile created automatically with User


# ✅ OPTIONAL: User Admin (if you want to see users in admin)
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')
    
    # Add UserProfile link in user view
    def get_userprofile(self, obj):
        try:
            return obj.userprofile.phone_number
        except:
            return "No profile"
    get_userprofile.short_description = 'Phone Number'
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_userprofile', 'is_staff')