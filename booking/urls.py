from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('register/', views.register, name="register"),
    path('api/booked-slots/<str:date_str>/', views.api_booked_slots, name="api_booked_slots"),
    path('book/', views.book_slot, name="book"),
    path('payment-success/', views.payment_success, name="payment_success"),
    path('history/', views.history, name="history"),
]
