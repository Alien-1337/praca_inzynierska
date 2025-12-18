import tempfile
import os
from tkinter import messagebox
from datetime import date
from db_utils import get_pending_tpm_tasks  # ZMIANA FUNKCJI


def print_tpm():
    try:
        # Pobieramy zadania oczekujące (dzisiejsze + zaległe)
        tasks = get_pending_tpm_tasks()

        if not tasks:
            messagebox.showinfo("TPM", "Brak zadań do wydruku (Wszystko zrobione!).")
            return

        today_str = date.today().strftime("%d.%m.%Y")
        content = f"HARMONOGRAM ZADAŃ TPM - {today_str}\n"
        content += "=" * 60 + "\n\n"

        # task = (id, date, interval, field, type, description, STATUS)
        for i, task in enumerate(tasks, 1):
            t_id, start_date, interval, field, task_type, desc, status = task

            # Oznaczenie zaległości w wydruku
            prefix = "[!]" if "ZALEGŁE" in status else "[ ]"

            content += f"ZADANIE #{i}  -- STATUS: {status}\n"
            content += f"Dział: {field} | Typ: {task_type}\n"
            content += f"Częstotliwość: {interval}\n"
            content += f"OPIS: {desc}\n"
            content += "-" * 60 + "\n"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tf:
            tf.write(content)
            temp_path = tf.name

        os.startfile(temp_path, "print")

    except Exception as e:
        messagebox.showerror("Błąd drukowania", f"Nie udało się wydrukować:\n{e}")
