from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from apps.portfolio.models import Portfolio
from apps.wallet.models import SeedPhrase

# This view handles user signup. It uses Django's built-in UserCreationForm to create a new user. If the form is valid, it saves the user, logs them in, and redirects to the homepage. If the request method is GET, it simply renders the signup form.
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})

#
@login_required
def index(request):
    portfolios = Portfolio.objects.filter(user=request.user)
    return render(request, "portfolio/dashboard.html", {"portfolios": portfolios})


@login_required
def detail(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
    holdings = portfolio.holdings.select_related("asset")
    allocation = portfolio.get_allocation()
    return render(
        request,
        "portfolio/detail.html",
        {
            "portfolio": portfolio,
            "holdings": holdings,
            "allocation": allocation,
        },
    )


@login_required
# This view handles the wallet page for the user. It checks if the user has an associated seed phrase and creates one if it doesn't exist. If the request method is POST and the action is to mark the seed phrase as downloaded, it updates the seed phrase accordingly. Finally, it renders the wallet page with the seed phrase information.
def wallet(request):
    seed_phrase = getattr(request.user, "seed_phrase", None)
    if not seed_phrase:
        seed_phrase = SeedPhrase.objects.create(user=request.user)

    if request.method == "POST":
        import json

        data = json.loads(request.body)
        if data.get("action") == "mark_downloaded":
            seed_phrase.is_downloaded = True
            seed_phrase.save()
            return JsonResponse({"status": "ok"})

    return render(request, "portfolio/wallet.html", {"seed_phrase": seed_phrase})


def import_wallet_step1(request):
    return render(request, "wallet/import/step1.html")


def import_wallet_step2(request):
    if request.method == "POST":
        request.session["import_seed_phrase"] = (
            request.POST.get("seed_phrase", "").strip().lower()
        )
        return redirect("portfolio:import_step3")
    return render(request, "wallet/import/step2.html")


def import_wallet_step3(request):
    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            return render(
                request, "wallet/import/step3.html", {"error": "Passwords do not match"}
            )

        if len(password) < 8:
            return render(
                request,
                "wallet/import/step3.html",
                {"error": "Password must be at least 8 characters"},
            )

        request.session["import_password"] = password
        return redirect("portfolio:import_step4")

    return render(request, "wallet/import/step3.html")

#
def import_wallet_step4(request):
    seed_phrase = request.session.get("import_seed_phrase", "")
    password = request.session.get("import_password", "")

    if not seed_phrase or not password:
        return redirect("portfolio:import_step1")

    words = seed_phrase.split()
    word_count = len(words)

    if word_count not in [12, 24]:
        del request.session["import_seed_phrase"]
        del request.session["import_password"]
        return redirect("portfolio:import_step2")

    return render(
        request,
        "wallet/import/step4.html",
        {"seed_phrase": seed_phrase, "word_count": word_count},
    )


def import_wallet_complete(request):
    if request.method == "POST":
        seed_phrase = request.session.pop("import_seed_phrase", "")
        password = request.session.pop("import_password", "")

        if seed_phrase and password:
            if request.user.is_authenticated:
                seed_phrase_obj, created = SeedPhrase.objects.get_or_create(
                    user=request.user
                )
                seed_phrase_obj.is_imported = True
                seed_phrase_obj.imported_phrase = seed_phrase
                seed_phrase_obj.save()

        return redirect("portfolio:wallet")

    return redirect("portfolio:index")
