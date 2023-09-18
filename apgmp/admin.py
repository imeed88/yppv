from django.contrib import admin
from .models import order, userprofile, group,equipment

# Register your models here.
admin.site.register(order)
admin.site.register(userprofile)
admin.site.register(group)
admin.site.register(equipment)