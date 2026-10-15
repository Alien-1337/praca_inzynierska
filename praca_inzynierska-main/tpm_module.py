import tempfile
import os
from tkinter import messagebox
from datetime import date
from db_utils import get_pending_tpm_tasks


def print_tpm():
    try:
        tasks = get_pending_tpm_tasks()

        if not tasks:
            messagebox.showinfo("TPM", "Brak zadań do wydruku (Wszystko zrobione!).")
            return

        today_str = date.today().strftime("%d.%m.%Y")

        content = []
        content.append(f"HARMONOGRAM ZADAŃ TPM - {today_str}")
        content.append("=" * 60)
        content.append("")

        # task = (id, date, interval, field, type, description, status)
        for i, task in enumerate(tasks, 1):
            try:
                t_id, start_date, interval, field, task_type, desc, status = task
            except ValueError:
                print("❌ Błąd struktury danych:", task)
                continue

            prefix = "[!]" if "ZALEGŁE" in str(status).upper() else "[ ]"

            content.append(f"{prefix} ZADANIE #{i}  -- STATUS: {status}")
            content.append(f"Dział: {field} | Typ: {task_type}")
            content.append(f"Częstotliwość: {interval}")
            content.append(f"OPIS: {desc}")
            content.append("-" * 60)

        final_text = "\n".join(content)

        # Tworzenie pliku tymczasowego
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tf:
            tf.write(final_text)
            temp_path = tf.name

        # Drukowanie (Windows)
        try:
            os.startfile(temp_path, "print")
        except Exception as e:
            print("❌ Problem z drukowaniem:", e)
            messagebox.showinfo("TPM", f"Plik zapisany:\n{temp_path}")

    except Exception as e:
        print("❌ Błąd główny TPM:", e)
        messagebox.showerror("Błąd drukowania", f"Nie udało się wydrukować:\n{e}")