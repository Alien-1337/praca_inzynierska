"""Role i uprawnienia. Wszystko, co zależy od roli, sprawdzamy przez can()."""

# nazwy muszą być takie same jak w tabeli roles
ROLE_ADMIN = "Administrator"
ROLE_MANAGER = "Kierownik"
ROLE_USER = "Użytkownik"
ROLE_TECH = "Technik"

ALL_ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_USER, ROLE_TECH)

# rola nowych kont; pierwsze konto w pustej bazie dostaje Administratora (db_utils.add_user)
DEFAULT_ROLE = ROLE_USER

ROLE_DESCRIPTIONS = {
    ROLE_ADMIN: "Dostęp do wszystkich funkcjonalności",
    ROLE_MANAGER: "Dostęp do raportów i wizualizacji",
    ROLE_USER: "Dostęp do zgłaszania błędów",
    ROLE_TECH: "Dostęp do rozwiązywania błędów, aktualizowania stanu maszyn i magazynu",
}

# funkcje aplikacji (kafelki w menu i przyciski)
FEATURE_TPM_TASKS = "tpm_tasks"
FEATURE_TPM_PRINT = "tpm_print"
FEATURE_TPM_ACCEPT = "tpm_accept"
FEATURE_FAILURE_REPORT = "failure_report"
FEATURE_FAILURE_RESOLVE = "failure_resolve"
FEATURE_INVENTORY = "inventory"
FEATURE_ANALYTICS = "analytics"
FEATURE_ANALYTICS_PRINT = "analytics_print"   # druk raportów ze Statystyk
FEATURE_USERS = "users"

ALL_FEATURES = frozenset({
    FEATURE_TPM_TASKS,
    FEATURE_TPM_PRINT,
    FEATURE_TPM_ACCEPT,
    FEATURE_FAILURE_REPORT,
    FEATURE_FAILURE_RESOLVE,
    FEATURE_INVENTORY,
    FEATURE_ANALYTICS,
    FEATURE_ANALYTICS_PRINT,
    FEATURE_USERS,
})

ROLE_FEATURES = {
    # wszystko oprócz druku raportów, który ma tylko Kierownik
    ROLE_ADMIN: ALL_FEATURES - {FEATURE_ANALYTICS_PRINT},
    ROLE_MANAGER: frozenset({FEATURE_ANALYTICS, FEATURE_ANALYTICS_PRINT}),
    ROLE_USER: frozenset({FEATURE_FAILURE_REPORT}),
    ROLE_TECH: frozenset({FEATURE_FAILURE_RESOLVE, FEATURE_TPM_ACCEPT, FEATURE_INVENTORY}),
}


def features_for(role):
    return ROLE_FEATURES.get(role, frozenset())


def can(role, feature):
    return feature in features_for(role)
