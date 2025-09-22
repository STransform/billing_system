from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .forms import ContactForm

from django.views.generic import View, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse

from .models import FlavorPrice, VolumePrice, IpPrice, RouterPrice, SnapShotPrice, ImagePrice, Instance
from .forms import FlavorPriceForm, VolumePriceForm, IpPriceForm, RouterPriceForm, SnapShotPriceForm, ImagePriceForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache


# your_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContactForm

def landing_page(request):
    # 🔹 Handle Contact Form Submission
    form = ContactForm()
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully!")
            return redirect("landing_page")  

    # 🔹 Process Pricing Data
    flavors = [
        {"name": "OSTD.1-2", "vcpu": 1, "ram": 2, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.2-4", "vcpu": 2, "ram": 4, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.2-8", "vcpu": 2, "ram": 8, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.4-8", "vcpu": 4, "ram": 8, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.4-16", "vcpu": 4, "ram": 16, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.8-16", "vcpu": 8, "ram": 16, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.8-24", "vcpu": 8, "ram": 24, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.12-24", "vcpu": 12, "ram": 24, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.12-32", "vcpu": 12, "ram": 32, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.16-32", "vcpu": 16, "ram": 32, "os_storage": 30, "data_storage": 50},
        {"name": "OSTD.16-48", "vcpu": 16, "ram": 48, "os_storage": 30, "data_storage": 50},
    ]

    for f in flavors:
        f["price"] = (f["vcpu"] * 2700) + (f["ram"] * 2500) + (f["os_storage"] * 20) + (f["data_storage"] * 20)

    # 🔹 Render the template with both contexts
    context = {
        "form": form,
        "flavors": flavors
    }
    return render(request, "landing_page/landing.html", context)


def user_instances(request):
    tenant_id = request.session.get('project_id', None)
    if not tenant_id:
        return render(request, 'dashboard/index.html', {
            'instances': [],
            'error': 'No tenant ID found in session. Please authenticate.'
        })
    instances = Instance.objects.filter(tenant_id=tenant_id)
    
    return {
        'instances': instances,
        'tenant_id': tenant_id
    }

@login_required(login_url='/accounts/login/')  # Redirects if not logged in
@never_cache
def dashboard(request):
    context = user_instances(request) 
    return render(request, "dashboard/index.html", context)

def invoice_detail(request, pk):
    return HttpResponse(f"Invoice #{pk} details here")


@csrf_exempt
def record_payment(request):

    return None

MODEL_MAP = {
    'flavor': {'model': FlavorPrice, 'form': FlavorPriceForm, 'id_field': 'flavor_id'},
    'volume': {'model': VolumePrice, 'form': VolumePriceForm, 'id_field': 'volume_type_id'},
    'ip': {'model': IpPrice, 'form': IpPriceForm, 'id_field': 'id'},
    'router': {'model': RouterPrice, 'form': RouterPriceForm, 'id_field': 'id'},
    'snapshot': {'model': SnapShotPrice, 'form': SnapShotPriceForm, 'id_field': 'id'},
    'image': {'model': ImagePrice, 'form': ImagePriceForm, 'id_field': 'id'},
}

class PricingView(View):
    def get(self, request, *args, **kwargs):
        context = {
            'flavor_prices': FlavorPrice.objects.all(),
            'volume_prices': VolumePrice.objects.all(),
            'ip_prices': IpPrice.objects.all(),
            'router_prices': RouterPrice.objects.all(),
            'snapshot_prices': SnapShotPrice.objects.all(),
            'image_prices': ImagePrice.objects.all(),
        }
        return render(request, 'dashboard/price_configuration/price_conf.html', context)

class DynamicPriceCreateView(View):
    def get(self, request, model_name):
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            return HttpResponse("Invalid model name", status=404)
        form = model_info['form']()
        return render(request, 'dashboard/price_configuration/price_modal_form.html', {'form': form, 'model_name': model_name})

    def post(self, request, model_name):
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            return HttpResponse("Invalid model name", status=404)
        form = model_info['form'](request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Created successfully!") 
        return render(request, 'dashboard/price_configuration/price_modal_form.html', {'form': form, 'model_name': model_name})

class DynamicPriceUpdateView(View):
    def get(self, request, model_name, pk):
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            return HttpResponse("Invalid model name", status=404)
        
        instance = get_object_or_404(model_info['model'], pk=pk)
        form = model_info['form'](instance=instance)
        return render(request, 'dashboard/price_configuration/price_modal_form.html', {'form': form, 'model_name': model_name, 'instance': instance})

    def post(self, request, model_name, pk):
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            return HttpResponse("Invalid model name", status=404)
            
        instance = get_object_or_404(model_info['model'], pk=pk)
        form = model_info['form'](request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated successfully!")
        return render(request, 'dashboard/price_configuration/price_modal_form.html', {'form': form, 'model_name': model_name, 'instance': instance})

class DynamicPriceDeleteView(View):
    def get(self, request, model_name, pk):
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            return HttpResponse("Invalid model name", status=404)
        
        instance = get_object_or_404(model_info['model'], pk=pk)
        return render(request, 'dashboard/price_configuration/price_delete_confirm.html', {'object': instance, 'model_name': model_name})

    def post(self, request, model_name, pk):
        model_info = MODEL_MAP.get(model_name)
        if not model_info:
            messages.success(request, "Invalid model name!")
            
        instance = get_object_or_404(model_info['model'], pk=pk)
        instance.delete()
        messages.success(request, "Deleted successfully!")

