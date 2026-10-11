# CMMS – jak uruchomić (role, magazyn dla Technika, obieg awarii)

Ta instrukcja prowadzi od zera do działającej aplikacji. Kroki z **pgAdmin 4** są oznaczone 🐘.

---

## 1. Czego potrzebujesz

- **Python 3.10+** (z tkinter – instalator z python.org zawiera go domyślnie),
- **PostgreSQL** i **pgAdmin 4**.

## 2. Baza i plik z hasłem (jednorazowo)

🐘 **Baza w pgAdmin 4** (pomiń, jeśli bazę CMMS już masz):

1. W drzewie po lewej: *Servers → PostgreSQL → Databases*.
2. Prawy przycisk na *Databases* → *Create → Database…*.
3. Nazwa: `cmms` → *Save*.

**Plik `data.env`** (w głównym folderze projektu, obok `main.py`):

1. Skopiuj `data.env.example` jako `data.env`.
2. Wpisz swoje dane (nazwa bazy z `DB_NAME` musi być taka sama jak w pgAdmin):

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cmms
DB_USER=postgres
DB_PASSWORD=twoje_haslo
```

**Skąd wziąć wartości** (pgAdmin 4): prawy przycisk na serwerze → *Properties…* → zakładka *Connection* (host, port, użytkownik); nazwa bazy to nazwa z drzewa *Databases*; hasło to hasło użytkownika `postgres` tego serwera. **Masz zainstalowanych kilka wersji PostgreSQL (np. 14, 17 i 18)?** Każda ma własny port (zwykle 5432, 5433, 5434…) i własne hasło, więc `DB_PORT` i `DB_PASSWORD` muszą pasować do tego serwera, na którym jest baza.

> `data.env` zawiera hasło – nie wrzucaj go na GitHub. Jest w `.gitignore` (plik `.gitignore` był zapisany w UTF-16, którego git nie czyta, więc przepisałem go na UTF-8).

## 3. Instalacja bibliotek

W terminalu, w folderze projektu:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Pierwsze uruchomienie i pierwszy Administrator

Uruchamiaj zawsze **z folderu projektu** (aplikacja czyta `data.env` z bieżącego folderu):

```
python main.py
```

Przy starcie aplikacja sama dodaje to, czego brakuje w bazie: tabelę ról, kolumnę roli w `users` i status w `failures`. Dane już w bazie zostają.

### A) Nowa, pusta baza

1. `python main.py` → **Załóż konto**.
2. **Pierwsze konto w pustej bazie automatycznie dostaje rolę Administrator.**
3. Zaloguj się → kafelek **Użytkownicy** → nadaj role pozostałym kontom.

### B) Baza, w której już są konta

Po migracji wszystkie dotychczasowe konta mają rolę **Użytkownik**, więc trzeba nadać pierwszego Administratora. Najwygodniej w 🐘 pgAdmin 4:

1. W drzewie kliknij swoją bazę (`cmms`, **nie** `postgres`) → prawy przycisk → **Query Tool**.
2. W pasku narzędzi kliknij ikonę folderu (**Open File**) i wybierz `sql/001_add_roles.sql`.
3. Przewiń do sekcji **4)** i odkomentuj (usuń `-- `) linię z `UPDATE ... 'Administrator'`, wpisując swój login:
   ```sql
   UPDATE users SET role = 'Administrator' WHERE username = 'twoj_login';
   ```
4. Uruchom: **F5** (albo przycisk ▶).
5. W zakładce **Data Output** na dole zobaczysz 4 role i liczbę kont przypisanych do każdej z nich.

Skrypt można uruchamiać wielokrotnie (nie dubluje danych i nie nadpisuje nadanych ról). Jeśli pgAdmin pokaże „Brak tabel users/failures w bazie …”, zaznaczona jest zła baza albo baza jest pusta – wybierz właściwą lub najpierw uruchom aplikację (`python main.py`).

> Jeśli wyłączyłeś auto-commit w pasku Query Tool, dopisz na końcu skryptu `COMMIT;`.

Bez pgAdmina to samo zrobisz poleceniem `UPDATE` z kroku 3 w dowolnym narzędziu SQL.

## 5. Role i uprawnienia

| Rola | Dostęp (kafelki w menu) |
|---|---|
| **Administrator** | wszystko: Zadania, Drukowanie TPM, Zgłoszenie Awarii, Rozwiązywanie Awarii, Magazyn, Statystyki, Zatwierdź TPM, Użytkownicy |
| **Kierownik** | raporty i wizualizacje: **Statystyki** |
| **Użytkownik** | zgłaszanie błędów: **Zgłoszenie Awarii** |
| **Technik** | rozwiązywanie błędów i aktualizacja stanu: **Rozwiązywanie Awarii**, **Zatwierdź TPM**, oraz **Magazyn** |

Gdzie to się zmienia: wszystko jest w jednym miejscu – plik `permissions.py`, słownik `ROLE_FEATURES`. Przykład: żeby Technik mógł też zgłaszać awarie, dopisz mu `FEATURE_FAILURE_REPORT`.

Menu pokazuje tylko kafelki dozwolone dla roli. Dodatkowo przy **każdym** otwarciu funkcji aplikacja sprawdza rolę w bazie, więc odebrana rola przestaje działać od razu, nawet w już otwartym menu. Dane (zmiana ról, zgłaszanie i naprawy awarii) są zabezpieczone także w `db_utils.py`.

## 6. Obieg awarii

1. **Użytkownik**: *Zgłoszenie Awarii* → formularz samego zgłoszenia → status **Zgłoszona**. W historii widzi tylko własne zgłoszenia (bez kosztów).
2. **Technik**: *Rozwiązywanie Awarii* → zaznacz awarię:
   - **Rozpocznij naprawę** → status **W naprawie** (przypisana do Ciebie),
   - **Zakończ naprawę** → podajesz datę i godzinę zakończenia oraz ewentualnie zużytą część z magazynu → status **Rozwiązana**. Przestój i koszty (robocizna ze stawki Technika + cena części) liczą się automatycznie,
   - **Dodaj zakończoną awarię** – dla awarii naprawionej od razu, bez wcześniejszego zgłoszenia (pełny formularz jak dawniej).
3. **Kierownik**: *Statystyki* – wykresy i KPI; MTTR liczy się z awarii naprawionych, a „Otwarte Awarie” pokazuje, ile czeka.

Dotychczasowe awarie w bazie dostały status **Rozwiązana**.

## 7. Zmiana roli później

- **W aplikacji**: Administrator → *Użytkownicy* → zaznacz konto → wybierz rolę → **Zmień rolę**. Nie da się odebrać roli ostatniemu Administratorowi (najpierw nadaj Administratora komuś innemu).
- **W pgAdmin 4**: Query Tool na bazie `cmms`:
  ```sql
  UPDATE users SET role = 'Technik' WHERE username = 'jan';
  ```
  Dozwolone wartości: `Administrator`, `Kierownik`, `Użytkownik`, `Technik` (inna nazwa zostanie odrzucona).

Zmiana roli działa przy następnym otwarciu funkcji; żeby menu pokazało nowe kafelki, wyloguj się i zaloguj ponownie. Podgląd: `SELECT id, username, role FROM users ORDER BY id;`.

## 8. Gdy coś nie działa

| Objaw | Co sprawdzić |
|---|---|
| Konsola: „Nie udało się połączyć z PostgreSQL … Komunikat serwera: …” | przeczytaj komunikat serwera: „uwierzytelnienie hasłem nie powiodło się” (po angielsku *password authentication failed*) = zły `DB_USER`/`DB_PASSWORD` albo port innej instalacji PostgreSQL; „baza danych … nie istnieje” = zły `DB_NAME`; „Connection refused” = serwer wyłączony albo zły `DB_HOST`/`DB_PORT` |
| Konsola: „Błąd inicjalizacji bazy danych” bez komunikatu serwera | `data.env` (host, port, nazwa bazy, użytkownik, hasło), czy uruchamiasz z folderu projektu |
| Starsza wersja: `'utf-8' codec can't decode byte 0xb3 …` | to samo co wyżej, tylko niewidoczne: polski komunikat serwera w kodowaniu Windows-1250 nie dał się odczytać. Podmień `db_utils.py` na nowszy – pokaże prawdziwy komunikat |
| Konsola: „W bazie nie ma Administratora” | krok 4B |
| W menu tylko „Wyloguj” i ostrzeżenie o roli | konto nie istnieje w bazie albo błąd bazy – zaloguj się ponownie / sprawdź konsolę |
| Brakuje kafelka | rola nie ma tej funkcji (tabela w pkt 5) |
| pgAdmin: „Brak tabel users/failures …” | zła baza albo pusta – patrz krok 4B |

## 9. Co jest nowe w projekcie

- `permissions.py` – role i uprawnienia (jedno miejsce),
- `failure_resolve_window.py` – okno Technika (kolejka awarii, naprawy),
- `sql/001_add_roles.sql` – migracja do uruchomienia w pgAdmin 4,
- `requirements.txt`, `data.env.example`, `URUCHOMIENIE.md`,
- zmienione: `db_utils.py`, `main.py`, `main_menu.py`, `login_window.py`, `register_window.py`, `user_management_window.py`, `failure_window.py`, `failure_report.py`, `Analytics.py`, `setup_db.py` (teraz tylko wywołuje `create_tables()`), `README.md`, `.gitignore`.
