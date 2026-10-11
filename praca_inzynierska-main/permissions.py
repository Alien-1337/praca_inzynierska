"""Role i uprawnienia w CMMS.

To jedyne miejsce, w którym określamy, kto co może:
  * menu główne pokazuje kafelki na podstawie ROLE_FEATURES,
  * db_utils używa can() do zabezpieczenia operacji (zmiana ról, naprawy awarii),
  * opisy ról trafiają do tabeli roles w bazie.

Żeby zmienić uprawnienia którejś roli, wystarczy edytować ROLE_FEATURES niżej.
"""

# --- Role (nazwy muszą być takie same jak w tabeli roles w bazie) ---
ROLE_ADMIN = "Administrator"
ROLE_MANAGER = "Kierownik"
ROLE_USER = "Użytkownik"
ROLE_TECH = "Technik"

ALL_ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_USER, ROLE_TECH)

# Rola nowo zarejestrowanych kont (najmniejsze uprawnienia).
# Wyjątek: pierwsze konto w pustej bazie dostaje Administratora (patrz db_utils.add_user).
DEFAULT_ROLE = ROLE_USER

ROLE_DESCRIPTIONS = {
    ROLE_ADMIN: "Dostęp do wszystkich funkcjonalności",
    ROLE_MANAGER: "Dostęp do raportów i wizualizacji",
    ROLE_USER: "Dostęp do zgłaszania błędów",
    ROLE_TECH: "Dostęp do rozwiązywania błędów, aktualizowania stanu maszyn i magazynu",
}

# --- Funkcje aplikacji (kafelki w menu) ---
FEATURE_TPM_TASKS = "tpm_tasks"              # Zadania - edycja definicji zadań TPM
FEATURE_TPM_PRINT = "tpm_print"              # Drukowanie TPM
FEATURE_TPM_ACCEPT = "tpm_accept"            # Zatwierdź TPM (odhaczanie wykonanych zadań)
FEATURE_FAILURE_REPORT = "failure_report"    # Zgłoszenie awarii
FEATURE_FAILURE_RESOLVE = "failure_resolve"  # Rozwiązywanie awarii (naprawa, zmiana stanu)
FEATURE_INVENTORY = "inventory"              # Magazyn
FEATURE_ANALYTICS = "analytics"              # Statystyki (raporty i wizualizacje)
FEATURE_USERS = "users"                      # Użytkownicy (stawki i role)

ALL_FEATURES = frozenset({
    FEATURE_TPM_TASKS,
    FEATURE_TPM_PRINT,
    FEATURE_TPM_ACCEPT,
    FEATURE_FAILURE_REPORT,
    FEATURE_FAILURE_RESOLVE,
    FEATURE_INVENTORY,
    FEATURE_ANALYTICS,
    FEATURE_USERS,
})

# --- Kto co może ---
ROLE_FEATURES = {
    # Administrator - wszystko
    ROLE_ADMIN: ALL_FEATURES,

    # Kierownik - raporty i wizualizacje (kafelek "Statystyki")
    ROLE_MANAGER: frozenset({FEATURE_ANALYTICS}),

    # Użytkownik - zgłaszanie awarii
    ROLE_USER: frozenset({FEATURE_FAILURE_REPORT}),

    # Technik - rozwiązywanie awarii, aktualizacja stanu (zatwierdzanie zadań TPM) i magazyn
    ROLE_TECH: frozenset({
        FEATURE_FAILURE_RESOLVE,
        FEATURE_TPM_ACCEPT,
        FEATURE_INVENTORY,
    }),
}


def features_for(role):
    """Zbiór funkcji dostępnych dla roli (pusty dla nieznanej roli)."""
    return ROLE_FEATURES.get(role, frozenset())


def can(role, feature):
    """True, jeśli rola ma dostęp do funkcji. Brak roli / nieznana rola = brak dostępu."""
    return feature in features_for(role)
