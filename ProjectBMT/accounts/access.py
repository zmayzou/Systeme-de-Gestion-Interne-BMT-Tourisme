from accounts.models import Employe


GLOBAL_ROLES = [
    'Administrateur',
    'Directeur',
]


def get_employe(user):
    """
    Retourne le profil Employe de l'utilisateur connecté.
    """

    if not user or not user.is_authenticated:
        return None

    return getattr(
        user,
        'employe',
        None
    )


def has_global_agency_access(user):
    """
    True :
        - Superuser
        - Administrateur
        - Directeur

    False :
        - Employés normaux
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    employe = get_employe(user)

    if not employe:
        return False

    if not employe.est_actif:
        return False

    if employe.role and employe.role.nom in GLOBAL_ROLES:
        return True

    return False


def get_user_agence(user):
    """
    Retourne l'agence de l'employé connecté.
    """

    employe = get_employe(user)

    if not employe:
        return None

    return employe.agence