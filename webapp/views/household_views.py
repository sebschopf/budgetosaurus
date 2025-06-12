from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from webapp.models import Household, HouseholdMember, Account
from webapp.forms.household_forms import CreateHouseholdForm, AddMemberForm, AccountSharingForm
from webapp.services.household_service import HouseholdService
from webapp.services.permission_service import PermissionService

@login_required
def household_list_view(request):
    """Vue listant les ménages de l'utilisateur"""
    user_households = HouseholdService.get_user_households(request.user)
    
    context = {
        'page_title': 'Mes Ménages',
        'households': user_households,
    }
    return render(request, 'webapp/household/household_list.html', context)

@login_required
def create_household_view(request):
    """Vue pour créer un nouveau ménage"""
    if request.method == 'POST':
        form = CreateHouseholdForm(request.POST)
        if form.is_valid():
            household = HouseholdService.create_household(
                name=form.cleaned_data['name'],
                household_type=form.cleaned_data['household_type'],
                admin_user=request.user
            )
            messages.success(request, f"Le ménage '{household.name}' a été créé avec succès.")
            return redirect('household_detail', household_id=household.id)
    else:
        form = CreateHouseholdForm()
    
    context = {
        'page_title': 'Créer un Ménage',
        'form': form,
    }
    return render(request, 'webapp/household/create_household.html', context)

@login_required
def household_detail_view(request, household_id):
    """Vue détaillée d'un ménage"""
    household = get_object_or_404(Household, id=household_id)
    
    # Vérifier que l'utilisateur est membre du ménage
    if not HouseholdMember.objects.filter(household=household, user=request.user).exists():
        messages.error(request, "Vous n'avez pas accès à ce ménage.")
        return redirect('household_list')
    
    # Récupérer les membres du ménage
    members = HouseholdService.get_household_members(household)
    
    # Vérifier si l'utilisateur est administrateur
    is_admin = HouseholdService.is_household_admin(request.user, household)
    
    context = {
        'page_title': f'Ménage: {household.name}',
        'household': household,
        'members': members,
        'is_admin': is_admin,
    }
    return render(request, 'webapp/household/household_detail.html', context)

@login_required
def add_household_member_view(request, household_id):
    """Vue pour ajouter un membre à un ménage"""
    household = get_object_or_404(Household, id=household_id)
    
    # Vérifier que l'utilisateur est administrateur du ménage
    if not HouseholdService.is_household_admin(request.user, household):
        messages.error(request, "Vous devez être administrateur pour ajouter des membres.")
        return redirect('household_detail', household_id=household.id)
    
    if request.method == 'POST':
        form = AddMemberForm(request.POST, household=household)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']
            
            HouseholdService.add_member(household, user, role)
            messages.success(request, f"{user.username} a été ajouté au ménage avec le rôle {dict(HouseholdMember.ROLE_CHOICES)[role]}.")
            return redirect('household_detail', household_id=household.id)
    else:
        form = AddMemberForm(household=household)
    
    context = {
        'page_title': f'Ajouter un membre à {household.name}',
        'household': household,
        'form': form,
    }
    return render(request, 'webapp/household/add_member.html', context)

@login_required
def remove_household_member_view(request, household_id, user_id):
    """Vue pour retirer un membre d'un ménage"""
    household = get_object_or_404(Household, id=household_id)
    
    # Vérifier que l'utilisateur est administrateur du ménage
    if not HouseholdService.is_household_admin(request.user, household):
        messages.error(request, "Vous devez être administrateur pour retirer des membres.")
        return redirect('household_detail', household_id=household.id)
    
    from django.contrib.auth.models import User
    user_to_remove = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        HouseholdService.remove_member(household, user_to_remove)
        messages.success(request, f"{user_to_remove.username} a été retiré du ménage.")
        return redirect('household_detail', household_id=household.id)
    
    context = {
        'page_title': f'Retirer {user_to_remove.username} de {household.name}',
        'household': household,
        'user_to_remove': user_to_remove,
    }
    return render(request, 'webapp/household/remove_member.html', context)

@login_required
def change_household_type_view(request, household_id):
    """Vue pour changer le type de ménage"""
    household = get_object_or_404(Household, id=household_id)
    
    # Vérifier que l'utilisateur est administrateur du ménage
    if not HouseholdService.is_household_admin(request.user, household):
        messages.error(request, "Vous devez être administrateur pour modifier le type de ménage.")
        return redirect('household_detail', household_id=household.id)
    
    if request.method == 'POST':
        form = CreateHouseholdForm(request.POST, instance=household)
        if form.is_valid():
            new_type = form.cleaned_data['household_type']
            HouseholdService.change_household_type(household, new_type)
            messages.success(request, f"Le type de ménage a été changé en {dict(Household.HOUSEHOLD_TYPES)[new_type]}.")
            return redirect('household_detail', household_id=household.id)
    else:
        form = CreateHouseholdForm(instance=household)
    
    context = {
        'page_title': f'Modifier le type de {household.name}',
        'household': household,
        'form': form,
    }
    return render(request, 'webapp/household/change_type.html', context)

@login_required
def manage_account_sharing_view(request):
    """Vue pour gérer le partage des comptes"""
    user_accounts = Account.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = AccountSharingForm(request.POST, user=request.user)
        if form.is_valid():
            for account in user_accounts:
                field_name = f'share_account_{account.id}'
                if field_name in form.cleaned_data:
                    account.is_shared = form.cleaned_data[field_name]
                    account.save()
            
            messages.success(request, "Les paramètres de partage des comptes ont été mis à jour.")
            return redirect('household_list')  # Rediriger vers la liste des ménages
    else:
        form = AccountSharingForm(user=request.user)
    
    context = {
        'page_title': 'Gérer le partage des comptes',
        'form': form,
        'accounts': user_accounts,
    }
    return render(request, 'webapp/household/manage_account_sharing.html', context)

@login_required
def manage_category_sharing_view(request):
    """Vue pour gérer le partage des catégories"""
    from webapp.models import Category
    user_categories = Category.objects.filter(user=request.user)
    
    if request.method == 'POST':
        for category in user_categories:
            field_name = f'share_category_{category.id}'
            if field_name in request.POST:
                category.is_shared = True
            else:
                category.is_shared = False
            category.save()
        
        messages.success(request, "Les paramètres de partage des catégories ont été mis à jour.")
        return redirect('household_list')
    
    context = {
        'page_title': 'Gérer le partage des catégories',
        'categories': user_categories,
    }
    return render(request, 'webapp/household/manage_category_sharing.html', context)
