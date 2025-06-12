from django import forms
from django.contrib.auth.models import User
from webapp.models import Household, HouseholdMember

class CreateHouseholdForm(forms.ModelForm):
    """Formulaire pour créer un nouveau ménage"""
    class Meta:
        model = Household
        fields = ['name', 'household_type']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'p-2 border rounded-md w-full'})
        self.fields['household_type'].widget.attrs.update({'class': 'p-2 border rounded-md w-full'})
        
        # Ajouter des descriptions pour les types de ménage
        self.fields['household_type'].help_text = {
            'SINGLE': 'Pour une personne seule gérant ses propres finances.',
            'COUPLE_SHARED': 'Pour un couple partageant tous leurs comptes et finances.',
            'COUPLE_MIXED': 'Pour un couple avec des comptes personnels et communs.',
            'COUPLE_SEPARATE': 'Pour un couple gérant leurs finances séparément.',
            'FAMILY_SHARED': 'Pour une famille partageant tous leurs comptes.',
            'FAMILY_MIXED': 'Pour une famille avec des comptes personnels et communs.',
            'ROOMMATES': 'Pour des colocataires avec finances séparées mais dépenses communes.',
            'CUSTOM': 'Configuration personnalisée des partages.'
        }

class AddMemberForm(forms.Form):
    """Formulaire pour ajouter un membre à un ménage"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label="Utilisateur",
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full'})
    )
    role = forms.ChoiceField(
        choices=HouseholdMember.ROLE_CHOICES,
        initial='MEMBER',
        label="Rôle",
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full'})
    )
    
    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if household:
            # Exclure les utilisateurs déjà membres du ménage
            existing_members = household.members.values_list('user', flat=True)
            self.fields['user'].queryset = User.objects.exclude(id__in=existing_members)

class AccountSharingForm(forms.Form):
    """Formulaire pour gérer le partage des comptes"""
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user:
            from webapp.models import Account
            accounts = Account.objects.filter(user=user)
            
            for account in accounts:
                self.fields[f'share_account_{account.id}'] = forms.BooleanField(
                    label=f"Partager {account.name}",
                    required=False,
                    initial=account.is_shared,
                    widget=forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5'})
                )
