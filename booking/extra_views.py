from django.shortcuts import render


def home_landing(request):
    return render(request, "home_landing.html")


def contract(request):
    return render(request, "contract.html")


def service(request):
    return render(request, "service.html")

