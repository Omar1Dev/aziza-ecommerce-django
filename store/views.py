from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import CartItem, Category, Order, OrderItem, Product

# Create your views here.


def home(request):
    categories = Category.objects.all()
    featured = Product.objects.filter(available=True).select_related("category")[:8]
    return render(
        request, "store/home.html", {"categories": categories, "featured": featured}
    )


def product_list(request):
    products = Product.objects.filter(available=True).select_related("category")
    category_slug = request.GET.get("category")
    selected = None
    if category_slug:
        selected = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected)
    categories = Category.objects.all()
    return render(
        request,
        "store/products.html",
        {"products": products, "categories": categories, "selected": selected},
    )


@login_required
def cart(request):
    items = CartItem.objects.filter(user=request.user).select_related("product__category")
    total = sum(item.get_total() for item in items)
    return render(request, "store/cart.html", {"items": items, "total": total})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.quantity += 1
        item.save()
    return redirect("cart")


@require_POST
@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(id=item_id, user=request.user).delete()
    return redirect("cart")


@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user).select_related("product__category")
    if not items:
        return redirect("cart")
    if request.method == "POST":
        total = sum(item.get_total() for item in items)
        order = Order.objects.create(
            user=request.user,
            total=total,
            full_name=request.POST.get("full_name", ""),
            address=request.POST.get("address", ""),
            phone=request.POST.get("phone", ""),
            payment_method=request.POST.get("payment", "cash"),
        )
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            product = item.product
            product.stock = max(0, product.stock - item.quantity)
            product.save()
        items.delete()
        return render(request, "store/order_success.html", {"order": order})
    total = sum(item.get_total() for item in items)
    return render(request, "store/checkout.html", {"items": items, "total": total})
