from django.contrib import admin

from .models import DataScienceMethod
from .models import DataSource
from .models import Implementation
from .models import Decisions

admin.site.register(DataSource)
admin.site.register(DataScienceMethod)
admin.site.register(Implementation)
admin.site.register(Decisions)
admin.site.site_header = 'Feads (admin)'
