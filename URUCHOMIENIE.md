# CMMS - uruchomienie, role i raporty

Instrukcja prowadzi od pustego komputera do działającej aplikacji. Kroki w pgAdmin 4 są oznaczone słowem "pgAdmin".

## 1. Wymagania

- Python 3.10 lub nowszy (z tkinter, instalator z python.org zawiera go domyślnie),
- PostgreSQL i pgAdmin 4.

## 2. Baza i plik data.env

pgAdmin: baza (pomiń, jeśli już ją masz)

1. W drzewie po lewej rozwiń Servers i kliknij swój serwer, podaj hasło użytkownika postgres.
2. Prawy przycisk na Databases, potem Create > Database...
3. W polu Database wpisz cmms i kliknij Save.

Plik data.env leży w głównym folderze projektu, obok main.py. Skopiuj data.env.example jako data.env i wpisz swoje dane:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cmms
DB_USER=postgres
DB_PASSWORD=twoje_haslo
```

Wartości znajdziesz w pgAdmin: prawy przycisk na serwerze, Properties, zakładka Connection (host, port, użytkownik). Nazwa bazy to nazwa z drzewa Databases, a hasło to hasło użytkownika postgres tego serwera.

Jeśli masz zainstalowanych kilka wersji PostgreSQL (np. 14, 17 i 18), każda ma własny port (zwykle 5432, 5433, 5434) i własne hasło. DB_PORT i DB_PASSWORD muszą pasować do serwera, na którym jest baza.

W Windows plik musi nazywać się dokładnie data.env, a nie data.env.txt (w Eksploratorze włącz Widok > Pokaż > Rozszerzenia nazw plików). Hasło z # lub spacjami ujmij w cudzysłów: DB_PASSWORD="ha#slo". Nie wrzucaj tego pliku na GitHuba, jest wpisany do .gitignore.

## 3. Instalacja bibliotek

W terminalu, w folderze projektu:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Jeśli PowerShell zgłosi błąd o wykonywaniu skryptów, użyj zwykłego Wiersza poleceń (cmd).

## 4. Pierwsze uruchomienie

```
python main.py
```

Aplikacja sama tworzy tabele, role i status awarii, a dane już istniejące w bazie zostają. W konsoli powinny pojawić się komunikaty "Wszystkie tabele gotowe." i "Baza danych gotowa", a potem okno logowania.

Pusta baza: pierwsze konto założone w oknie rejestracji dostaje rolę Administrator. Pozostałym nadajesz role w kafelku Użytkownicy.

Baza z kontami: po aktualizacji wszystkie istniejące konta mają rolę Użytkownik, więc trzeba nadać pierwszego Administratora. W pgAdmin:

1. Kliknij bazę (cmms, nie postgres), potem Tools > Query Tool. W nagłówku karty sprawdź nazwę bazy.
2. Kliknij ikonę folderu (Open File) i wybierz sql/001_add_roles.sql.
3. W sekcji 4 skryptu odkomentuj linię z UPDATE ... 'Administrator' (usuń dwa myślniki na początku) i wpisz swój login.
4. Odznacz tekst i naciśnij F5. W Data Output zobaczysz 4 role i liczbę kont.

Skrypt można uruchamiać wielokrotnie. Jeśli pokaże "Brak tabel users/failures", baza jest pusta albo wybrana jest zła baza. Wtedy uruchom najpierw aplikację albo python setup_db.py.

## 5. Dodawanie kont z pgAdmin

Hasła są zapisane jako SHA-256 z solą, więc poniższe zapytanie liczy je tak samo jak aplikacja (wymaga PostgreSQL 11 lub nowszego). W Query Tool na bazie CMMS wklej, zmień wiersze i naciśnij F5:

```sql
-- login, hasło, stawka (zł/h), rola
INSERT INTO users (username, password_hash, salt, hourly_rate, role)
SELECT v.username,
       encode(sha256(convert_to(v.password || v.salt, 'UTF8')), 'hex'),
       v.salt, v.hourly_rate, v.role
FROM (
    SELECT t.*, md5(random()::text || clock_timestamp()::text || t.username) AS salt
    FROM (VALUES
        ('admin',      'Admin123',      0.00, 'Administrator'),
        ('kierownik',  'Kierownik123',  0.00, 'Kierownik'),
        ('technik',    'Technik123',   45.00, 'Technik'),
        ('uzytkownik', 'Haslo1234',     0.00, 'Użytkownik')
    ) AS t(username, password, hourly_rate, role)
) AS v
ON CONFLICT (username) DO NOTHING;
```

Rola musi brzmieć dokładnie: Administrator, Kierownik, Technik albo Użytkownik. Istniejące loginy są pomijane. Stawka jest potrzebna do kosztu robocizny przy zamykaniu awarii. Nie zapisuj skryptu z prawdziwymi hasłami w repozytorium.

Zmiana roli i hasła istniejącego konta:

```sql
UPDATE users SET role = 'Technik' WHERE username = 'jan';

WITH s AS (SELECT md5(random()::text || clock_timestamp()::text) AS salt)
UPDATE users
SET salt = s.salt,
    password_hash = encode(sha256(convert_to('NoweHaslo456' || s.salt, 'UTF8')), 'hex')
FROM s
WHERE username = 'jan';
```

Rolę można też zmienić w aplikacji: Administrator, kafelek Użytkownicy, zaznacz konto, wybierz rolę i kliknij Zmień rolę. Ostatniemu Administratorowi nie można odebrać roli. Zmiana działa przy następnym otwarciu funkcji, a nowe kafelki w menu pojawią się po ponownym zalogowaniu.

## 6. Role i uprawnienia

| Rola | Dostęp |
|---|---|
| Administrator | wszystkie funkcje oprócz druku raportów |
| Kierownik | Statystyki i druk raportów |
| Użytkownik | Zgłoszenie Awarii |
| Technik | Rozwiązywanie Awarii, Zatwierdź TPM, Magazyn |

Uprawnienia są w jednym miejscu, w pliku permissions.py (słownik ROLE_FEATURES). Żeby np. Administrator mógł też drukować raporty, wystarczy dopisać mu FEATURE_ANALYTICS_PRINT. Menu pokazuje tylko dozwolone kafelki, a rola jest sprawdzana w bazie przy każdym otwarciu funkcji.

## 7. Obieg awarii

1. Użytkownik zgłasza awarię w kafelku Zgłoszenie Awarii (status Zgłoszona). W historii widzi tylko własne zgłoszenia.
2. Technik w kafelku Rozwiązywanie Awarii zaznacza awarię i klika Rozpocznij naprawę (status W naprawie), a po naprawie Zakończ naprawę. Podaje datę i godzinę zakończenia oraz ewentualnie użytą część z magazynu. Awaria dostaje status Rozwiązana, a przestój i koszty liczą się automatycznie.
3. Awarię naprawioną od razu, bez zgłoszenia, Technik zapisuje przyciskiem Dodaj zakończoną awarię.

Awarie zapisane przed wprowadzeniem statusów mają status Rozwiązana.

## 8. Raport do druku

Raport mogą przygotować tylko konta z rolą Kierownik. W kafelku Statystyki jest przycisk Drukuj raport.

1. Wybierz miesiąc (lista zawiera miesiące, w których były awarie).
2. Wybierz zakres: Wszystkie maszyny albo jedną maszynę (obszar systemu z awarii w tym miesiącu). Pod listą widać, ile awarii obejmie raport.
3. Zapisz PDF zapisuje plik i otwiera go w przeglądarce PDF. Drukuj wysyła raport do domyślnej drukarki, a gdy program do PDF nie obsługuje takiego druku, otwiera plik i wydrukujesz go z niego (Ctrl+P).

Raport ma format A4 i zawiera: nagłówek z zakresem i datą wygenerowania, wskaźniki (liczba awarii, awarie otwarte, przestój, MTTR, koszty), najważniejsze obserwacje, cztery wykresy (typy awarii, Pareto przestojów, przestoje w kolejnych dniach, koszty) oraz tabelę wszystkich awarii z podsumowaniem. Dla jednej maszyny wykresy porównują jej podsystemy.

## 9. Gdy coś nie działa

| Objaw | Co sprawdzić |
|---|---|
| Konsola: "Nie udało się połączyć z PostgreSQL ... Komunikat serwera: ..." | "uwierzytelnienie hasłem nie powiodło się" (po angielsku password authentication failed) oznacza zły DB_USER lub DB_PASSWORD albo port innej instalacji. "baza danych ... nie istnieje" oznacza zły DB_NAME. "Connection refused" oznacza wyłączony serwer albo zły DB_HOST lub DB_PORT |
| Konsola: "W bazie nie ma Administratora" | krok 4, baza z kontami |
| W menu tylko Wyloguj i ostrzeżenie o roli | konto nie istnieje w bazie albo jest błąd bazy, sprawdź konsolę |
| Brak kafelka lub przycisku | rola nie ma tej funkcji (tabela w punkcie 6) |
| Drukuj otwiera plik zamiast drukować | program do PDF nie obsługuje druku z systemu, wydrukuj z niego (Ctrl+P) |
| pgAdmin: "Brak tabel users/failures" | zła lub pusta baza, patrz krok 4 |

## 10. Pliki dodane lub zmienione

Nowe: permissions.py, failure_resolve_window.py, report_generator.py, report_window.py, sql/001_add_roles.sql, requirements.txt, data.env.example, URUCHOMIENIE.md.

Zmienione: db_utils.py, main.py, main_menu.py, login_window.py, register_window.py, user_management_window.py, failure_window.py, failure_report.py, Analytics.py, setup_db.py, README.md, .gitignore.
