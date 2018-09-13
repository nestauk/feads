from django.contrib import admin

from .models import DataScienceResource
from .models import Decisions

admin.site.register(DataScienceResource)
admin.site.register(Decisions)
admin.site.site_header = 'Feads (admin)'
