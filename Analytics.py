import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from collections import Counter
import db_utils
from datetime import datetime, date
import calendar

# Ustawienie stylu wykresów
plt.style.use('dark_background')


class AnalyticsWindow:
    def __init__(self, master, username, back_callback):
        self.master = master
        self.username = username
        self.back_callback = back_callback

        self.master.title("Centrum Analityki CMMS")
        self.master.geometry("1200x800")
        self.master.state("zoomed")

        # --- POBRANIE DANYCH Z BAZY ---
        self.raw_data = db_utils.get_failure_history()
        # Indeksy: 0:id, 2:maszyna, 5:data(YYYY-MM-DD), 9:czas_minuty, 12:typ

        # --- GUI ---
        self.main_frame = ctk.CTkFrame(self.master, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        # Pasek górny
        self.top_bar = ctk.CTkFrame(self.main_frame, height=60, corner_radius=0, fg_color="#1a1a1a")
        self.top_bar.pack(side="top", fill="x")

        title_label = ctk.CTkLabel(self.top_bar, text="DASHBOARD MIESIĘCZNY",
                                   font=ctk.CTkFont(size=24, weight="bold"), text_color="#3B8ED0")
        title_label.pack(side="left", padx=20, pady=10)

        btn_back = ctk.CTkButton(self.top_bar, text="WRÓĆ DO MENU",
                                 fg_color="transparent", border_width=1, border_color="#FF5555", text_color="#FF5555",
                                 command=self.close_window)
        btn_back.pack(side="right", padx=20, pady=10)

        # Zakładki
        self.tab_view = ctk.CTkTabview(self.main_frame, corner_radius=15)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_overview = self.tab_view.add("PRZEGLĄD & KPI")
        self.tab_machines = self.tab_view.add("MASZYNY (PARETO)")
        self.tab_stats = self.tab_view.add("WYDAJNOŚĆ (MIESIĄC)")

        if not self.raw_data:
            ctk.CTkLabel(self.tab_overview, text="Brak danych w bazie.\nDodaj awarie, aby zobaczyć wykresy.",
                         font=("Arial", 20)).pack(pady=50)
        else:
            self.create_overview_tab()
            self.create_machines_tab()
            self.create_monthly_performance_tab()

    def close_window(self):
        self.master.destroy()
        self.back_callback()

    # ==========================================
    # ZAKŁADKA 1: KPI
    # ==========================================
    def create_overview_tab(self):
        kpi_frame = ctk.CTkFrame(self.tab_overview, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=20)

        total_failures = len(self.raw_data)
        total_downtime = sum([row[9] for row in self.raw_data])
        mttr = round(total_downtime / total_failures, 1) if total_failures > 0 else 0

        self.create_kpi_card(kpi_frame, "Liczba Awarii (Total)", str(total_failures), "#3B8ED0")
        self.create_kpi_card(kpi_frame, "Suma Przestojów", f"{total_downtime} min", "#FF5555")
        self.create_kpi_card(kpi_frame, "Średnie MTTR", f"{mttr} min", "#2CC985")

        chart_frame = ctk.CTkFrame(self.tab_overview, fg_color="#2b2b2b", corner_radius=15)
        chart_frame.pack(fill="both", expand=True, pady=10, padx=10)

        ctk.CTkLabel(chart_frame, text="Rozkład Typów Awarii", font=("Arial", 16, "bold")).pack(pady=10)
        self.draw_pie_chart(chart_frame)

    def create_kpi_card(self, parent, title, value, color):
        card = ctk.CTkFrame(parent, width=250, height=100, corner_radius=15, fg_color="#333333")
        card.pack(side="left", padx=10, expand=True, fill="x")
        ctk.CTkLabel(card, text=title, font=("Arial", 12), text_color="gray").pack(pady=(15, 5))
        ctk.CTkLabel(card, text=value, font=("Arial", 28, "bold"), text_color=color).pack(pady=10)

    def draw_pie_chart(self, parent):
        types = [row[12] for row in self.raw_data]
        counts = Counter(types)
        if not counts: return

        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor('#2b2b2b')
        ax.pie(counts.values(), labels=counts.keys(), autopct='%1.1f%%', startangle=90)
        for text in ax.texts: text.set_color('slategray')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

    # ==========================================
    # ZAKŁADKA 2: MASZYNY
    # ==========================================
    def create_machines_tab(self):
        header = ctk.CTkFrame(self.tab_machines, fg_color="transparent")
        header.pack(fill="x", pady=10)
        ctk.CTkLabel(header, text="Najbardziej Awaryjne Maszyny", font=("Arial", 18, "bold")).pack()

        plot_frame = ctk.CTkFrame(self.tab_machines, fg_color="#2b2b2b")
        plot_frame.pack(fill="both", expand=True, padx=20, pady=10)

        machines = [row[2] for row in self.raw_data]
        common = Counter(machines).most_common(5)
        if not common: return

        labels, values = zip(*common)

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')
        bars = ax.bar(labels, values, color='#3B8ED0')
        ax.bar_label(bars, color='white')

        ax.tick_params(colors='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ==========================================
    # ZAKŁADKA 3: WYDAJNOŚĆ MIESIĘCZNA (NOWA)
    # ==========================================
    def create_monthly_performance_tab(self):
        ctk.CTkLabel(self.tab_stats, text=f"Średni czas naprawy (dzień po dniu) - {datetime.now().strftime('%B %Y')}",
                     font=("Arial", 18, "bold")).pack(pady=15)

        plot_frame = ctk.CTkFrame(self.tab_stats, fg_color="#2b2b2b")
        plot_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. Przygotowanie danych kalendarzowych na obecny miesiąc
        today = date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        days_in_month = list(range(1, last_day + 1))

        # Słownik do sumowania czasów: {1: [30, 45], 2: [], 3: [120]...}
        daily_stats = {day: [] for day in days_in_month}

        # 2. Filtrowanie i przypisywanie awarii do dni
        for row in self.raw_data:
            # row[5] to data w formacie "YYYY-MM-DD"
            try:
                failure_date = datetime.strptime(row[5], "%Y-%m-%d").date()
                # Sprawdzamy czy awaria jest z tego roku i miesiąca
                if failure_date.year == today.year and failure_date.month == today.month:
                    downtime = row[9]  # Czas awarii
                    daily_stats[failure_date.day].append(downtime)
            except ValueError:
                continue  # Jeśli data jest źle sformatowana, pomijamy

        # 3. Obliczanie średniej dla każdego dnia
        # Jeśli brak awarii w danym dniu -> 0
        avg_downtimes = []
        for day in days_in_month:
            times = daily_stats[day]
            if times:
                avg = sum(times) / len(times)
                avg_downtimes.append(avg)
            else:
                avg_downtimes.append(0)

        # 4. Rysowanie wykresu
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        # Wykres liniowy z kropkami
        ax.plot(days_in_month, avg_downtimes, marker='o', linestyle='-', color='#E59400', linewidth=2, markersize=6)

        # Wypełnienie kolorem pod wykresem (dla efektu)
        ax.fill_between(days_in_month, avg_downtimes, color='#E59400', alpha=0.1)

        ax.set_title('Średni czas przestoju [min]', color='white')
        ax.set_xlabel('Dzień miesiąca', color='white')
        ax.set_ylabel('Minuty', color='white')

        # Oś X - pokazujemy wszystkie dni
        ax.set_xticks(days_in_month)
        # Jeśli dni jest dużo, obracamy etykiety
        if last_day > 20:
            ax.tick_params(axis='x', rotation=90, colors='white', labelsize=8)
        else:
            ax.tick_params(axis='x', colors='white')

        ax.tick_params(axis='y', colors='white')
        ax.grid(True, linestyle=':', alpha=0.3)

        # Usunięcie ramek
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


def show_analytics_window(username, back_callback):
    window = ctk.CTkToplevel()
    app = AnalyticsWindow(window, username, back_callback)

    def on_close():
        window.destroy()
        back_callback()

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()
