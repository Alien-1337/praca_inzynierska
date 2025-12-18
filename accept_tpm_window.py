import customtkinter as ctk
from tkinter import messagebox
import db_utils


class AcceptTPMWindow:
    def __init__(self, username, back_callback):
        self.username = username
        self.back_callback = back_callback

        self.window = ctk.CTkToplevel()
        self.window.title("Zatwierdzanie zadań TPM")
        self.window.geometry("900x700")
        self.window.grab_set()  # Okno modalne
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        ctk.set_appearance_mode("dark")

        # Nagłówek
        ctk.CTkLabel(self.window, text=f"Zatwierdź wykonanie zadań TPM",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        ctk.CTkLabel(self.window, text="Zaznacz zadania, które zostały wykonane, a następnie kliknij 'Zatwierdź'.",
                     text_color="gray").pack(pady=(0, 10))

        # Kontener na listę zadań (Scroll)
        self.scroll_frame = ctk.CTkScrollableFrame(self.window, width=800, height=500)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Pobranie zadań z bazy
        self.pending_tasks = db_utils.get_pending_tpm_tasks()

        self.checkboxes = {}  # Słownik do przechowywania zmiennych checkboxów {task_id: checkbox_var}

        if not self.pending_tasks:
            ctk.CTkLabel(self.scroll_frame, text="Wszystkie zadania są aktualne! Brak zaległości.",
                         font=ctk.CTkFont(size=18), text_color="green").pack(pady=50)
        else:
            for task in self.pending_tasks:
                # task = (id, date, interval, field, type, description, STATUS)
                t_id, _, _, field, t_type, desc, status = task

                # Ramka dla jednego zadania
                item_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#333333")
                item_frame.pack(pady=5, padx=5, fill="x")

                # Kolor statusu
                status_color = "#EF4444" if "ZALEGŁE" in status else "#10B981"  # Czerwony / Zielony

                # Checkbox
                var = ctk.BooleanVar()
                cb = ctk.CTkCheckBox(item_frame, text="", variable=var, width=30)
                cb.pack(side="left", padx=10)
                self.checkboxes[t_id] = var

                # Opis zadania
                info_text = f"[{status}] {field} | {t_type}\n{desc}"
                lbl = ctk.CTkLabel(item_frame, text=info_text, anchor="w", justify="left",
                                   font=ctk.CTkFont(size=14))
                lbl.pack(side="left", padx=10, pady=10)

                # Etykieta statusu z boku
                status_lbl = ctk.CTkLabel(item_frame, text=status, text_color=status_color,
                                          font=ctk.CTkFont(weight="bold"))
                status_lbl.pack(side="right", padx=20)

        # Przycisk Zatwierdź
        btn_confirm = ctk.CTkButton(self.window, text="Zatwierdź Wybrane",
                                    command=self.confirm_selection,
                                    font=ctk.CTkFont(size=16, weight="bold"),
                                    fg_color="green", height=50)
        btn_confirm.pack(pady=20, padx=20, fill="x")

    def confirm_selection(self):
        selected_ids = []
        for t_id, var in self.checkboxes.items():
            if var.get():
                selected_ids.append(t_id)

        if not selected_ids:
            messagebox.showwarning("Brak wyboru", "Nie zaznaczono żadnych zadań.")
            return

        # Aktualizacja w bazie
        count = 0
        for t_id in selected_ids:
            db_utils.mark_task_as_done(t_id)
            count += 1

        messagebox.showinfo("Sukces", f"Zatwierdzono {count} zadań.")
        self.window.destroy()
        self.back_callback()  # Odświeżenie menu (opcjonalne)

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_accept_window(username, back_callback):
    AcceptTPMWindow(username, back_callback)
