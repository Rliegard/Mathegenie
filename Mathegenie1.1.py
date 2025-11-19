# ==============================================================================
# PROJEKT: Mathegenie - Adaptiver Mathetrainer
# AUTOR:   Rainer Liegard
# DATUM:   07. November 2025
# VERSION: 1.1 (Integration des "Zurück zum Hauptmenü" Buttons in der Session)
# ==============================================================================
#
# Eine plattformübergreifende (Tkinter) Anwendung zur Erstellung und Durchführung
# von adaptiven Mathematikübungen, basierend auf Thema und Schwierigkeitsgrad.
#
# Haupt-Features der Version 1.3:
# 1. Stabile Übungslogik mit Aufgaben-Generierung für vier Themen (Zahlenraum, Terme, Geometrie, Statistik).
# 2. Zeitgesteuerte Übungssitzungen mit automatischer Bewertung und Speicherung.
# 3. Datenbank-Persistenz (SQLite) für Lernergebnisse und eine Fortschrittsanzeige (Treeview) mit Lösch-/Bearbeiten-Funktion.
# 4. **Verbesserte Usability:** Ein "Abbrechen & Zurück zum Hauptmenü"-Button wurde in das Übungsfenster (`AufgabenSession`) integriert, um die Fullscreen-Session vorzeitig und kontrolliert verlassen zu können.
# 5. Fullscreen-Modus und grundlegende Hotkeys (Alt+F4, Alt+L).
#
# Abhängigkeiten & Voraussetzungen:
# - Python 3.x
# - Tkinter (Standard in Python)
# - sqlite3 (Standard in Python)
#
################################################################################

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import random
from datetime import datetime
import time
import operator

# --- HILFSKLASSEN ---

class ToolTip:
    """Eine Klasse zur Erstellung einfacher Tooltips für Tkinter Widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        "Zeigt den Tooltip-Text an."
        if self.tip_window or not self.text:
            return

        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "10", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        "Verbirgt den Tooltip."
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class DatabaseManager:
    """Verwaltet die SQLite-Datenbank für Lernergebnisse."""
    def __init__(self, db_name="mathegenie.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        """Erstellt die Tabelle, falls sie noch nicht existiert."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                correct_count INTEGER NOT NULL,
                total_count INTEGER NOT NULL,
                duration REAL,
                timestamp TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_result(self, topic, correct, total, duration):
        """Speichert ein neues Lernergebnis."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO results (topic, correct_count, total_count, duration, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (topic, correct, total, duration, timestamp))
        self.conn.commit()

    def get_all_results(self):
        """Ruft alle gespeicherten Ergebnisse ab."""
        self.cursor.execute("SELECT id, topic, correct_count, total_count, duration, timestamp FROM results ORDER BY timestamp DESC")
        return self.cursor.fetchall()

    def delete_result(self, result_id):
        """Löscht ein Ergebnis anhand der ID."""
        self.cursor.execute("DELETE FROM results WHERE id = ?", (result_id,))
        self.conn.commit()

    def update_result(self, result_id, new_correct, new_total, new_duration):
        """Bearbeitet ein Ergebnis anhand der ID (wird im UI simuliert)."""
        self.cursor.execute("""
            UPDATE results SET correct_count = ?, total_count = ?, duration = ?
            WHERE id = ?
        """, (new_correct, new_total, new_duration, result_id))
        self.conn.commit()

# --- AUFGABEN-ALGORITHMEN ---

class AufgabenGenerator:
    """Erstellt mathematische Aufgaben und deren Lösungen basierend auf Thema und Schwierigkeit."""

    def __init__(self, topic, difficulty, num_questions=10):
        self.topic = topic
        self.difficulty = difficulty
        self.num_questions = num_questions
        self.questions = []
        self._generate_questions()

    def _get_params(self):
        """Definiert Zahlenbereiche, Termlängen und Komplexität basierend auf dem Schwierigkeitsgrad."""
        if self.difficulty == "Leicht":
            return {'range': (1, 10), 'operators': ['+', '-'], 'vars': 1, 'max_terms': 2, 'decimals': 0}
        elif self.difficulty == "Mittel":
            return {'range': (1, 100), 'operators': ['+', '-', '*'], 'vars': 1, 'max_terms': 3, 'decimals': 1}
        else: # Schwer
            return {'range': (10, 1000), 'operators': ['+', '-', '*', '/'], 'vars': 2, 'max_terms': 4, 'decimals': 2}

    def _generate_questions(self):
        """Hauptmethode zum Erstellen aller Aufgaben."""
        for i in range(self.num_questions):
            if self.topic == "Zahlenraum-Training":
                q, a = self._generate_zahlenraum()
            elif self.topic == "Terme & Gleichungen":
                q, a = self._generate_terme()
            elif self.topic == "Geometrie":
                q, a = self._generate_geometrie()
            elif self.topic == "Statistik":
                q, a = self._generate_statistik()
            else:
                q, a = "Fehler: Unbekanntes Thema.", 0

            self.questions.append({'id': i + 1, 'question': q, 'correct_answer': a, 'user_answer': None})

    # --- Themen-Algorithmen ---

    def _generate_zahlenraum(self):
        """Erstellt arithmetische Aufgaben."""
        params = self._get_params()
        op_map = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}

        if params['decimals'] == 0 and '/' in params['operators']:
            params['operators'].remove('/')

        op = random.choice(params['operators'])

        if op == '/':
            answer = random.randint(params['range'][0] * 2, params['range'][1] // 2)
            divisor = random.randint(2, 9)
            num1 = answer * divisor
            question = f"{num1} {op} {divisor} ="
        else:
            num1 = random.randint(params['range'][0], params['range'][1])
            num2 = random.randint(params['range'][0], params['range'][1])

            if op == '-' and num1 < num2:
                num1, num2 = num2, num1

            answer = op_map[op](num1, num2)
            question = f"{num1} {op} {num2} ="

        return question, round(answer, params['decimals'])

    def _generate_terme(self):
        """Erstellt Aufgaben zum Vereinfachen von Termen."""
        params = self._get_params()
        var_list = ['x', 'y', 'a', 'b']
        vars = random.sample(var_list, params['vars'])
        max_coeff = params['range'][1] // 5

        term_parts = []
        answer_parts = {v: 0 for v in vars}
        answer_parts['const'] = 0

        for _ in range(params['max_terms']):
            coeff = random.randint(-max_coeff, max_coeff)

            if random.random() < 0.7 and vars:
                var = random.choice(vars)
                term_parts.append(f"{coeff}{var}")
                answer_parts[var] += coeff
            else:
                term_parts.append(str(coeff))
                answer_parts['const'] += coeff

        # Vereinfachte Berechnung des numerischen Werts des Terms (für Termwert-Aufgabe)
        x_val, y_val = 2, 3

        solution_value = 0
        for part in term_parts:
            coeff = 0
            if 'x' in part:
                coeff = int(part.replace('x', '')) if part.replace('x', '') not in ('', '+', '-') else 1 if part.startswith('+') else -1 if part.startswith('-') else int(part.replace('x', ''))
                solution_value += coeff * x_val
            elif 'y' in part:
                coeff = int(part.replace('y', '')) if part.replace('y', '') not in ('', '+', '-') else 1 if part.startswith('+') else -1 if part.startswith('-') else int(part.replace('y', ''))
                solution_value += coeff * y_val
            elif part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
                solution_value += int(part)

        question = "Setze x=2 (und y=3, falls vorhanden) ein und berechne den Termwert: " + " ".join([p if p.startswith('-') else ('+' + p) if i > 0 else p for i, p in enumerate(term_parts)]).replace("+ +", "+ ").replace("- -", "+ ").replace("+ -", "- ")

        return question, solution_value

    def _generate_geometrie(self):
        """Erstellt geometrische Aufgaben (Umfang, Fläche)."""
        params = self._get_params()
        shape = random.choice(['Rechteck', 'Kreis', 'Dreieck'])
        unit = "cm"

        if shape == 'Rechteck':
            length = random.randint(params['range'][0], params['range'][1] // 2)
            width = random.randint(params['range'][0], length)

            q_type = random.choice(['Umfang', 'Fläche'])
            if q_type == 'Umfang':
                question = f"Berechne den Umfang eines Rechtecks mit Länge {length}{unit} und Breite {width}{unit}."
                answer = 2 * (length + width)
            else:
                question = f"Berechne die Fläche eines Rechtecks mit Länge {length}{unit} und Breite {width}{unit}."
                answer = length * width

        elif shape == 'Kreis':
            radius = random.randint(params['range'][0], params['range'][1] // 5)
            q_type = random.choice(['Umfang', 'Fläche'])

            if q_type == 'Umfang':
                question = f"Berechne den Umfang eines Kreises mit Radius {radius}{unit}. Runde auf zwei Nachkommastellen (Nutze 3.14159)."
                answer = 2 * 3.14159 * radius
            else:
                question = f"Berechne die Fläche eines Kreises mit Radius {radius}{unit}. Runde auf zwei Nachkommastellen (Nutze 3.14159)."
                answer = 3.14159 * (radius ** 2)

            return question, round(answer, 2)

        else: # Dreieck (Fläche)
            base = random.randint(params['range'][0], params['range'][1] // 2)
            height = random.randint(params['range'][0], base)
            question = f"Berechne die Fläche eines Dreiecks mit Grundseite {base}{unit} und Höhe {height}{unit}."
            answer = 0.5 * base * height

        return question, round(answer, params['decimals'])

    def _generate_statistik(self):
        """Erstellt statistische Aufgaben (Mittelwert, Median)."""
        params = self._get_params()

        data_size = random.randint(5, 10)
        data = [random.randint(params['range'][0], params['range'][1] // 2) for _ in range(data_size)]

        q_type = random.choice(['Mittelwert', 'Median'])

        if q_type == 'Mittelwert':
            question = f"Berechne den Mittelwert der folgenden Datenreihe: {', '.join(map(str, data))}. Runde auf eine Nachkommastelle."
            answer = sum(data) / len(data)
            return question, round(answer, 1)

        else: # Median
            data.sort()
            question = f"Berechne den Median der folgenden sortierten Datenreihe: {', '.join(map(str, data))}."
            n = len(data)
            if n % 2 == 1:
                answer = data[n // 2]
            else:
                answer = (data[n // 2 - 1] + data[n // 2]) / 2

            return question, answer

# --- ÜBUNGSSESSION KLASSE ---

class AufgabenSession:
    """Verwaltet das Tkinter-Fenster für eine Übungssitzung."""
    def __init__(self, parent_app, topic, difficulty):
        self.parent_app = parent_app
        self.topic = topic
        self.difficulty = difficulty

        self.num_questions = 10
        self.time_limit = self._get_time_limit(difficulty)

        self.generator = AufgabenGenerator(topic, difficulty, self.num_questions)
        self.current_question_index = 0
        self.start_time = time.time()
        self.time_left = self.time_limit
        self.timer_id = None

        self._create_session_window()

    def _get_time_limit(self, difficulty):
        """Liefert das Zeitlimit in Sekunden (Simulation der Komplexität)."""
        if difficulty == "Leicht":
            return 60  # 1 Minute
        elif difficulty == "Mittel":
            return 120 # 2 Minuten
        else: # Schwer
            return 240 # 4 Minuten

    def _create_session_window(self):
        """Erstellt das Übungsfenster (Toplevel)."""
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title(f"Übung: {self.topic} ({self.difficulty})")

        self.window.attributes('-fullscreen', True)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel_session) # X-Button abfangen

        self.frame = tk.Frame(self.window, bg="#f5f5f5")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)

        # Titel und Timer
        tk.Label(self.frame, text=f"Aufgaben: {self.topic} ({self.difficulty})",
                 font=("Arial", 32, "bold"), bg="#f5f5f5").pack(pady=(10, 20))

        self.timer_label = tk.Label(self.frame, text=f"Verbleibende Zeit: {self.time_left}s",
                                    font=("Courier", 18), fg="red", bg="#f5f5f5")
        self.timer_label.pack(pady=10)

        # Fragebereich
        self.question_label = tk.Label(self.frame, text="", font=("Arial", 20),
                                       wraplength=800, justify=tk.CENTER, bg="#f5f5f5")
        self.question_label.pack(pady=30)

        # Eingabefeld
        self.answer_entry = ttk.Entry(self.frame, font=("Arial", 20), justify=tk.CENTER)
        self.answer_entry.pack(pady=10, ipadx=50, ipady=10)
        self.answer_entry.bind('<Return>', lambda e: self._check_answer())

        # Navigations-Button
        self.next_button = ttk.Button(self.frame, text="Antwort prüfen & Weiter >>",
                                      command=self._check_answer, style='Big.TButton')
        self.next_button.pack(pady=20)

        # --- NEUER ABBRUCH-BUTTON ---
        self.cancel_button = ttk.Button(self.frame, text="🛑 Übung abbrechen & zum Hauptmenü",
                                        command=self._cancel_session, style='TButton')
        self.cancel_button.pack(pady=40)

        self._update_question()
        self._start_timer()

    def _cancel_session(self):
        """Bricht die Übung ab und kehrt zum Hauptmenü zurück."""
        if messagebox.askyesno("Abbrechen bestätigen",
                               "Möchten Sie die Übung wirklich abbrechen? Der aktuelle Fortschritt geht dabei verloren.",
                               parent=self.window):
            if self.timer_id:
                self.window.after_cancel(self.timer_id)
            self.window.destroy()
            self.parent_app.show_main_menu()
            print("Übung abgebrochen. Zurück zum Hauptmenü.")

    def _start_timer(self):
        """Startet den Countdown-Timer."""
        self.time_left = self.time_limit
        self.timer_label.config(text=f"Verbleibende Zeit: {self.time_left}s")
        self._countdown()

    def _countdown(self):
        """Aktualisiert den Timer jede Sekunde."""
        if self.time_left > 0:
            self.time_left -= 1
            self.timer_label.config(text=f"Verbleibende Zeit: {self.time_left}s")
            self.timer_id = self.window.after(1000, self._countdown)
        else:
            self._finish_session(timeout=True)

    def _update_question(self):
        """Zeigt die aktuelle Frage an."""
        if self.current_question_index < self.num_questions:
            q_data = self.generator.questions[self.current_question_index]
            self.question_label.config(text=f"Frage {q_data['id']}/{self.num_questions}:\n{q_data['question']}")
            self.answer_entry.delete(0, tk.END)

            if self.current_question_index == self.num_questions - 1:
                self.next_button.config(text="Antwort prüfen & Beenden (Letzte Frage)")
            else:
                self.next_button.config(text="Antwort prüfen & Weiter >>")
        else:
            self._finish_session()

    def _check_answer(self):
        """Prüft die Antwort des Benutzers und geht zur nächsten Frage."""
        if self.current_question_index >= self.num_questions:
            self._finish_session()
            return

        user_input = self.answer_entry.get().strip().replace(',', '.')
        q_data = self.generator.questions[self.current_question_index]

        try:
            user_answer = float(user_input)
            q_data['user_answer'] = user_answer
        except ValueError:
            q_data['user_answer'] = "Ungültige Eingabe"

        self.current_question_index += 1
        self._update_question()

    def _finish_session(self, timeout=False):
        """Beendet die Übung, wertet aus und speichert in der DB."""
        if self.timer_id:
            self.window.after_cancel(self.timer_id)

        elapsed_time = self.time_limit - self.time_left if not timeout else self.time_limit

        correct_count = 0
        total_count = self.num_questions

        for q in self.generator.questions:
            # Toleranz für Gleitkommazahlen (0.1)
            if isinstance(q['user_answer'], (int, float)) and abs(q['user_answer'] - q['correct_answer']) < 0.1:
                correct_count += 1

        full_topic = f"{self.topic} ({self.difficulty})"
        self.parent_app.db.save_result(full_topic, correct_count, total_count, elapsed_time)

        result_msg = f"⏱️ Übungszeit abgelaufen!" if timeout else "✅ Übung beendet!"
        result_msg += (f"\n\nThema: {full_topic}\n"
                       f"Richtige Antworten: {correct_count} von {total_count}\n"
                       f"Genutzte Zeit: {elapsed_time:.1f}s / {self.time_limit}s\n"
                       f"Ergebnis in Datenbank gespeichert.")

        messagebox.showinfo("Übungsergebnis", result_msg)

        self.window.destroy()
        self.parent_app.show_main_menu()

# --- HAUPTANWENDUNG ---

class MatheGenieApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mathegenie by Rainer Liegard")

        self.db = DatabaseManager()
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Alt-F4>', lambda event: self.root.quit())
        self.root.bind('<Alt-l>', self.handle_progress_menu)

        self.current_frame = None
        self.schuljahr_options = [f"Klasse {j}.{h}"
                                  for j in range(1, 14) for h in range(1, 3)]
        self.selected_schuljahr = tk.StringVar(self.root)
        self.selected_schuljahr.set(self.schuljahr_options[0])
        self.schuljahr_dropdown = None

        self.show_splash_screen()

    def clear_screen(self):
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None
        self.schuljahr_dropdown = None

    def show_splash_screen(self):
        self.clear_screen()
        splash_frame = tk.Frame(self.root, bg="#34495e")
        splash_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = splash_frame
        splash_label = tk.Label(splash_frame,
                                text="Mathegenie by Rainer Liegard",
                                font=("Arial", 48, "bold"),
                                fg="white",
                                bg="#34495e")
        splash_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.root.after(4000, self.show_main_menu)

    # --- Schuljahr Dropdown Logik (wie zuvor) ---

    def hide_schuljahr_dropdown(self):
        if self.schuljahr_dropdown:
            self.schuljahr_dropdown.place_forget()

    def handle_schuljahr_selection(self, event=None):
        if not self.schuljahr_dropdown:
            return

        try:
            schuljahr_button = self.root.nametowidget('.!mathegenieapp.!frame.!schuljahr_button')
        except KeyError:
            return

        schuljahr_button.update_idletasks()
        button_width = schuljahr_button.winfo_width()
        button_height = schuljahr_button.winfo_height()
        button_x = schuljahr_button.winfo_rootx()
        button_y = schuljahr_button.winfo_rooty()

        x_pos = button_x - self.root.winfo_rootx()
        y_pos = button_y - self.root.winfo_rooty() + button_height + 2

        self.schuljahr_dropdown.place(x=x_pos, y=y_pos, width=button_width)

        self.schuljahr_dropdown.focus_set()
        self.schuljahr_dropdown.bind('<FocusOut>', self.hide_schuljahr_dropdown_on_focusout)

    def hide_schuljahr_dropdown_on_focusout(self, event):
        self.root.after(100, self._check_focus_and_hide)

    def _check_focus_and_hide(self):
        if self.schuljahr_dropdown and not self.schuljahr_dropdown.focus_get() == self.schuljahr_dropdown:
            self.hide_schuljahr_dropdown()
            print(f"Schuljahr geändert: {self.selected_schuljahr.get()}. Dropdown ausgeblendet.")

    # --- Startfunktion für Übung ---

    def start_practice_session(self, topic, difficulty):
        """Startet eine neue Übungssession in einem Toplevel-Fenster."""
        if self.current_frame:
            self.current_frame.destroy()

        AufgabenSession(self, topic, difficulty)


    def handle_progress_menu(self, event=None):
        self.show_progress_menu()

    # --- Untermenü und Hauptmenü (angepasst) ---

    def show_topic_submenu(self, topic, menu_frame):
        self.clear_screen()

        style = ttk.Style()
        style.configure('TButton', font=('Arial', 16), padding=10)

        submenu_frame = tk.Frame(self.root, bg="#ecf0f1")
        submenu_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = submenu_frame

        tk.Label(submenu_frame, text=f"{topic}: Schwierigkeitsgrad wählen",
                 font=("Arial", 28, "bold"), bg="#ecf0f1").pack(pady=40)

        button_container = tk.Frame(submenu_frame, bg="#ecf0f1")
        button_container.pack(pady=20)

        difficulties = [
            ("Leicht", "Grundlagenwissen, kurze Aufgaben (z.B. Zahlenraum bis 20).", "#D4EDDA"),
            ("Mittel", "Standardaufgaben, längere Rechenwege (z.B. Terme zusammenfassen).", "#FFF3CD"),
            ("Schwer", "Komplexe Aufgaben, Textaufgaben (z.B. Gleichungen umstellen, statistische Analyse).", "#F8D7DA")
        ]

        for i, (level, tooltip_text, color) in enumerate(difficulties):
            button_style = f'{level}.TButton'
            style.configure(button_style, font=('Arial', 20, 'bold'), padding=20, background=color)

            command_func = lambda t=topic, d=level: self.start_practice_session(t, d)

            button = ttk.Button(button_container, text=level, command=command_func, style=button_style)
            button.grid(row=0, column=i, padx=30, ipadx=50, ipady=30)

            ToolTip(button, tooltip_text)

        ttk.Button(submenu_frame, text="⬅️ Zurück zum Hauptmenü", command=self.show_main_menu).pack(pady=50)


    def show_progress_menu(self):
        """Erstellt und zeigt die Ansicht mit dem Lernfortschritt (Datenbank-Tabelle)."""
        self.clear_screen()

        progress_frame = tk.Frame(self.root, bg="#ecf0f1")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = progress_frame

        tk.Label(progress_frame, text="Lernfortschritt und Ergebnisse (SQLite-Datenbank)",
                 font=("Arial", 28, "bold"), bg="#ecf0f1").pack(pady=20)

        # 1. Tabelle (Treeview)
        columns = ("ID", "Thema", "Richtig", "Gesamt", "Dauer (s)", "Datum")
        self.tree = ttk.Treeview(progress_frame, columns=columns, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=50, pady=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.CENTER)

        self.tree.column("ID", width=50, stretch=tk.NO)

        self.load_results_to_tree()

        # 2. Steuerelemente
        control_frame = tk.Frame(progress_frame, bg="#ecf0f1")
        control_frame.pack(pady=10)

        ttk.Button(control_frame, text="🗑️ Ergebnis löschen", command=self.delete_selected_result).pack(side=tk.LEFT, padx=10)
        ToolTip(control_frame.winfo_children()[-1], "Löscht das ausgewählte Ergebnis aus der Datenbank.")

        ttk.Button(control_frame, text="🔄 Bearbeiten (Simuliert)", command=self.simulate_edit_result).pack(side=tk.LEFT, padx=10)
        ToolTip(control_frame.winfo_children()[-1], "Simuliert eine manuelle Korrektur des Ergebnisses.")

        ttk.Button(control_frame, text="⬅️ Zurück zum Hauptmenü", command=self.show_main_menu).pack(side=tk.LEFT, padx=10)
        ToolTip(control_frame.winfo_children()[-1], "Zurück zum Hauptmenü.")

    def load_results_to_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        results = self.db.get_all_results()
        for row in results:
            display_row = list(row)
            display_row[4] = f"{row[4]:.1f}"
            self.tree.insert("", tk.END, values=display_row)

    def delete_selected_result(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Löschen", "Bitte wählen Sie ein Ergebnis zum Löschen.")
            return

        result_id = self.tree.item(selected_item)['values'][0]
        if messagebox.askyesno("Löschen bestätigen", f"Soll Ergebnis ID {result_id} wirklich gelöscht werden?"):
            self.db.delete_result(result_id)
            self.load_results_to_tree()
            messagebox.showinfo("Gelöscht", f"Ergebnis ID {result_id} wurde gelöscht.")

    def simulate_edit_result(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Bearbeiten", "Bitte wählen Sie ein Ergebnis zum Bearbeiten.")
            return

        old_values = self.tree.item(selected_item)['values']
        result_id = old_values[0]

        new_correct = int(old_values[2]) + 1
        new_total = int(old_values[3])
        new_duration = float(old_values[4]) * 0.9

        self.db.update_result(result_id, new_correct, new_total, new_duration)
        self.load_results_to_tree()
        messagebox.showinfo("Bearbeitet", f"Ergebnis ID {result_id} wurde simuliert bearbeitet (Richtige Zahl um 1 erhöht).")


    def show_main_menu(self):
        self.clear_screen()

        menu_frame = tk.Frame(self.root, bg="#ecf0f1")
        menu_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = menu_frame

        style = ttk.Style()
        style.configure('TButton', font=('Arial', 16), padding=10)
        style.configure('Big.TButton', font=('Arial', 24, 'bold'), padding=20)

        schuljahr_button = ttk.Button(menu_frame, text=f"Aktuelle Klasse: {self.selected_schuljahr.get()}",
                                      command=self.handle_schuljahr_selection,
                                      style='Big.TButton',
                                      name='schuljahr_button')
        schuljahr_button.place(relx=0.5, rely=0.20, anchor=tk.CENTER)

        self.root.bind('<Alt-s>', self.handle_schuljahr_selection)
        ToolTip(schuljahr_button, "Wählt den aktuellen Lernstand von Klasse 1.1 bis 13.2 (Hotkey: Alt+S)")

        button_info = [
            ("Zahlenraum-Training", "Addition/Subtraktion/Multiplikation/Division im gewählten Zahlenraum.", self.show_topic_submenu),
            ("Terme & Gleichungen", "Vereinfachen, Umstellen und Auflösen von Termen und Gleichungen.", self.show_topic_submenu),
            ("Geometrie", "Flächen, Umfang, Volumen, Winkel und geometrische Körper.", self.show_topic_submenu),
            ("Statistik", "Häufigkeit, Wahrscheinlichkeit, Boxplots und stochastische Prozesse.", self.show_topic_submenu),
            ("Lernfortschritt", "Zeigt gespeicherte Ergebnisse an (Hotkey: Alt+L)", self.handle_progress_menu),
            ("Einstellungen", "Öffnet die Einstellungen", lambda: print("Einstellungen gedrückt"))
        ]

        button_container = tk.Frame(menu_frame, bg="#ecf0f1")
        button_container.place(relx=0.5, rely=0.70, anchor=tk.CENTER)

        for i, (text, tooltip_text, handler) in enumerate(button_info):
            if handler == self.show_topic_submenu:
                command_func = lambda t=text, f=menu_frame: self.show_topic_submenu(t, f)
            else:
                command_func = handler

            button = ttk.Button(button_container, text=text, command=command_func)
            button.grid(row=i // 2, column=i % 2, padx=20, pady=15, ipadx=20, ipady=10)

            ToolTip(button, tooltip_text)

        self.schuljahr_dropdown = ttk.Combobox(menu_frame,
                                               textvariable=self.selected_schuljahr,
                                               values=self.schuljahr_options,
                                               font=('Arial', 14),
                                               state='readonly'
                                               )
        self.schuljahr_dropdown.bind('<<ComboboxSelected>>',
                                     lambda event: (schuljahr_button.config(text=f"Aktuelle Klasse: {self.selected_schuljahr.get()}"),
                                                    self.root.after(1, self.hide_schuljahr_dropdown)))

        exit_button = ttk.Button(menu_frame, text="✖ Beenden (Alt+F4)",
                                 command=self.root.quit,
                                 style='TButton')

        exit_button.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-20, y=20)


if __name__ == "__main__":
    root = tk.Tk()
    app = MatheGenieApp(root)
    root.mainloop()