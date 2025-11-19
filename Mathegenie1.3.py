# ==============================================================================
# PROJEKT: Mathegenie - Adaptiver Mathetrainer
# AUTOR:   Rainer Liegard
# DATUM:   07. November 2025
# [cite_start]VERSION: 1.3 (Behebung des Fokus-Problems für Hotkeys durch focus_set()) [cite: 383]
# ==============================================================================
#
# Eine Tkinter-Anwendung zur Durchführung und Aufzeichnung von Mathematikübungen.
# Die Logik ist stabil, und diese Version legt den Fokus auf die vollständige
# und zuverlässige Steuerung der Anwendung über Hotkeys.
#
# Haupt-Features der Version 2.2:
# 1. **Fokus-Fix (Hauptziel):** Durch konsequentes Setzen des Fokus mit `focus_set()`
#    auf die Root-Ebene oder das Toplevel-Fenster (Übungssession) wird sichergestellt,
#    [cite_start]dass alle Hotkeys der Menüs und der Übungssitzung fehlerfrei reagieren[cite: 668, 745, 747, 756].
# 2. **Vollständige Hotkey-Steuerung:**
#    [cite_start]* Hauptmenü-Navigation: Strg+1, 2, 3, 4, P, I, K[cite: 754, 755].
#    [cite_start]* Session-Steuerung: 'Weiter' per Leertaste, 'Abbrechen' per Strg+X[cite: 658, 666].
#    [cite_start]* Menü-Navigation: 'Zurück' per Strg+Z in Submenüs und Fortschrittsansicht[cite: 745].
# 3. **Usability-Verbesserung:** Das Eingabefeld in der Übungssession erhält sofort den Fokus
#    [cite_start](`self.answer_entry.focus_set()`), sodass der Benutzer ohne Klick mit der Eingabe beginnen kann[cite: 701].
# 4. **Stabile Basis:** Die Datenbank-Migration, Klassen-Speicherung und Aufgabenlogik (Version 1.8/2.1) bleiben stabil.
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
        """Erstellt die Tabelle und migriert das Schema, falls 'class' fehlt (Fix für OperationalError)."""
        # 1. Basis-Tabelle erstellen (enthält alle neuen Spalten für Neuinstallationen)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                class TEXT NOT NULL, 
                correct_count INTEGER NOT NULL,
                total_count INTEGER NOT NULL,
                duration REAL,
                timestamp TEXT NOT NULL
            )
        """)
        self.conn.commit()

        # 2. Schema-Migration: Prüfen und Hinzufügen der 'class' Spalte, falls sie in einer
        # alten Datenbank-Version fehlt (Ursache des OperationalError).
        try:
            # Versuch, die Spalte abzurufen. Scheitert, wenn sie fehlt.
            self.cursor.execute("SELECT class FROM results LIMIT 1")
        except sqlite3.OperationalError as e:
            # Prüfen auf den spezifischen Fehler "no such column: class"
            if "no such column: class" in str(e):
                # Fügt die Spalte hinzu mit einem Default-Wert für existierende Zeilen
                self.cursor.execute("ALTER TABLE results ADD COLUMN class TEXT NOT NULL DEFAULT 'Klasse N.N'")
                self.conn.commit()
                print("Datenbank-Migration: Spalte 'class' erfolgreich hinzugefügt zu existierender Tabelle.")
            else:
                # Anderen OperationalError weitergeben
                raise

        self.conn.commit()

    def save_result(self, topic, class_name, correct, total, duration):
        """Speichert ein neues Lernergebnis, inklusive der Klasse."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO results (topic, class, correct_count, total_count, duration, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (topic, class_name, correct, total, duration, timestamp))
        self.conn.commit()

    def get_all_results(self):
        """Ruft alle gespeicherten Ergebnisse ab (jetzt mit Klasse)."""
        # Diese Query funktioniert nun dank der Migrationslogik immer
        self.cursor.execute("SELECT id, topic, class, correct_count, total_count, duration, timestamp FROM results ORDER BY timestamp DESC")
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

        x_val, y_val = 2, 3
        solution_value = 0

        for part in term_parts:
            coeff = 0
            if 'x' in part:
                coeff_str = part.replace('x', '')
                coeff = int(coeff_str) if coeff_str not in ('', '+', '-') else 1 if coeff_str == '' or coeff_str == '+' else -1
                solution_value += coeff * x_val
            elif 'y' in part:
                coeff_str = part.replace('y', '')
                coeff = int(coeff_str) if coeff_str not in ('', '+', '-') else 1 if coeff_str == '' or coeff_str == '+' else -1
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
    def __init__(self, parent_app, topic, difficulty, class_name):
        self.parent_app = parent_app
        self.topic = topic
        self.difficulty = difficulty
        self.class_name = class_name

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
        self.window.title(f"Übung: {self.topic} ({self.difficulty}) | {self.class_name}")

        self.window.attributes('-fullscreen', True)
        # HACK: Protokoll für X-Button anpassen, um Abbruch zu ermöglichen
        self.window.protocol("WM_DELETE_WINDOW", self._cancel_session)

        self.frame = tk.Frame(self.window, bg="#f5f5f5")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)

        # Titel zeigt jetzt auch die Klasse
        tk.Label(self.frame, text=f"Aufgaben: {self.topic} ({self.difficulty}) | {self.class_name}",
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
        # Hotkey: Return/Enter ist an das Eingabefeld gebunden
        self.answer_entry.bind('<Return>', lambda e: self._check_answer())
        ToolTip(self.answer_entry, "Eingabe der Antwort. Mit **Enter** prüfen und zur nächsten Frage springen.")

        # Navigations-Button
        self.next_button = ttk.Button(self.frame, text="Antwort prüfen & Weiter >> (Leertaste)",
                                      command=self._check_answer, style='Big.TButton')
        self.next_button.pack(pady=20)

        # Hotkey: Leertaste
        self.window.bind('<space>', lambda e: self._check_answer())
        ToolTip(self.next_button, "Prüft die Antwort und geht zur nächsten Frage.")

        # ABBRUCH-BUTTON - Hotkey Strg+X
        self.cancel_button = ttk.Button(self.frame, text="🛑 Übung abbrechen & zum Hauptmenü (Strg+X)",
                                        command=self._cancel_session, style='TButton')
        self.cancel_button.pack(pady=40)

        # Hotkey: Control-x
        self.window.bind('<Control-x>', lambda e: self._cancel_session())
        ToolTip(self.cancel_button, "Bricht die aktuelle Übung ab. Der Fortschritt geht verloren.")

        # Fokus auf das Toplevel-Fenster setzen, um die Hotkeys zu aktivieren
        self.window.focus_set()

        self._update_question()
        self._start_timer()

    def _cancel_session(self, event=None):
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
        q_data = self.generator.questions[self.current_question_index]
        self.question_label.config(text=f"Frage {q_data['id']}/{self.num_questions}:\n{q_data['question']}")
        self.answer_entry.delete(0, tk.END)

        if self.current_question_index == self.num_questions - 1:
            self.next_button.config(text="Antwort prüfen & Beenden (Letzte Frage)")
        else:
            self.next_button.config(text="Antwort prüfen & Weiter >> (Leertaste)")

        # Fokus auf das Eingabefeld setzen, damit man direkt tippen kann
        self.answer_entry.focus_set()

    def _check_answer(self, event=None):
        """Prüft die Antwort des Benutzers und geht zur nächsten Frage."""
        # 1. Prüfen, ob noch Fragen offen sind
        if self.current_question_index >= self.num_questions:
            self._finish_session()
            return

        # 2. Antwort der AKTUELLEN Frage (current_question_index) speichern
        user_input = self.answer_entry.get().strip().replace(',', '.')
        q_data = self.generator.questions[self.current_question_index]

        try:
            user_answer = float(user_input)
            q_data['user_answer'] = user_answer
        except ValueError:
            q_data['user_answer'] = "Ungültige Eingabe"

        # 3. Index erhöhen
        self.current_question_index += 1

        # 4. Prüfen, ob alle Fragen beantwortet wurden (Index ist jetzt 10)
        if self.current_question_index == self.num_questions:
            self._finish_session()
        else:
            # 5. Nächste Frage anzeigen (Index ist 1 bis 9)
            self._update_question()


    def _finish_session(self, timeout=False):
        """Beendet die Übung, wertet aus und speichert in der DB."""
        if self.timer_id:
            self.window.after_cancel(self.timer_id)

        elapsed_time = self.time_limit - self.time_left if not timeout else self.time_limit

        correct_count = 0
        total_count = self.num_questions

        for q in self.generator.questions:
            if isinstance(q['user_answer'], (int, float)) and abs(q['user_answer'] - q['correct_answer']) < 0.1:
                correct_count += 1

        full_topic = f"{self.topic} ({self.difficulty})"
        # Speichern mit Klassenname
        self.parent_app.db.save_result(full_topic, self.class_name, correct_count, total_count, elapsed_time)

        result_msg = f"⏱️ Übungszeit abgelaufen!" if timeout else "✅ Übung beendet!"
        result_msg += (f"\n\nKlasse: {self.class_name}\n"
                       f"Thema: {full_topic}\n"
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

        # Die Datenbank wird initialisiert und die Migration findet statt
        self.db = DatabaseManager()
        self.root.attributes('-fullscreen', True)

        # Globale Hotkeys
        self.root.bind('<Alt-F4>', lambda event: self.root.quit()) # Standard
        # Strg+P für Progress (klein geschrieben, da es nicht im Hauptmenü ist)
        self.root.bind('<Control-p>', self.handle_progress_menu)

        self.current_frame = None
        # Klassen-Liste von 1.1 bis 13.2
        self.schuljahr_options = [f"Klasse {j}.{h}"
                                  for j in range(1, 14) for h in range(1, 3)]
        self.selected_schuljahr = tk.StringVar(self.root)
        self.selected_schuljahr.set(self.schuljahr_options[0])
        self.schuljahr_dropdown = None

        self.show_splash_screen()

    def clear_screen(self):
        # Alle spezifischen Hotkeys, die beim Laden eines neuen Menüs entfernt werden müssen
        # Hauptmenü-Hotkeys
        self.root.unbind('<Control-1>')
        self.root.unbind('<Control-2>')
        self.root.unbind('<Control-3>')
        self.root.unbind('<Control-4>')
        self.root.unbind('<Control-P>')
        self.root.unbind('<Control-I>')
        self.root.unbind('<Control-K>')

        # Submenü-Hotkeys
        self.root.unbind('<Control-Z>')

        # Fortschrittsmenü-Hotkeys
        self.root.unbind('<Control-L>')
        self.root.unbind('<Control-B>')

        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None

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

    def start_practice_session(self, topic, difficulty):
        """Startet eine neue Übungssession in einem Toplevel-Fenster."""
        if self.current_frame:
            self.current_frame.destroy()

        current_class = self.selected_schuljahr.get()
        # Hinweis: Das AufgabenSession-Fenster muss seinen eigenen Hotkey-Fokus setzen (ist implementiert)
        AufgabenSession(self, topic, difficulty, current_class)

    def handle_progress_menu(self, event=None):
        self.show_progress_menu()

    # --- Untermenü und Hauptmenü ---

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

        # Hotkeys Strg+1, 2, 3
        difficulties = [
            ("Leicht (Strg+1)", "Grundlagenwissen, kurze Aufgaben (z.B. Zahlenraum bis 20).", "#D4EDDA", '<Control-1>'),
            ("Mittel (Strg+2)", "Standardaufgaben, längere Rechenwege (z.B. Terme zusammenfassen).", "#FFF3CD", '<Control-2>'),
            ("Schwer (Strg+3)", "Komplexe Aufgaben, Textaufgaben (z.B. Gleichungen umstellen, statistische Analyse).", "#F8D7DA", '<Control-3>')
        ]

        for i, (level_text, tooltip_text, color, hotkey_binding) in enumerate(difficulties):
            level = level_text.split('(')[0].strip()
            button_style = f'{level}.TButton'
            style.configure(button_style, font=('Arial', 20, 'bold'), padding=20, background=color)

            command_func = lambda t=topic, d=level: self.start_practice_session(t, d)

            button = ttk.Button(button_container, text=level_text, command=command_func, style=button_style)
            button.grid(row=0, column=i, padx=30, ipadx=50, ipady=30)

            ToolTip(button, tooltip_text)

            self.root.bind(hotkey_binding, lambda e, t=topic, d=level: self.start_practice_session(t, d))


        # Hotkey: Strg+Z für Zurück
        back_button = ttk.Button(submenu_frame, text="⬅️ Zurück zum Hauptmenü (Strg+Z)", command=self.show_main_menu)
        back_button.pack(pady=50)
        ToolTip(back_button, "Kehrt zum Hauptmenü zurück.")
        self.root.bind('<Control-Z>', lambda e: self.show_main_menu())

        # FIX: Fokus zurück zum Root-Fenster setzen
        self.root.focus_set()

    def show_progress_menu(self, event=None):
        """Erstellt und zeigt die Ansicht mit dem Lernfortschritt (Datenbank-Tabelle)."""
        self.clear_screen()

        progress_frame = tk.Frame(self.root, bg="#ecf0f1")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = progress_frame

        # Hotkey Zurück (Strg+Z) binden
        self.root.bind('<Control-Z>', lambda e: self.show_main_menu())

        tk.Label(progress_frame, text="Lernfortschritt und Ergebnisse (SQLite-Datenbank)",
                 font=("Arial", 28, "bold"), bg="#ecf0f1").pack(pady=20)

        # 1. Tabelle (Treeview)
        columns = ("ID", "Thema", "Klasse", "Richtig", "Gesamt", "Dauer (s)", "Datum")
        self.tree = ttk.Treeview(progress_frame, columns=columns, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=50, pady=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.CENTER)

        self.tree.column("ID", width=50, stretch=tk.NO)
        self.tree.column("Klasse", width=100, stretch=tk.NO)

        self.load_results_to_tree()

        # 2. Steuerelemente
        control_frame = tk.Frame(progress_frame, bg="#ecf0f1")
        control_frame.pack(pady=10)

        # Löschen Button (Strg+L)
        delete_button = ttk.Button(control_frame, text="🗑️ Ergebnis löschen (Strg+L)", command=self.delete_selected_result)
        delete_button.pack(side=tk.LEFT, padx=10)
        ToolTip(delete_button, "Löscht das ausgewählte Ergebnis aus der Datenbank.")
        self.root.bind('<Control-L>', lambda e: self.delete_selected_result())

        # Bearbeiten Button (Strg+B)
        edit_button = ttk.Button(control_frame, text="🔄 Bearbeiten (Simuliert) (Strg+B)", command=self.simulate_edit_result)
        edit_button.pack(side=tk.LEFT, padx=10)
        ToolTip(edit_button, "Simuliert eine manuelle Korrektur des Ergebnisses.")
        self.root.bind('<Control-B>', lambda e: self.simulate_edit_result())

        # Zurück Button (Strg+Z)
        back_button = ttk.Button(control_frame, text="⬅️ Zurück zum Hauptmenü (Strg+Z)", command=self.show_main_menu)
        back_button.pack(side=tk.LEFT, padx=10)
        ToolTip(back_button, "Zurück zum Hauptmenü.")

        # FIX: Fokus zurück zum Root-Fenster setzen
        self.root.focus_set()


    def load_results_to_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        results = self.db.get_all_results()
        for row in results:
            # row: (id, topic, class, correct_count, total_count, duration, timestamp)
            display_row = list(row)
            # Die Dauer (Index 5) wird formatiert.
            display_row[5] = f"{row[5]:.1f}"

            self.tree.insert("", tk.END, values=display_row)

    def delete_selected_result(self, event=None):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Löschen", "Bitte wählen Sie ein Ergebnis zum Löschen.")
            return

        result_id = self.tree.item(selected_item)['values'][0]
        if messagebox.askyesno("Löschen bestätigen", f"Soll Ergebnis ID {result_id} wirklich gelöscht werden?"):
            self.db.delete_result(result_id)
            self.load_results_to_tree()
            messagebox.showinfo("Gelöscht", f"Ergebnis ID {result_id} wurde gelöscht.")

    def simulate_edit_result(self, event=None):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Bearbeiten", "Bitte wählen Sie ein Ergebnis zum Bearbeiten.")
            return

        old_values = self.tree.item(selected_item)['values']
        result_id = old_values[0]

        # Indizes: Richtig (3), Gesamt (4), Dauer (5)
        new_correct = int(old_values[3]) + 1
        new_total = int(old_values[4])
        new_duration = float(old_values[5]) * 0.9

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

        # --- Schuljahr Button (Anzeige) ---
        # Hotkey: Strg+K (Klasse)
        schuljahr_button_text = f"Aktuelle Klasse: {self.selected_schuljahr.get()} (Strg+K)"

        schuljahr_button = ttk.Button(menu_frame,
                                      text=schuljahr_button_text,
                                      style='Big.TButton',
                                      name='schuljahr_button')
        schuljahr_button.place(relx=0.5, rely=0.20, anchor=tk.CENTER)

        ToolTip(schuljahr_button, "Zeigt die aktuell gewählte Lernklasse. Klicken oder **Strg+K** wählen, um die Klasse zu ändern.")

        # --- Schuljahr Dropdown ---
        self.schuljahr_dropdown = ttk.Combobox(menu_frame,
                                               textvariable=self.selected_schuljahr,
                                               values=self.schuljahr_options,
                                               font=('Arial', 14),
                                               state='readonly',
                                               justify=tk.CENTER
                                               )

        self.schuljahr_dropdown.place(relx=0.5, rely=0.30, anchor=tk.CENTER, width=350)

        ToolTip(self.schuljahr_dropdown, "Wählen Sie hier den aktuellen Lernstand von Klasse 1.1 bis 13.2.")

        def update_schuljahr_display(event):
            schuljahr_button.config(text=f"Aktuelle Klasse: {self.selected_schuljahr.get()} (Strg+K)")

        self.schuljahr_dropdown.bind('<<ComboboxSelected>>', update_schuljahr_display)

        # Strg+K Hotkey zum Fokussieren der Combobox
        self.root.bind('<Control-K>', lambda e: self.schuljahr_dropdown.focus_set())

        schuljahr_button.config(command=lambda: self.schuljahr_dropdown.focus_set())

        # Hotkeys jetzt mit Strg+Ziffer und Strg+Buchstabe
        button_info = [
            ("1. Zahlenraum-Training (Strg+1)", "Addition/Subtraktion/Multiplikation/Division im gewählten Zahlenraum.", self.show_topic_submenu, '<Control-1>'),
            ("2. Terme & Gleichungen (Strg+2)", "Vereinfachen, Umstellen und Auflösen von Termen und Gleichungen.", self.show_topic_submenu, '<Control-2>'),
            ("3. Geometrie (Strg+3)", "Flächen, Umfang, Volumen, Winkel und geometrische Körper.", self.show_topic_submenu, '<Control-3>'),
            ("4. Statistik (Strg+4)", "Häufigkeit, Wahrscheinlichkeit, Boxplots und stochastische Prozesse.", self.show_topic_submenu, '<Control-4>'),
            ("Lernfortschritt (Strg+P)", "Zeigt gespeicherte Ergebnisse an.", self.handle_progress_menu, '<Control-P>'),
            ("Einstellungen (Strg+I)", "Öffnet die Einstellungen.", lambda: print("Einstellungen gedrückt"), '<Control-I>')
        ]

        button_container = tk.Frame(menu_frame, bg="#ecf0f1")
        button_container.place(relx=0.5, rely=0.70, anchor=tk.CENTER)

        for i, (text, tooltip_text, handler, hotkey_binding) in enumerate(button_info):
            if handler == self.show_topic_submenu:
                topic_name = text.split('(')[0].strip()[3:].strip() # Entfernt "X. "
                command_func = lambda t=topic_name, f=menu_frame: self.show_topic_submenu(t, f)
            else:
                command_func = handler

            button = ttk.Button(button_container, text=text, command=command_func)
            button.grid(row=i // 2, column=i % 2, padx=20, pady=15, ipadx=20, ipady=10)

            ToolTip(button, tooltip_text)

            # Hotkeys an root binden
            self.root.bind(hotkey_binding, lambda e, func=command_func: func())

        exit_button = ttk.Button(menu_frame, text="✖ Beenden (Alt+F4)",
                                 command=self.root.quit,
                                 style='TButton')

        exit_button.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-20, y=20)
        ToolTip(exit_button, "Beendet die Anwendung.")

        # FIX: Fokus zurück zum Root-Fenster setzen
        self.root.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatheGenieApp(root)
    root.mainloop()