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
        self.master.geometry("1200x850")
        self.master.state("zoomed")

        # --- POBRANIE DANYCH Z BAZY ---
        # Indeksy w db_utils:
        # 0:id, 2:obszar, 5:data, 9:czas
        # 15:uzyta_czesc (NOWE), 16:robocizna, 17:czesci, 18:total
        self.raw_data = db_utils.get_failure_history()

        # --- GUI ---
        self.main_frame = ctk.CTkFrame(self.master, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        # Pasek górny
        self.top_bar = ctk.CTkFrame(self.main_frame, height=60, corner_radius=0, fg_color="#1a1a1a")
        self.top_bar.pack(side="top", fill="x")

        title_label = ctk.CTkLabel(self.top_bar, text="DASHBOARD ANALITYCZNY",
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

        # --- NOWA ZAKŁADKA ---
        self.tab_costs = self.tab_view.add("KOSZTY (MIESIĄC)")

        if not self.raw_data:
            ctk.CTkLabel(self.tab_overview, text="Brak danych w bazie.\nDodaj awarie, aby zobaczyć wykresy.",
                         font=("Arial", 20)).pack(pady=50)
        else:
            self.create_overview_tab()
            self.create_machines_tab()
            self.create_monthly_performance_tab()
            self.create_costs_tab()

    def close_window(self):
        self.master.destroy()
        self.back_callback()

    # ==========================================
    # ZAKŁADKA 1: KPI OGÓLNE
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
        ctk.CTkLabel(card, text=value, font=("Arial", 26, "bold"), text_color=color).pack(pady=10)

    def draw_pie_chart(self, parent):
        # Index 12 to typ awarii
        types = [row[12] for row in self.raw_data]
        counts = Counter(types)
        if not counts: return

        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor('#2b2b2b')
        ax.pie(counts.values(), labels=counts.keys(), autopct='%1.1f%%', startangle=90)
        for text in ax.texts: text.set_color('white')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

    # ==========================================
    # ZAKŁADKA 2: MASZYNY (PARETO)
    # ==========================================
    def create_machines_tab(self):
        header = ctk.CTkFrame(self.tab_machines, fg_color="transparent")
        header.pack(fill="x", pady=10)
        ctk.CTkLabel(header, text="Najbardziej Awaryjne Obszary (Top 5)", font=("Arial", 18, "bold")).pack()

        plot_frame = ctk.CTkFrame(self.tab_machines, fg_color="#2b2b2b")
        plot_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Index 2 to Obszar/Maszyna
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
    # ZAKŁADKA 3: WYDAJNOŚĆ MIESIĘCZNA
    # ==========================================
    def create_monthly_performance_tab(self):
        ctk.CTkLabel(self.tab_stats, text=f"Średni czas naprawy (dzień po dniu) - {datetime.now().strftime('%B %Y')}",
                     font=("Arial", 18, "bold")).pack(pady=15)

        plot_frame = ctk.CTkFrame(self.tab_stats, fg_color="#2b2b2b")
        plot_frame.pack(fill="both", expand=True, padx=20, pady=10)

        today = date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        days_in_month = list(range(1, last_day + 1))
        daily_stats = {day: [] for day in days_in_month}

        for row in self.raw_data:
            try:
                failure_date = datetime.strptime(row[5], "%Y-%m-%d").date()
                if failure_date.year == today.year and failure_date.month == today.month:
                    downtime = row[9]
                    daily_stats[failure_date.day].append(downtime)
            except ValueError:
                continue

        avg_downtimes = []
        for day in days_in_month:
            times = daily_stats[day]
            if times:
                avg = sum(times) / len(times)
                avg_downtimes.append(avg)
            else:
                avg_downtimes.append(0)

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        ax.plot(days_in_month, avg_downtimes, marker='o', linestyle='-', color='#E59400', linewidth=2)
        ax.fill_between(days_in_month, avg_downtimes, color='#E59400', alpha=0.1)

        ax.set_title('Średni czas przestoju [min]', color='white')
        ax.set_xticks(days_in_month)
        ax.tick_params(colors='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.grid(True, linestyle=':', alpha=0.3)

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ==========================================
    # ZAKŁADKA 4: KOSZTY (NAPRAWIONA)
    # ==========================================
    def create_costs_tab(self):
        current_date_str = datetime.now().strftime('%B %Y')
        ctk.CTkLabel(self.tab_costs, text=f"Analiza Finansowa Awarii - {current_date_str}",
                     font=("Arial", 18, "bold")).pack(pady=10)

        kpi_frame = ctk.CTkFrame(self.tab_costs, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=10)

        today = date.today()

        monthly_labor_cost = 0.0
        monthly_parts_cost = 0.0
        monthly_total_cost = 0.0

        machine_costs = {}

        for row in self.raw_data:
            try:
                # Sprawdzenie czy wiersz ma komplet danych (19 kolumn)
                if len(row) < 19:
                    continue

                f_date = datetime.strptime(row[5], "%Y-%m-%d").date()

                if f_date.year == today.year and f_date.month == today.month:
                    # POPRAWIONE INDEKSY: 16, 17, 18 (bo 15 to 'used_part' - tekst)
                    labor = row[16] if row[16] else 0.0
                    parts = row[17] if row[17] else 0.0
                    total = row[18] if row[18] else 0.0

                    monthly_labor_cost += labor
                    monthly_parts_cost += parts
                    monthly_total_cost += total

                    machine_name = row[2]
                    if machine_name:
                        machine_costs[machine_name] = machine_costs.get(machine_name, 0.0) + total

            except (ValueError, IndexError, TypeError):
                continue

        self.create_kpi_card(kpi_frame, "Robocizna (Miesiąc)", f"{monthly_labor_cost:.2f} PLN", "#3B8ED0")
        self.create_kpi_card(kpi_frame, "Części (Miesiąc)", f"{monthly_parts_cost:.2f} PLN", "#E59400")
        self.create_kpi_card(kpi_frame, "SUMA KOSZTÓW", f"{monthly_total_cost:.2f} PLN", "#FF5555")

        plot_frame = ctk.CTkFrame(self.tab_costs, fg_color="#2b2b2b")
        plot_frame.pack(fill="both", expand=True, padx=20, pady=10)

        if not machine_costs:
            ctk.CTkLabel(plot_frame, text="Brak kosztów w tym miesiącu.", font=("Arial", 16)).pack(pady=50)
            return

        sorted_machines = dict(sorted(machine_costs.items(), key=lambda item: item[1], reverse=True)[:7])

        labels = list(sorted_machines.keys())
        values = list(sorted_machines.values())

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')

        bars = ax.bar(labels, values, color='#FF5555', alpha=0.8)
        ax.bar_label(bars, fmt='%.2f zł', color='white', padding=3)

        ax.set_title('Koszty napraw wg Maszyn/Obszarów (Top 7)', color='white')
        ax.set_ylabel('Koszt [PLN]', color='white')

        ax.tick_params(colors='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')

        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

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