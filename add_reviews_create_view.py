filepath = '/app/apps/pages/views.py'
with open(filepath, 'r') as f:
    content = f.read()

add_code = '''

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

@login_required
@require_POST
def reviews_create(request):
    import json
    from apps.catalog.models import Review, Product
    
    rating = int(request.POST.get("rating", 0))
    delivery_rating = request.POST.get("delivery_rating")
    text = request.POST.get("text", "")
    delivery_text = request.POST.get("delivery_text", "")
    delivery_operator = request.POST.get("delivery_operator", "")
    
    errors = {}
    if rating < 1 or rating > 5:
        errors["rating"] = "Рейтинг магазина от 1 до 5"
    if not text.strip():
        errors["text"] = "Напишите отзыв"
    
    if delivery_rating:
        delivery_rating = int(delivery_rating)
        if delivery_rating < 1 or delivery_rating > 5:
            errors["delivery_rating"] = "Рейтинг доставки от 1 до 5"
    else:
        delivery_rating = None
    
    if errors:
        return JsonResponse({"success": False, "errors": errors})
    
    default_product = Product.objects.order_by("id").first()
    if not default_product:
        return JsonResponse({"success": False, "errors": {"general": "Нет товаров"}})
    
    review = Review.objects.create(
        product=default_product,
        user=request.user,
        rating=rating,
        delivery_rating=delivery_rating,
        text=text.strip(),
        delivery_text=delivery_text.strip(),
        delivery_operator=delivery_operator.strip(),
        status=Review.STATUS_NEW,
    )
    
    return JsonResponse({"success": True, "review_id": review.pk})
'''

# Add at end of file
content += add_code
with open(filepath, 'w') as f:
    f.write(content)
print('VIEW ADDED')
