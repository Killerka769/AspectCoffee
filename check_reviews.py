import django; import os; os.environ['DJANGO_SETTINGS_MODULE']='aspectcoffee.settings'
import django; django.setup()
from apps.pages.models import Review
for r in Review.objects.filter(is_approved=True):
    uid = r.user_id if r.user else None
    fn = r.user.first_name if r.user else ''
    un = r.user.username if r.user else ''
    print(f'Review {r.id}: user_id={uid}, username={un!r}, first_name={fn!r}, author_name={r.author_name!r}')
