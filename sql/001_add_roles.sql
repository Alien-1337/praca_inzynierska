-- CMMS: role użytkowników i status awarii.
--
-- Skrypt do uruchomienia w pgAdmin 4 (Query Tool) na bazie CMMS.
-- Można go uruchamiać wielokrotnie: nie dubluje ról i nie nadpisuje ról nadanych kontom.
-- To samo robi aplikacja przy starcie (db_utils.create_tables), skrypt jest wygodny,
-- gdy chcesz zmienić bazę ręcznie i od razu nadać pierwszego Administratora.
--
-- Role:
--   Administrator - dostęp do wszystkich funkcjonalności
--   Kierownik     - dostęp do raportów i wizualizacji
--   Użytkownik    - dostęp do zgłaszania błędów
--   Technik       - dostęp do rozwiązywania błędów, aktualizowania stanu maszyn i magazynu
--
-- Status awarii: Zgłoszona, W naprawie, Rozwiązana.


-- 0) Sprawdzenie, czy to baza CMMS (tabele users i failures). Jeśli nie, skrypt przerywa się
--    z komunikatem i nic nie zmienia.
DO $$
BEGIN
    IF to_regclass('users') IS NULL OR to_regclass('failures') IS NULL THEN
        RAISE EXCEPTION
            'Brak tabel users/failures w bazie "%". Wybierz w pgAdmin bazę CMMS (nie "postgres") i otwórz Query Tool jeszcze raz. Pusta baza? Uruchom najpierw aplikację (python main.py) - utworzy tabele.',
            current_database();
    END IF;
END
$$;


-- 1) Słownik ról
CREATE TABLE IF NOT EXISTS roles (
    name        VARCHAR(30) PRIMARY KEY,
    description TEXT        NOT NULL
);

INSERT INTO roles (name, description) VALUES
    ('Administrator', 'Dostęp do wszystkich funkcjonalności'),
    ('Kierownik',     'Dostęp do raportów i wizualizacji'),
    ('Użytkownik',    'Dostęp do zgłaszania błędów'),
    ('Technik',       'Dostęp do rozwiązywania błędów, aktualizowania stanu maszyn i magazynu')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;


-- 2) Rola przypisana do użytkownika. Istniejące i nowe konta dostają 'Użytkownik',
--    wpisać można tylko rolę ze słownika.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'Użytkownik'
        CONSTRAINT users_role_fkey REFERENCES roles (name) ON UPDATE CASCADE;


-- 3) Status awarii. Dotychczasowe wpisy były już naprawione, więc dostają 'Rozwiązana',
--    nowe zgłoszenia domyślnie 'Zgłoszona'.
ALTER TABLE failures
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'Rozwiązana'
        CONSTRAINT failures_status_check
        CHECK (status IN ('Zgłoszona', 'W naprawie', 'Rozwiązana'));

ALTER TABLE failures ALTER COLUMN status SET DEFAULT 'Zgłoszona';


-- 4) Ręczne nadawanie ról (opcjonalnie). Odkomentuj, wpisz właściwy login i uruchom
--    skrypt ponownie (albo zaznacz same te linie i uruchom je osobno).
--
--    Pierwszy Administrator, bez niego nikt nie ma pełnych uprawnień:
-- UPDATE users SET role = 'Administrator' WHERE username = 'TU_WPISZ_LOGIN';
--
--    Pozostałe role:
-- UPDATE users SET role = 'Kierownik'  WHERE username = 'TU_WPISZ_LOGIN';
-- UPDATE users SET role = 'Technik'    WHERE username = 'TU_WPISZ_LOGIN';
-- UPDATE users SET role = 'Użytkownik' WHERE username = 'TU_WPISZ_LOGIN';


-- 5) Podsumowanie (pgAdmin pokaże wynik ostatniego zapytania): 4 role i liczba kont w każdej.
SELECT r.name        AS rola,
       r.description AS opis,
       count(u.id)   AS liczba_uzytkownikow
FROM roles r
LEFT JOIN users u ON u.role = r.name
GROUP BY r.name, r.description
ORDER BY r.name;

-- Lista kont z rolami:
-- SELECT id, username, role FROM users ORDER BY id;
--
-- Awarie według statusu:
-- SELECT status, count(*) FROM failures GROUP BY status;
