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
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        ctk.set_appearance_mode("dark")

        ctk.CTkLabel(
            self.window,
            text="Zatwierdź wykonanie zadań TPM",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=20)

        ctk.CTkLabel(
            self.window,
            text="Zaznacz zadania, które zostały wykonane, a następnie kliknij 'Zatwierdź'.",
            text_color="gray"
        ).pack(pady=(0, 10))

        self.scroll_frame = ctk.CTkScrollableFrame(self.window, width=800, height=500)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.checkboxes = {}

        try:
            self.pending_tasks = db_utils.get_pending_tpm_tasks()
        except Exception as e:
            print(f"❌ Błąd pobierania zadań TPM: {e}")
            ctk.CTkLabel(
                self.scroll_frame,
                text="Błąd pobierania zadań z bazy danych.",
                font=ctk.CTkFont(size=16),
                text_color="red"
            ).pack(pady=50)
            self.pending_tasks = []

        if not self.pending_tasks:
            ctk.CTkLabel(
                self.scroll_frame,
                text="Wszystkie zadania są aktualne! Brak zaległości.",
                font=ctk.CTkFont(size=18),
                text_color="green"
            ).pack(pady=50)
        else:
            for task in self.pending_tasks:
                try:
                    t_id, t_date, t_interval, field, t_type, desc, status = task

                    t_date = str(t_date) if t_date is not None else ""

                    status_color = "#EF4444" if "ZALEGŁE" in status else "#10B981"

                    item_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#333333")
                    item_frame.pack(pady=5, padx=5, fill="x")

                    var = ctk.BooleanVar()
                    cb = ctk.CTkCheckBox(item_frame, text="", variable=var, width=30)
                    cb.pack(side="left", padx=10)
                    self.checkboxes[t_id] = var

                    info_text = f"[{status}]  {field}  |  {t_type}  |  {t_date}\n{desc}"
                    ctk.CTkLabel(
                        item_frame,
                        text=info_text,
                        anchor="w",
                        justify="left",
                        font=ctk.CTkFont(size=14)
                    ).pack(side="left", padx=10, pady=10)

                    ctk.CTkLabel(
                        item_frame,
                        text=status,
                        text_color=status_color,
                        font=ctk.CTkFont(weight="bold")
                    ).pack(side="right", padx=20)

                except Exception as e:
                    print(f"⚠️ Błąd renderowania zadania {task}: {e}")

        # Przyciski
        btn_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_frame.pack(pady=20, padx=20, fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Zatwierdź wybrane",
            command=self.confirm_selection,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=50
        ).pack(side="left", expand=True, fill="x", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🔙 Powrót",
            command=self.on_close,
            fg_color="#555",
            hover_color="#444",
            height=50
        ).pack(side="left", expand=True, fill="x", padx=(10, 0))

    def confirm_selection(self):
        selected_ids = [t_id for t_id, var in self.checkboxes.items() if var.get()]

        if not selected_ids:
            messagebox.showwarning("Brak wyboru", "Nie zaznaczono żadnych zadań.")
            return

        try:
            for t_id in selected_ids:
                db_utils.mark_task_as_done(t_id)

            messagebox.showinfo("Sukces", f"Zatwierdzono {len(selected_ids)} zadań.")
            self.window.destroy()
            self.back_callback()

        except Exception as e:
            print(f"❌ Błąd zatwierdzania zadań: {e}")
            messagebox.showerror("Błąd", f"Nie udało się zatwierdzić zadań:\n{e}")

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_accept_window(username, back_callback):
    AcceptTPMWindow(username, back_callback)