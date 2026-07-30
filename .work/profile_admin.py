import time

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext


user = get_user_model().objects.filter(is_superuser=True).first()
request = RequestFactory().get("/admin/")
request.user = user

started = time.perf_counter()
with CaptureQueriesContext(connection) as queries:
    response = admin.site.index(request)
    response.render()
elapsed = time.perf_counter() - started

print(f"ADMIN_RENDER_SECONDS|{elapsed:.4f}")
print(f"ADMIN_RENDER_QUERIES|{len(queries)}")
for query in sorted(queries.captured_queries, key=lambda item: float(item["time"]), reverse=True)[:5]:
    print(f"QUERY|{query['time']}|{query['sql'][:180]}")
