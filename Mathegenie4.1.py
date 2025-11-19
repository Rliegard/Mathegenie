# ==============================================================================
# PROJEKT: Mathegenie - Adaptiver Mathetrainer
# AUTOR:   Rainer Liegard
# DATUM:   13. November 2025
# VERSION: 4.1 (Verfeinerung der Halbjahrestest-Auswertung & UI-Optimierung)
# ==============================================================================
#
# Eine adaptive Tkinter-Anwendung zur Durchführung und Aufzeichnung von
# Mathematikübungen. Diese Version optimiert die Anzeige und die Logik
# des in V4.0 eingeführten Halbjahrestests.
#
# Haupt-Features der Version 4.1:
# 1. Optimierte Testauswertung: Die Ergebnisanzeige des Halbjahrestests wurde
#    verfeinert, um eine klarere Darstellung der erreichten Punkte pro Thema
#    oder Schwierigkeitsgrad zu gewährleisten.
# 2. UI-Anpassungen: Feintuning der Menü-Layouts und der Tooltips nach der
#    Hinzunahme des Test-Buttons, um eine konsistente Usability zu gewährleisten.
# 3. Bugfixes und Code-Refactoring: Bereinigung kleinerer Fehler, die während
#    der Entwicklung des komplexen Testgenerators aufgetreten sind.
# 4. Stabile Basis: Alle Kernfunktionen, insbesondere der Halbjahrestest (V4.0)
#    und die adaptive Lehrplan-Steuerung, bleiben stabil und funktionsfähig.
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
import re # Import für RegEx
import math # Import für sqrt, pi

#NEU: Helper-Funktion zur Formatierung von Zahlen im deutschen Format
def format_german(number):
    """Formatiert eine Zahl (int/float) ins deutsche Format (z. B. 1.453.557,0)"""
    try:
        number = round(number, 5)
    except TypeError:
        return str(number)

    s = f"{number:f}".rstrip('0')
    if s.endswith('.'):
        s = s[:-1]

    parts = s.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    sign = ""
    if integer_part.startswith('-'):
        sign = '-'
        integer_part = integer_part[1:]

    try:
        integer_part_formatted = f"{int(integer_part):,}"
    except ValueError:
        integer_part_formatted = integer_part

    integer_part_german = integer_part_formatted.replace(',', '.')

    if decimal_part:
        return f"{sign}{integer_part_german},{decimal_part}"
    else:
        if isinstance(number, float) and number == int(number):
            return f"{sign}{integer_part_german},0"
        else:
            return f"{sign}{integer_part_german}"

#--- HILFSKLASSEN
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

#=========================
# NEUE FEEDBACK DIALOG KLASSE (ersetzt messagebox)
#=========================
class FeedbackDialog(tk.Toplevel):
    """
    Ein modales Dialogfeld, das Feedback (richtig/falsch) und optional
    eine Geometrie- oder Statistik-Skizze auf einem Canvas anzeigt.
    """
    def __init__(self, parent, title, is_correct, message, drawing_info=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.config(bg="#f0f0f0")

        if is_correct:
            title_text = "☑ Richtig!"
            title_color = "#28a745"
        else:
            title_text = "X Leider falsch!"
            title_color = "#dc3545"

        title_label = tk.Label(self, text=title_text, font=("Arial", 18, "bold"), fg=title_color, bg="#f0f0f0")
        title_label.pack(pady=(15, 10))

        message_label = tk.Label(self, text=message, font=("Arial", 12), bg="#f0f0f0", justify=tk.LEFT, wraplength=450)
        message_label.pack(padx=20, pady=(0, 10))

        if drawing_info:
            try:
                self._draw_sketch(drawing_info)
            except Exception as e:
                print(f"Fehler beim Zeichnen der Skizze: {e}")

        style = ttk.Style()
        style.configure('Dialog.TButton', font=('Arial', 12))

        ok_button = ttk.Button(self, text="OK", command=self.destroy, style='Dialog.TButton')
        ok_button.pack(pady=15, ipadx=20)

        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)

        self.geometry(f"+{x}+{y}")
        self.wait_window()

    # --- MODIFIZIERT: _draw_sketch (mit mehr Formen) ---
    def _draw_sketch(self, info):
        """Zeichnet die Geometrie- oder Statistik-Skizze auf ein Canvas."""
        canvas = tk.Canvas(self, width=220, height=150, bg="white", highlightthickness=1,
                           highlightbackground="black")

        shape = info.get('shape')

        # 2D
        if shape == 'Rechteck':
            l_text = f"Länge: {info.get('l', '?')}"
            w_text = f"Breite: {info.get('w', '?')}"
            canvas.create_rectangle(40, 40, 180, 110, outline="blue", width=2)
            canvas.create_text(110, 30, text=l_text, fill="black")
            canvas.create_text(30, 75, text=w_text, fill="black", anchor="e")

        elif shape == 'Kreis':
            r = info.get('r', '?')
            r_text = f"Radius: {r}"
            canvas.create_oval(60, 20, 160, 120, outline="red", width=2)
            canvas.create_line(110, 70, 160, 70, fill="red", dash=(4, 2))
            canvas.create_text(135, 80, text=r_text, fill="black", anchor="w")

        elif shape == 'Dreieck':
            b_text = f"g: {info.get('b', '?')}"
            h_text = f"h: {info.get('h', '?')}"
            canvas.create_polygon(50, 120, 170, 120, 50, 30, fill="#eeeeee", outline="purple", width=2)
            canvas.create_line(50, 120, 50, 30, fill="purple", dash=(4, 2))
            canvas.create_text(110, 130, text=b_text, fill="black")
            canvas.create_text(40, 75, text=h_text, fill="black", anchor="e")

        elif shape == 'Trapez':
            a_text = f"a: {info.get('a', '?')}"
            c_text = f"c: {info.get('c', '?')}"
            h_text = f"h: {info.get('h', '?')}"
            canvas.create_polygon(50, 110, 170, 110, 130, 40, 90, 40, fill="#eeeeee", outline="orange", width=2)
            canvas.create_line(50, 110, 50, 40, fill="orange", dash=(4, 2))
            canvas.create_text(110, 120, text=a_text, fill="black")
            canvas.create_text(110, 30, text=c_text, fill="black")
            canvas.create_text(40, 75, text=h_text, fill="black", anchor="e")

        # 3D
        elif shape == 'Würfel':
            a_text = f"a: {info.get('a', '?')}"
            canvas.create_rectangle(70, 70, 150, 150, outline="black", width=2, fill="#ddddff")
            canvas.create_rectangle(50, 50, 130, 130, outline="grey", width=2)
            canvas.create_line(70, 70, 50, 50, outline="grey")
            canvas.create_line(150, 70, 130, 50, outline="grey")
            canvas.create_line(70, 150, 50, 130, outline="grey")
            canvas.create_line(150, 150, 130, 130, outline="grey")
            canvas.create_text(110, 60, text=a_text, fill="black")

        elif shape == 'Kugel':
            r = info.get('r', '?')
            r_text = f"Radius: {r}"
            canvas.create_oval(60, 30, 160, 130, outline="blue", width=2, fill="#eeeeff")
            canvas.create_oval(60, 75, 160, 85, outline="blue", dash=(4, 2))
            canvas.create_line(110, 80, 160, 80, fill="blue", dash=(2, 2))
            canvas.create_text(135, 90, text=r_text, fill="black", anchor="w")

        elif shape == 'Quader':
            l_text = f"l: {info.get('l', '?')}"
            w_text = f"b: {info.get('w', '?')}"
            h_text = f"h: {info.get('h', '?')}"
            canvas.create_rectangle(70, 70, 170, 130, outline="black", width=2, fill="#ddddff")
            canvas.create_rectangle(50, 50, 150, 110, outline="grey", width=2)
            canvas.create_line(70, 70, 50, 50, outline="grey")
            canvas.create_line(170, 70, 150, 50, outline="grey")
            canvas.create_line(70, 130, 50, 110, outline="grey")
            canvas.create_line(170, 130, 150, 110, outline="grey")
            canvas.create_text(120, 60, text=l_text, fill="black")
            canvas.create_text(160, 60, text=w_text, fill="black")
            canvas.create_text(60, 100, text=h_text, fill="black")

        elif shape == 'Zylinder':
            r_text = f"r: {info.get('r', '?')}"
            h_text = f"h: {info.get('h', '?')}"
            canvas.create_oval(50, 110, 170, 130, outline="black", width=2, fill="#ddddff")
            canvas.create_line(50, 120, 50, 50, outline="black", width=2)
            canvas.create_line(170, 120, 170, 50, outline="black", width=2)
            canvas.create_oval(50, 40, 170, 60, outline="black", width=2, fill="#ddddff")
            canvas.create_line(110, 120, 110, 50, fill="grey", dash=(2,2))
            canvas.create_text(40, 85, text=h_text, fill="black")
            canvas.create_text(110, 30, text=r_text, fill="black")

        elif shape == 'Kegel':
            r_text = f"r: {info.get('r', '?')}"
            h_text = f"h: {info.get('h', '?')}"
            canvas.create_oval(50, 110, 170, 130, outline="black", width=2, fill="#ddddff")
            canvas.create_line(50, 120, 110, 30, outline="black", width=2)
            canvas.create_line(170, 120, 110, 30, outline="black", width=2)
            canvas.create_line(110, 120, 110, 30, fill="grey", dash=(2,2))
            canvas.create_text(40, 85, text=h_text, fill="black")
            canvas.create_text(110, 100, text=r_text, fill="black")

        # Statistik
        elif shape == 'BarChart':
            data = info.get('data', [])
            if not data:
                canvas.create_text(110, 75, text="Keine Daten für Skizze.")
                canvas.pack(pady=10, padx=20)
                return

            max_val = max(data) if data else 1
            padding = 20
            canvas_width = 220
            canvas_height = 150

            canvas.create_line(padding, canvas_height - padding, canvas_width - padding, canvas_height - padding)

            bar_width = (canvas_width - 2 * padding) / len(data)
            bar_spacing = 2

            max_bar_height = canvas_height - 2 * padding - 10

            for i, val in enumerate(data):
                x0 = padding + i * bar_width + bar_spacing
                x1 = padding + (i + 1) * bar_width - bar_spacing
                bar_height = (val / max_val) * max_bar_height
                y0 = canvas_height - padding - bar_height
                y1 = canvas_height - padding

                canvas.create_rectangle(x0, y0, x1, y1, fill="#4a90e2", outline="black")
                canvas.create_text((x0 + x1) / 2, y0 - 8, text=str(val), font=("Arial", 10))

        else:
            canvas.create_text(110, 75, text="Keine Skizze verfügbar.")

        canvas.pack(pady=10, padx=20)

#=========================
# NEUE ZERTIFIKAT DIALOG KLASSE
#=========================
class ZertifikatDialog(tk.Toplevel):
    """
    Ein modales Dialogfeld, das ein Zertifikat für einen
    bestandenen Test anzeigt.
    """
    def __init__(self, parent, class_name):
        super().__init__(parent)
        self.title("Zertifikat")
        self.transient(parent)
        self.grab_set()
        self.config(bg="#f0f0f0")

        tk.Label(self, text="Herzlichen Glückwunsch",
                 font=("Arial", 28, "bold"), fg="#2c3e50", bg="#f0f0f0").pack(pady=(20, 5))

        tk.Label(self, text="...zum bestandenen Halbjahrestest!",
                 font=("Arial", 18), bg="#f0f0f0").pack(pady=(0, 10))

        tk.Label(self, text=f"Klasse: {class_name}",
                 font=("Arial", 14, "italic"), bg="#f0f0f0").pack(pady=(0, 15))

        # --- Grafische Darstellung (Trophäe) ---
        try:
            canvas = tk.Canvas(self, width=200, height=220, bg="#f0f0f0", highlightthickness=0)

            # Trophäen-Basis
            canvas.create_rectangle(70, 190, 130, 200, fill="#c0c0c0", outline="#c0c0c0") # Silber-Basis
            canvas.create_rectangle(80, 180, 120, 190, fill="#FFD700", outline="#b8860b") # Gold-Stamm

            # Trophäen-Kelch
            points = [60, 100, 80, 180, 120, 180, 140, 100]
            canvas.create_polygon(points, fill="#FFD700", outline="#b8860b", width=2)

            # Trophäen-Henkel
            canvas.create_arc(30, 110, 80, 160, start=0, extent=180, style=tk.ARC, outline="#FFD700", width=6)
            canvas.create_arc(120, 110, 170, 160, start=0, extent=-180, style=tk.ARC, outline="#FFD700", width=6)

            # Stern (Grafik)
            canvas.create_text(100, 140, text="★", font=("Arial", 40, "bold"), fill="#FFFFFF")

            canvas.pack(pady=10)
        except Exception as e:
            print(f"Fehler beim Zeichnen des Zertifikats: {e}")
            tk.Label(self, text="[Grafik konnte nicht geladen werden]", bg="#f0f0f0").pack(pady=20)


        style = ttk.Style()
        style.configure('Dialog.TButton', font=('Arial', 12))

        ok_button = ttk.Button(self, text="Schließen", command=self.destroy, style='Dialog.TButton')
        ok_button.pack(pady=20, ipadx=20)

        # Zentrieren
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)

        self.geometry(f"+{x}+{y}")
        self.wait_window()

#=========================
#--- DATENBANK-VERWALTUNG
#=========================
class DatabaseManager:
    """Verwaltet die SQLite-Datenbank für Lernergebnisse."""
    def __init__(self, db_name="mathegenie.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        """Erstellt die Tabelle und migriert das Schema, falls 'class' fehlt."""
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

        try:
            self.cursor.execute("SELECT class FROM results LIMIT 1")
        except sqlite3.OperationalError as e:
            if "no such column: class" in str(e):
                self.cursor.execute("ALTER TABLE results ADD COLUMN class TEXT NOT NULL DEFAULT 'Klasse N.N'")
                self.conn.commit()
                print("Datenbank-Migration: Spalte 'class' erfolgreich hinzugefügt zu existierender Tabelle.")
            else:
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
        self.cursor.execute("SELECT id, topic, class, correct_count, total_count, duration, timestamp FROM results ORDER BY timestamp DESC")
        return self.cursor.fetchall()

    def delete_result(self, result_id):
        """Löscht ein Ergebnis anhand der ID."""
        self.cursor.execute("DELETE FROM results WHERE id=?", (result_id,))
        self.conn.commit()

    def update_result(self, result_id, new_correct, new_total, new_duration):
        """Bearbeitet ein Ergebnis anhand der ID (wird im UI simuliert)."""
        self.cursor.execute("""
        UPDATE results SET correct_count=?, total_count=?, duration=?
        WHERE id=?
        """, (new_correct, new_total, new_duration, result_id))
        self.conn.commit()

#=========================
#--- AUFGABEN-ALGORITHMEN
#=========================
class AufgabenGenerator:
    """Erstellt mathematische Aufgaben und deren Lösungen basierend auf Thema und Schwierigkeit."""

    def __init__(self, topic, difficulty, class_name, num_questions=10):
        self.topic = topic
        self.difficulty = difficulty
        self.class_name = class_name
        self.num_questions = num_questions
        self.questions = []
        self._generate_questions()

    def _parse_class(self):
        """Extrahiert Jahr und Halbjahr aus dem Klassennamen (z. B. 'Klasse 5.2' -> 5, 2)."""
        parts = self.class_name.split()
        if len(parts) > 1:
            grade_parts = parts[1].split('.')
            if len(grade_parts) == 2:
                try:
                    year = int(grade_parts[0])
                    semester = int(grade_parts[1])
                    return year, semester
                except ValueError:
                    pass
        return 1, 1 # Standardwert, falls Fehler

    def _get_params(self):
        """Definiert Zahlenbereiche, Operatoren und Komplexität basierend auf Klasse, Thema und
         Schwierigkeit."""
        year, semester = self._parse_class()

        # 1. Basis-Parameter basierend auf Schuljahr
        if year <= 2:
            max_val = 100
            base_ops = ['+', '-']
        elif year <= 4:
            max_val = 1000
            base_ops = ['+', '-', '*', '/']
        elif year <= 7:
            max_val = 10000
            base_ops = ['+', '-', '*', '/']
        else: # Ab Klasse 8
            max_val = 100000
            base_ops = ['+', '-', '*', '/']

        params = {
            'range': (1, max_val),
            'operators': base_ops,
            'vars': 1,
            'max_terms': 2,
            'decimals': 0,
            'allow_negatives': False
        }

        # 2. Anpassung basierend auf Schwierigkeit (NEU DEFINIERT)
        if self.difficulty == "Leicht":
            # 1-stellige Zahlen (1-9)
            params['range'] = (1, 9)
            params['max_terms'] = 2
            params['decimals'] = 0
            params['allow_negatives'] = False

        elif self.difficulty == "Mittel":
            # 2-stellige Zahlen (10-99)
            lower_bound = 10
            upper_bound = 99
            if max_val < 10:
                lower_bound = 1
                upper_bound = max(1, max_val)
            elif max_val < 99:
                upper_bound = max_val

            params['range'] = (lower_bound, upper_bound)
            params['max_terms'] = 3
            if year >= 5:
                params['decimals'] = 1

        elif self.difficulty == "Schwer":
            # 3-stellige Zahlen (100+) bis max_val
            lower_bound = 100
            if max_val < 100:
                lower_bound = max(10, max_val // 2)

            upper_bound = max_val
            if lower_bound > upper_bound:
                lower_bound = max(1, upper_bound // 2)

            params['range'] = (lower_bound, upper_bound)
            params['max_terms'] = 4
            if year >= 5:
                params['decimals'] = 2
            if year >= 7:
                params['allow_negatives'] = True

        # 3. Anpassung basierend auf Thema (Original-Logik)
        # Für Geometrie, Statistik, Stochastik, Polynom, Vektor: Kleinere Zahlenbereiche
        if self.topic not in ["Zahlenraum-Training"]:
            current_lower, current_upper = params['range']

            if self.difficulty == "Schwer":
                new_upper = min(150, current_upper)
            else:
                new_upper = min(50, current_upper)

            new_lower = min(current_lower, new_upper)

            if self.topic in ["Polynomdivision", "Vektor-Berechnung", "Stochastik"]:
                new_upper = min(25, current_upper) if self.difficulty != "Leicht" else min(9, current_upper)
                new_lower = 1

            params['range'] = (new_lower, new_upper)

            if year >= 7:
                params['allow_negatives'] = True # Erlaube negative Vektorkoordinaten etc.
            if year >= 5:
                params['decimals'] = 1

        if self.difficulty == "Mittel" and self.topic == "Zahlenraum-Training":
            params['decimals'] = 0

        return params

    def _generate_questions(self):
        """Hauptmethode zum Erstellen aller Aufgaben."""
        for i in range(self.num_questions):
            q, a, steps = "", 0, "Kein Lösungsweg verfügbar."
            drawing_info = None

            if self.topic == "Zahlenraum-Training":
                q, a, steps = self._generate_zahlenraum()
            elif self.topic == "Terme & Gleichungen":
                q, a, steps = self._generate_terme()
            elif self.topic == "Geometrie":
                q, a, steps, drawing_info = self._generate_geometrie()
            elif self.topic == "Statistik":
                q, a, steps, drawing_info = self._generate_statistik()
            # --- NEUE THEMEN ---
            elif self.topic == "Stochastik":
                q, a, steps = self._generate_stochastik()
            elif self.topic == "Polynomdivision":
                q, a, steps = self._generate_polynomdivision()
            elif self.topic == "Vektor-Berechnung":
                q, a, steps = self._generate_vektoren()
            else:
                q, a, steps = "Fehler: Unbekanntes Thema.", 0, "Fehler bei Generierung."

            self.questions.append({
                'id': i + 1,
                'question': q,
                'correct_answer': a,
                'solution_steps': steps,
                'user_answer': None,
                'drawing_info': drawing_info
            })

    #--- Themen-Algorithmen (Bestehende)
    def _generate_zahlenraum(self):
        # ... (Unverändert) ...
        params = self._get_params()
        op_map = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}
        op_name_map = {'+': 'Addition', '-': 'Subtraktion', '*': 'Multiplikation', '/': 'Division'}

        num_terms = params.get('max_terms', 2)
        lower_bound = params['range'][0]
        upper_bound = params['range'][1]
        allow_negatives = params['allow_negatives']

        if num_terms > 2:
            multi_op_map = {'+': operator.add, '-': operator.sub}
            ops_to_use = ['+', '-']
            nums = []
            for _ in range(num_terms):
                min_val = -upper_bound if allow_negatives else lower_bound
                nums.append(random.randint(min_val, upper_bound))

            ops = [random.choice(ops_to_use) for _ in range(num_terms - 1)]
            question = str(nums[0])
            answer = nums[0]
            steps_calc = f"1. Schritt: {nums[0]}\n"
            current_val = nums[0]

            for i in range(num_terms - 1):
                op = ops[i]
                num2 = nums[i+1]
                if op == '-' and not allow_negatives and current_val < num2:
                    op = '+'

                question += f" {op} {num2}"
                next_val = multi_op_map[op](current_val, num2)
                steps_calc += f"{i+2}. Schritt: {current_val} {op} {num2} = {next_val}\n"
                current_val = next_val

            answer = current_val
            question += " ="
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"**Berechnung (von links nach rechts):**\n"
                f"{steps_calc}\n"
                f"**Ergebnis:** {answer}"
            )
            return question, round(answer, params['decimals']), steps

        if params['decimals'] == 0 and '/' in params['operators']:
            params['operators'].remove('/')

        if not params['operators']:
            params['operators'] = ['+', '-']

        op = random.choice(params['operators'])
        steps = ""

        if op == '/':
            safe_lower = max(2, lower_bound)
            safe_upper = max(safe_lower + 1, upper_bound // 2)
            if safe_lower > safe_upper: safe_upper = safe_lower

            answer = random.randint(safe_lower, safe_upper)
            divisor = random.randint(2, 9)
            num1 = answer * divisor
            question = f"{num1} {op} {divisor} ="
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"1. Schritt: Führe die {op_name_map[op]} aus.\n"
                f" {num1} / {divisor} = {answer}\n"
                f"\n**Ergebnis:** {answer}"
            )
        else:
            num1_min = -upper_bound if params['allow_negatives'] else lower_bound
            num1 = random.randint(num1_min, upper_bound)
            num2_min = -upper_bound if params['allow_negatives'] else lower_bound
            num2 = random.randint(num2_min, upper_bound)

            if op == '-' and not params['allow_negatives'] and num1 < num2:
                num1, num2 = num2, num1

            answer = op_map[op](num1, num2)
            question = f"{num1} {op} {num2} ="
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"1. Schritt: Führe die {op_name_map[op]} aus.\n"
                f" {num1} {op} {num2} = {answer}\n"
                f"\n**Ergebnis:** {answer}"
            )

        return question, round(answer, params['decimals']), steps

    def _generate_terme(self):
        # ... (Unverändert) ...
        params = self._get_params()
        var_list = ['x', 'y', 'a', 'b']
        vars_count = params.get('vars', 1)
        vars = random.sample(var_list, vars_count)
        max_coeff = params['range'][1]

        term_parts = []
        for _ in range(params['max_terms']):
            coeff_min = -max_coeff if params['allow_negatives'] else params['range'][0]
            coeff = random.randint(coeff_min, max_coeff)

            if random.random() < 0.7 and vars:
                var = random.choice(vars)
                term_parts.append(f"{coeff}{var}")
            else:
                term_parts.append(str(coeff))

        x_val, y_val = 2, 3
        solution_value = 0

        try:
            env = {'x': x_val, 'y': y_val, 'a': x_val, 'b': y_val}
            eval_str = "".join([p if p.startswith('-') else f"+{p}" for p in term_parts])
            solution_value = eval(eval_str, {}, env)
        except Exception:
            for part in term_parts:
                if 'x' in part: solution_value += int(part.replace('x','')) * x_val
                elif 'y' in part: solution_value += int(part.replace('y','')) * y_val
                elif 'a' in part: solution_value += int(part.replace('a','')) * x_val
                elif 'b' in part: solution_value += int(part.replace('b','')) * y_val
                else: solution_value += int(part)

        term_str = " ".join([p if p.startswith('-') else f"+ {p}" for i, p in
                             enumerate(term_parts)]).replace("+ -", "-")

        if term_str.startswith("+ "): term_str = term_str[2:]

        question = f"Setze x={x_val} (und y={y_val}, falls vorhanden) ein und berechne den Termwert:\n{term_str}"

        eingesetzt_str = term_str
        for v, val in [('x', x_val), ('y', y_val), ('a', x_val), ('b', y_val)]:
            eingesetzt_str = eingesetzt_str.replace(v, f"({val})")

        eingesetzt_str = re.sub(r'(\d)\(', r'\1 * (', eingesetzt_str)
        eingesetzt_str = eingesetzt_str.replace(" (", " * (")

        steps = (
            f"**Aufgabe:** {question}\n\n"
            f"1. Schritt: Setze die Werte (x={x_val}, y={y_val}) in den Term ein.\n"
            f" - Term: {term_str}\n"
            f" - Eingesetzt: {eingesetzt_str}\n\n"
            f"2. Schritt: Berechne den Wert (Punkt vor Strich beachten).\n"
            f" - (Berechnung der einzelnen Term-Teile...)\n"
            f" - Gesamtwert = {solution_value}\n\n"
            f"**Ergebnis:** {round(solution_value, params['decimals'])}"
        )

        return question, round(solution_value, params['decimals']), steps

    #--- MODIFIZIERT: GEOMETRIE (2D & 3D) ---
    def _generate_geometrie(self):
        """Erstellt geometrische Aufgaben (2D und 3D).
        Gibt (q, a, steps, drawing_info) zurück."""
        params = self._get_params()
        year, _ = self._parse_class()

        available_shapes = ['Rechteck', 'Kreis', 'Dreieck']
        if year >= 6: # Ab Klasse 6 Trapez etc.
            available_shapes.append('Trapez')
        if year >= 7: # Ab Klasse 7 3D
            available_shapes.extend(['Würfel', 'Kugel', 'Quader', 'Zylinder', 'Kegel'])

        shape = random.choice(available_shapes)
        unit = "cm"

        max_dim = max(1, params['range'][1])
        if max_dim <= 0: max_dim = 1

        question, answer, steps = "", 0, ""
        drawing_info = None
        pi_val = 3.14159 # math.pi

        if shape == 'Rechteck':
            length = random.randint(1, max_dim)
            width = random.randint(1, length)
            drawing_info = {'shape': 'Rechteck', 'l': length, 'w': width}
            q_type = random.choice(['Umfang', 'Fläche'])

            if q_type == 'Umfang':
                question = f"Berechne den Umfang eines Rechtecks mit Länge {length}{unit} und Breite {width}{unit}."
                answer = 2 * (length + width)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: U = 2 * (l + w)\n"
                         f"2. Einsatz: U = 2 * ({length} + {width}) = {answer}\n\n"
                         f"**Ergebnis:** {answer} {unit}")
            else: # Fläche
                question = f"Berechne die Fläche eines Rechtecks mit Länge {length}{unit} und Breite {width}{unit}."
                answer = length * width
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: A = l * w\n"
                         f"2. Einsatz: A = {length} * {width} = {answer}\n\n"
                         f"**Ergebnis:** {answer} {unit}²")

        elif shape == 'Kreis':
            radius = random.randint(1, max(2, max_dim // 2))
            drawing_info = {'shape': 'Kreis', 'r': radius}
            q_type = random.choice(['Umfang', 'Fläche'])

            if q_type == 'Umfang':
                question = f"Berechne den Umfang eines Kreises mit Radius {radius}{unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = 2 * pi_val * radius
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: U = 2 * Pi * r\n"
                         f"2. Einsatz: U = 2 * {pi_val:.4f} * {radius} ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}")
            else: # Fläche
                question = f"Berechne die Fläche eines Kreises mit Radius {radius}{unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = pi_val * (radius ** 2)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: A = Pi * r²\n"
                         f"2. Einsatz: A = {pi_val:.4f} * {radius}² = {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}²")
            return question, round(answer, params['decimals']), steps, drawing_info

        elif shape == 'Dreieck': # Dreieck (Fläche)
            base = random.randint(1, max_dim)
            height = random.randint(1, max(2, base))
            drawing_info = {'shape': 'Dreieck', 'b': base, 'h': height}

            question = f"Berechne die Fläche eines Dreiecks mit Grundseite {base}{unit} und Höhe {height}{unit}."
            answer = 0.5 * base * height
            steps = (f"**Aufgabe:** {question}\n\n"
                     f"1. Formel: A = 0.5 * g * h\n"
                     f"2. Einsatz: A = 0.5 * {base} * {height} = {answer}\n\n"
                     f"**Ergebnis:** {answer} {unit}²")

        elif shape == 'Trapez':
            a = random.randint(1, max_dim)
            c = random.randint(1, a)
            h = random.randint(1, max_dim)
            drawing_info = {'shape': 'Trapez', 'a': a, 'c': c, 'h': h}

            question = f"Berechne die Fläche eines Trapez mit Seiten a={a}{unit}, c={c}{unit} und Höhe h={h}{unit}."
            answer = ((a+c)/2) * h
            steps = (f"**Aufgabe:** {question}\n\n"
                     f"1. Formel: A = ((a + c) / 2) * h\n"
                     f"2. Einsatz: A = (({a} + {c}) / 2) * {h}\n"
                     f"   A = ({ (a+c)/2 }) * {h} = {answer}\n\n"
                     f"**Ergebnis:** {answer} {unit}²")

        # --- NEUE 3D-KÖRPER ---
        elif shape == 'Würfel':
            a = random.randint(1, max(2, max_dim // 4))
            drawing_info = {'shape': 'Würfel', 'a': a}
            q_type = random.choice(['Volumen', 'Oberfläche'])

            if q_type == 'Volumen':
                question = f"Berechne das Volumen (V) eines Würfels mit Seitenlänge a = {a}{unit}."
                answer = a ** 3
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: V = a³\n"
                         f"2. Einsatz: V = {a}³ = {answer}\n\n"
                         f"**Ergebnis:** {answer} {unit}³")
            else: # Oberfläche
                question = f"Berechne die Oberfläche (O) eines Würfels mit Seitenlänge a = {a}{unit}."
                answer = 6 * (a ** 2)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: O = 6 * a²\n"
                         f"2. Einsatz: O = 6 * {a}² = 6 * {a**2} = {answer}\n\n"
                         f"**Ergebnis:** {answer} {unit}²")

        elif shape == 'Quader':
            l = random.randint(1, max(2, max_dim // 3))
            w = random.randint(1, max(2, max_dim // 3))
            h = random.randint(1, max(2, max_dim // 3))
            drawing_info = {'shape': 'Quader', 'l': l, 'w': w, 'h': h}
            q_type = random.choice(['Volumen', 'Oberfläche'])

            if q_type == 'Volumen':
                question = f"Berechne das Volumen (V) eines Quaders (l={l}, b={w}, h={h}){unit}."
                answer = l * w * h
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: V = l * b * h\n"
                         f"2. Einsatz: V = {l} * {w} * {h} = {answer}\n\n"
                         f"**Ergebnis:** {answer} {unit}³")
            else: # Oberfläche
                question = f"Berechne die Oberfläche (O) eines Quaders (l={l}, b={w}, h={h}){unit}."
                answer = 2 * (l*w + l*h + w*h)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: O = 2 * (lb + lh + bh)\n"
                         f"2. Einsatz: O = 2 * ({l}*{w} + {l}*{h} + {w}*{h})\n"
                         f"   O = 2 * ({l*w} + {l*h} + {w*h}) = {answer}\n\n"
                         f"**Ergebnis:** {answer} {unit}²")

        elif shape == 'Zylinder':
            radius = random.randint(1, max(2, max_dim // 4))
            height = random.randint(1, max(2, max_dim // 2))
            drawing_info = {'shape': 'Zylinder', 'r': radius, 'h': height}
            q_type = random.choice(['Volumen', 'Oberfläche'])

            if q_type == 'Volumen':
                question = f"Berechne das Volumen (V) eines Zylinders (r={radius}, h={height}){unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = pi_val * (radius**2) * height
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: V = Pi * r² * h\n"
                         f"2. Einsatz: V = {pi_val:.4f} * {radius}² * {height} ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}³")
            else: # Oberfläche (Mantel + 2*Grundfläche)
                question = f"Berechne die Oberfläche (O) eines Zylinders (r={radius}, h={height}){unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = (2 * pi_val * radius * height) + (2 * pi_val * (radius**2))
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: O = 2*Pi*r*h (Mantel) + 2*Pi*r² (Deckel/Boden)\n"
                         f"2. Einsatz: O = (2*{pi_val:.4f}*{radius}*{height}) + (2*{pi_val:.4f}*{radius}²) ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}²")
            return question, round(answer, params['decimals']), steps, drawing_info

        elif shape == 'Kegel':
            radius = random.randint(1, max(2, max_dim // 4))
            height = random.randint(1, max(2, max_dim // 2))
            drawing_info = {'shape': 'Kegel', 'r': radius, 'h': height}
            # Für Oberfläche 's' (Seitenlinie)
            s = math.sqrt(radius**2 + height**2)
            q_type = random.choice(['Volumen', 'Oberfläche'])

            if q_type == 'Volumen':
                question = f"Berechne das Volumen (V) eines Kegels (r={radius}, h={height}){unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = (1/3) * pi_val * (radius**2) * height
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: V = (1/3) * Pi * r² * h\n"
                         f"2. Einsatz: V = (1/3) * {pi_val:.4f} * {radius}² * {height} ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}³")
            else: # Oberfläche
                question = f"Berechne die Oberfläche (O) eines Kegels (r={radius}, h={height}){unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = (pi_val * radius**2) + (pi_val * radius * s)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: O = Pi*r² (Grundfläche) + Pi*r*s (Mantel)\n"
                         f"2. Seitenlinie s = √(r² + h²) = √({radius}² + {height}²) ≈ {s:.2f}\n"
                         f"3. Einsatz: O = ({pi_val:.4f} * {radius}²) + ({pi_val:.4f} * {radius} * {s:.2f}) ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}²")
            return question, round(answer, params['decimals']), steps, drawing_info

        elif shape == 'Kugel':
            radius = random.randint(1, max(2, max_dim // 4))
            drawing_info = {'shape': 'Kugel', 'r': radius}
            q_type = random.choice(['Volumen', 'Oberfläche'])

            if q_type == 'Volumen':
                question = f"Berechne das Volumen (V) einer Kugel mit Radius r = {radius}{unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = (4/3) * pi_val * (radius ** 3)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: V = (4/3) * Pi * r³\n"
                         f"2. Einsatz: V = (4/3) * {pi_val:.4f} * {radius}³ ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}³")
            else: # Oberfläche
                question = f"Berechne die Oberfläche (O) einer Kugel mit Radius r = {radius}{unit}. Runde auf {params['decimals']} Nachkommastellen (Pi={pi_val:.4f})."
                answer = 4 * pi_val * (radius ** 2)
                steps = (f"**Aufgabe:** {question}\n\n"
                         f"1. Formel: O = 4 * Pi * r²\n"
                         f"2. Einsatz: O = 4 * {pi_val:.4f} * {radius}² ≈ {answer}\n\n"
                         f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}²")
            return question, round(answer, params['decimals']), steps, drawing_info

        return question, round(answer, params['decimals']), steps, drawing_info

    def _generate_statistik(self):
        # ... (Unverändert) ...
        params = self._get_params()
        data_size = random.randint(5, 10)
        max_data_val = max(1, max(5, params['range'][1] // 2))
        data = [random.randint(1, max_data_val) for _ in range(data_size)]

        drawing_info = {'shape': 'BarChart', 'data': data}

        q_type = random.choice(['Mittelwert', 'Median'])
        question, answer, steps = "", 0, ""

        if q_type == 'Mittelwert':
            question = f"Berechne den Mittelwert der folgenden Datenreihe: {', '.join(map(str, data))}. Runde auf {params['decimals']} Nachkommastelle(n)."
            answer = sum(data) / len(data)
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"1. Schritt: Formel für Mittelwert (MW) notieren.\n"
                f" - MW = (Summe aller Werte) / (Anzahl der Werte)\n"
                f"2. Schritt: Alle Werte addieren.\n"
                f" - Summe = {' + '.join(map(str, data))} = {sum(data)}\n"
                f"3. Schritt: Anzahl der Werte zählen.\n"
                f" - Anzahl = {len(data)}\n"
                f"4. Schritt: Dividieren.\n"
                f" - MW = {sum(data)} / {len(data)} = {answer}\n\n"
                f"**Ergebnis (gerundet):** {round(answer, params['decimals'])}"
            )
            return question, round(answer, params['decimals']), steps, drawing_info

        else: # Median
            data_sorted = sorted(data)
            question = f"Berechne den Median der folgenden Datenreihe: {', '.join(map(str, data))}."
            n = len(data_sorted)
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"1. Schritt: Datenreihe der Größe nach ordnen.\n"
                f" - Original: {', '.join(map(str, data))}\n"
                f" - Sortiert: {', '.join(map(str, data_sorted))}\n"
                f"2. Schritt: Anzahl der Werte bestimmen: n = {n}.\n"
            )

            if n % 2 == 1:
                answer = data_sorted[n//2]
                steps += (
                    f"3. Schritt (n ist ungerade): Der Wert in der Mitte ist der Median.\n"
                    f" - Position: (n+1)/2 = {(n+1)//2}. Wert\n"
                    f" - Median = {answer}\n"
                )
            else:
                answer = (data_sorted[n//2 - 1] + data_sorted[n//2]) / 2
                steps += (
                    f"3. Schritt (n ist gerade): Der Durchschnitt der beiden mittleren Werte ist der Median.\n"
                    f" - Mittlere Werte (Position {n//2} und {n//2 + 1}): {data_sorted[n//2 - 1]} und {data_sorted[n//2]}\n"
                    f" - Median = ({data_sorted[n//2 - 1]} + {data_sorted[n//2]}) / 2 = {answer}\n"
                )

            steps += f"\n**Ergebnis:** {answer}"
            return question, answer, steps, drawing_info

    #--- NEUE GENERATOREN ---
    def _generate_stochastik(self):
        # ... (Unverändert) ...
        params = self._get_params()
        q_type = random.choice(['Wuerfel', 'Urne'])

        if q_type == 'Wuerfel':
            n = 6 # Standard W6
            event_n = random.randint(1, 5)
            question = (f"Ein idealer 6-seitiger Würfel (W6) wird einmal geworfen.\n"
                        f"Wie groß ist die Wahrscheinlichkeit P(Ergebnis <= {event_n})? "
                        f"(Runde auf {params['decimals']
                        } Nachkommastellen)")
            answer = event_n / n
            steps = (f"**Aufgabe:** {question}\n\n"
                     f"1. Formel (Laplace): P(E) = |E| / |Ω|\n"
                     f"2. |Ω| (Alle möglichen Ergebnisse): 6 (Zahlen 1-6)\n"
                     f"3. |E| (Günstige Ergebnisse <= {event_n}): {event_n} (Zahlen 1 bis {event_n})\n"
                     f"4. P(E) = {event_n} / {n} = {answer}\n\n"
                     f"**Ergebnis (gerundet):** {round(answer, params['decimals'])}")

        else: # Urne
            r = random.randint(1, 9)
            b = random.randint(1, 9)
            total = r + b
            question = (f"In einer Urne befinden sich {r} rote und {b} blaue Kugeln. Es wird einmal gezogen.\n"
                        f"Wie groß ist die Wahrscheinlichkeit P(rot)? "
                        f"(Runde auf {params['decimals']} Nachkommastellen)")
            answer = r / total
            steps = (f"**Aufgabe:** {question}\n\n"
                     f"1. Formel (Laplace): P(E) = |E| / |Ω|\n"
                     f"2. |Ω| (Alle Kugeln): {r} (rot) + {b} (blau) = {total}\n"
                     f"3. |E| (Günstige Ergebnisse 'rot'): {r}\n"
                     f"4. P(E) = {r} / {total} = {answer}\n\n"
                     f"**Ergebnis (gerundet):** {round(answer, params['decimals'])}")

        return question, round(answer, params['decimals']), steps

    def _generate_polynomdivision(self):
        # ... (Unverändert) ...
        params = self._get_params()

        # P(x) = ax^2 + bx + c
        a = random.randint(1, 5)
        b = random.randint(-5, 5)
        c = random.randint(-5, 5)

        # Divisor (x - val)
        val = random.randint(1, 4)

        polynom_str = f"{a}x² + {b}x + {c}".replace("+ -", "- ")
        divisor_str = f"(x - {val})"

        # Antwort nach Satz vom Rest: P(val)
        answer = a * (val**2) + b * val + c

        question = (f"Berechnen Sie den **Rest** der folgenden Polynomdivision:\n\n"
                    f"({polynom_str}) : {divisor_str}")

        steps = (f"**Aufgabe:** {question}\n\n"
                 f"1. Methode: Satz vom Rest (Remainder Theorem).\n"
                 f"   Der Rest der Division P(x) : (x - a) ist P(a).\n"
                 f"2. Polynom P(x) = {polynom_str}\n"
                 f"3. Divisor (x - {val}). Der Wert 'a' ist also {val}.\n"
                 f"4. Setze a = {val} in P(x) ein:\n"
                 f"   Rest = P({val}) = {a}*({val}²) + {b}*({val}) + {c}\n"
                 f"   Rest = {a}*({val**2}) + {b*val} + {c}\n"
                 f"   Rest = {a * (val**2)} + {b*val} + {c} = {answer}\n\n"
                 f"**Ergebnis (Rest):** {answer}")

        return question, round(answer, params['decimals']), steps

    def _generate_vektoren(self):
        # ... (Unverändert) ...
        params = self._get_params()

        # 2D (Leicht/Mittel) oder 3D (Schwer)
        dim = 3 if self.difficulty == "Schwer" else 2

        # Vektor 1
        v1 = [random.randint(params['range'][0], params['range'][1]) for _ in range(dim)]

        q_type = random.choice(['Betrag', 'Skalarprodukt'])

        if q_type == 'Betrag':
            v_str = f"({', '.join(map(str, v1))})"
            question = (f"Berechnen Sie den Betrag (Länge) |v| des Vektors v = {v_str}.\n"
                        f"(Runde auf {params['decimals']} Nachkommastellen)")

            sum_sq = sum(n**2 for n in v1)
            answer = math.sqrt(sum_sq)

            steps = (f"**Aufgabe:** {question}\n\n"
                     f"1. Formel (Betrag): |v| = √(v₁² + v₂² + ...)\n"
                     f"2. Einsatz: |v| = √({'² + '.join(map(str, v1))}²)\n"
                     f"3. Quadrate: |v| = √({' + '.join(map(str, [n**2 for n in v1]))})\n"
                     f"4. Summe: |v| = √({sum_sq}) ≈ {answer}\n\n"
                     f"**Ergebnis (gerundet):** {round(answer, params['decimals'])}")

        else: # Skalarprodukt
            # Vektor 2
            v2 = [random.randint(params['range'][0], params['range'][1]) for _ in range(dim)]

            v1_str = f"({', '.join(map(str, v1))})"
            v2_str = f"({', '.join(map(str, v2))})"

            question = (f"Berechnen Sie das Skalarprodukt v • w der Vektoren:\n"
                        f"v = {v1_str}\n"
                        f"w = {v2_str}\n"
                        f"(Runde auf {params['decimals']} Nachkommastellen)")

            answer = sum(v1[i] * v2[i] for i in range(dim))

            steps = (f"**Aufgabe:** {question}\n\n"
                     f"1. Formel (Skalarprodukt): v•w = v₁w₁ + v₂w₂ + ...\n"
                     f"2. Einsatz:\n"
                     f"   v•w = {' + '.join([f'({v1[i]}*{v2[i]})' for i in range(dim)])}\n"
                     f"3. Produkte:\n"
                     f"   v•w = {' + '.join(map(str, [v1[i]*v2[i] for i in range(dim)]))}\n"
                     f"4. Summe: v•w = {answer}\n\n"
                     f"**Ergebnis (gerundet):** {round(answer, params['decimals'])}")

        return question, round(answer, params['decimals']), steps

#=================================================================================
#--- ÜBUNGSSESSION KLASSE ---------------------------------------------------------
#=================================================================================

class AufgabenSession:
    # ... (Unverändert) ...
    def __init__(self, parent_app, topic, difficulty, class_name):
        self.parent_app = parent_app
        self.topic = topic
        self.difficulty = difficulty
        self.class_name = class_name
        self.num_questions = 10
        self.time_limit = self._get_time_limit(difficulty)

        self.generator = AufgabenGenerator(topic, difficulty, class_name, self.num_questions)
        self.current_question_index = 0
        self.start_time = time.time()
        self.time_left = self.time_limit
        self.timer_id = None

        self._create_session_window()

    def _get_time_limit(self, difficulty):
        if difficulty == "Leicht":
            return 600
        elif difficulty == "Mittel":
            return 900
        else:
            return 1200

    def _create_session_window(self):
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title(f"Übung: {self.topic} ({self.difficulty}) | {self.class_name}")
        self.window.attributes('-fullscreen', True)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel_session)

        self.frame = tk.Frame(self.window, bg="#f5f5f5")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)

        tk.Label(self.frame, text=f"Aufgaben: {self.topic} ({self.difficulty}) | {self.class_name}",
                 font=("Arial", 32, "bold"), bg="#f5f5f5").pack(pady=(10, 20))

        self.timer_label = tk.Label(self.frame, text=f"Verbleibende Zeit: {self.time_left}s",
                                    font=("Courier", 18), fg="red", bg="#f5f5f5")
        self.timer_label.pack(pady=10)

        self.question_label = tk.Label(self.frame, text="", font=("Arial", 20),
                                       wraplength=800, justify=tk.CENTER, bg="#f5f5f5")
        self.question_label.pack(pady=30)

        self.answer_entry = ttk.Entry(self.frame, font=("Arial", 20), justify=tk.CENTER)
        self.answer_entry.pack(pady=10, ipadx=50, ipady=10)
        self.answer_entry.bind('<Return>', self._check_answer)
        ToolTip(self.answer_entry, "Eingabe der Antwort. Bestätigung mit **Enter**.")

        self.next_button = ttk.Button(self.frame, text="Antwort prüfen & Weiter >>",
                                      command=self._check_answer, style='Big.TButton')
        self.next_button.pack(pady=20)
        ToolTip(self.next_button, "Prüft die Antwort und geht zur nächsten Frage.")

        self.cancel_button = ttk.Button(self.frame, text="Übung abbrechen & zum Hauptmenü",
                                        command=self._cancel_session, style='TButton')
        self.cancel_button.pack(pady=40)
        ToolTip(self.cancel_button, "Bricht die aktuelle Übung ab. Der Fortschritt geht verloren.")

        self.window.focus_set()
        self._update_question()
        self._start_timer()

    def _cancel_session(self, event=None):
        if messagebox.askyesno("Abbrechen bestätigen",
                               "Möchten Sie die Übung wirklich abbrechen? Der aktuelle Fortschritt geht dabei verloren.",
                               parent=self.window):
            if self.timer_id:
                self.window.after_cancel(self.timer_id)
            self.window.destroy()
            self.parent_app.show_main_menu()
            print("Übung abgebrochen. Zurück zum Hauptmenü.")

    def _start_timer(self):
        self.time_left = self.time_limit
        self._update_timer_label()
        self._countdown()

    def _update_timer_label(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.config(text=f"Verbleibende Zeit: {minutes:02d}:{seconds:02d}")

    def _countdown(self):
        if self.time_left > 0:
            self.time_left -= 1
            self._update_timer_label()
            self.timer_id = self.window.after(1000, self._countdown)
        else:
            self._finish_session(timeout=True)

    def _update_question(self):
        q_data = self.generator.questions[self.current_question_index]

        self.question_label.config(text=f"Frage {q_data['id']}/{self.num_questions}:\n{q_data['question']}")
        self.answer_entry.delete(0, tk.END)

        if self.current_question_index == self.num_questions - 1:
            self.next_button.config(text="Antwort prüfen & Beenden (Letzte Frage)")
        else:
            self.next_button.config(text="Antwort prüfen & Weiter >>")

        self.answer_entry.focus_set()

    def _check_answer(self, event=None):
        if self.current_question_index >= self.num_questions:
            self._finish_session()
            return

        user_input = self.answer_entry.get().strip()
        cleaned_input = user_input.replace('.', '').replace(',', '.')

        q_data = self.generator.questions[self.current_question_index]

        try:
            user_answer = float(cleaned_input)
            q_data['user_answer'] = user_answer
        except ValueError:
            if cleaned_input == "":
                user_answer = None
                q_data['user_answer'] = None
            else:
                user_answer = "Ungültige Eingabe"
                q_data['user_answer'] = user_answer

        correct_answer = q_data['correct_answer']
        solution_steps = q_data.get('solution_steps', "Kein detaillierter Lösungsweg verfügbar.")
        is_correct = False

        if isinstance(user_answer, (int, float)) and abs(user_answer - correct_answer) < 0.1:
            is_correct = True

        drawing_info = q_data.get('drawing_info')

        if is_correct:
            FeedbackDialog(self.window,
                           "Antwortprüfung",
                           is_correct=True,
                           message="Sehr gut gemacht!")
        else:
            correct_answer_formatted = format_german(correct_answer)
            feedback_msg = (
                f"Deine Eingabe: {user_input if user_input else 'Keine Angabe'}\n"
                f"Das korrekte Ergebnis lautet: {correct_answer_formatted}\n\n"
                f"--- **Lösungsweg** ---\n{solution_steps}"
            )

            FeedbackDialog(self.window,
                           "Antwortprüfung",
                           is_correct=False,
                           message=feedback_msg,
                           drawing_info=drawing_info)

        self.current_question_index += 1

        if self.current_question_index == self.num_questions:
            self._finish_session()
        else:
            self._update_question()

    def _finish_session(self, timeout=False):
        if self.timer_id:
            self.window.after_cancel(self.timer_id)

        elapsed_time = (time.time() - self.start_time)
        if timeout:
            elapsed_time = self.time_limit
        else:
            elapsed_time = self.time_limit - self.time_left

        correct_count = 0
        total_count = self.num_questions

        for q in self.generator.questions:
            if isinstance(q['user_answer'], (int, float)) and abs(q['user_answer'] - q['correct_answer']) < 0.1:
                correct_count += 1

        full_topic = f"{self.topic} ({self.difficulty})"

        self.parent_app.db.save_result(full_topic, self.class_name, correct_count, total_count, elapsed_time)

        result_msg = "⏱️Übungszeit abgelaufen!" if timeout else "✅Übung beendet!"
        result_msg += (f"\n\nKlasse: {self.class_name}\n"
                       f"Thema: {full_topic}\n"
                       f"Richtige Antworten: {correct_count} von {total_count}\n"
                       f"Genutzte Zeit: {elapsed_time:.1f}s / {self.time_limit}s\n"
                       f"Ergebnis in Datenbank gespeichert.")

        messagebox.showinfo("Übungsergebnis", result_msg)
        self.window.destroy()
        self.parent_app.show_main_menu()

#=================================================================================
#--- NEUE HALBJAHRESTEST-SESSION KLASSE -------------------------------------------
#=================================================================================

class HalbjahrestestSession:
    # ... (Unverändert, nutzt jetzt automatisch die neuen Geometrie-Aufgaben, wenn Klasse >= 7) ...
    def __init__(self, parent_app, class_name):
        self.parent_app = parent_app
        self.class_name = class_name

        self.all_questions = []
        self._generate_test_questions() # Füllt self.all_questions

        self.num_questions = len(self.all_questions) # Sollte 23 sein
        self.time_limit = self._get_time_limit() # 30 Minuten

        self.current_question_index = 0
        self.start_time = time.time()
        self.time_left = self.time_limit
        self.timer_id = None

        self._create_session_window()

    def _get_time_limit(self):
        """Liefert das Zeitlimit in Sekunden für den Test (30 Minuten)."""
        return 1800

    def _generate_test_questions(self):
        """Erstellt die 23 Testfragen basierend auf dem Lernstand."""

        # 1. Verfügbare Themen für die Klasse ermitteln
        _, _, current_total_semester = self.parent_app._parse_selected_class()

        # --- MODIFIZIERT: Alle Themen auflisten ---
        all_topics = [
            "Zahlenraum-Training", "Terme & Gleichungen", "Geometrie", "Statistik",
            "Stochastik", "Polynomdivision", "Vektor-Berechnung"
        ]

        available_topics = [
            t for t in all_topics
            if current_total_semester >= self.parent_app._get_min_class(t)
        ]

        if not available_topics:
            available_topics = ["Zahlenraum-Training"]

        self.all_questions = []

        # 2. Genaue Anzahl pro Schwierigkeitsgrad definieren
        specs = [("Leicht", 15), ("Mittel", 5), ("Schwer", 3)]

        for difficulty, count in specs:
            for _ in range(count):
                topic = random.choice(available_topics)

                gen = AufgabenGenerator(topic, difficulty, self.class_name, num_questions=1)

                if gen.questions:
                    self.all_questions.append(gen.questions[0])

        # 3. Alle 23 Fragen mischen
        random.shuffle(self.all_questions)

        # 4. IDs neu nummerieren
        for i, q in enumerate(self.all_questions):
            q['id'] = i + 1

        self.num_questions = len(self.all_questions)
        print(f"Halbjahrestest generiert: {self.num_questions} Fragen (aus {available_topics}) für {self.class_name}.")


    def _create_session_window(self):
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title(f"Halbjahrestest! | {self.class_name}")
        self.window.attributes('-fullscreen', True)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel_session)

        self.frame = tk.Frame(self.window, bg="#f5f5f5")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)

        tk.Label(self.frame, text=f"Halbjahrestest! | {self.class_name}",
                 font=("Arial", 32, "bold"), bg="#f5f5f5").pack(pady=(10, 20))

        self.timer_label = tk.Label(self.frame, text=f"Verbleibende Zeit: {self.time_left}s",
                                    font=("Courier", 18), fg="red", bg="#f5f5f5")
        self.timer_label.pack(pady=10)

        self.question_label = tk.Label(self.frame, text="", font=("Arial", 20),
                                       wraplength=800, justify=tk.CENTER, bg="#f5f5f5")
        self.question_label.pack(pady=30)

        self.answer_entry = ttk.Entry(self.frame, font=("Arial", 20), justify=tk.CENTER)
        self.answer_entry.pack(pady=10, ipadx=50, ipady=10)
        self.answer_entry.bind('<Return>', self._check_answer)
        ToolTip(self.answer_entry, "Eingabe der Antwort. Bestätigung mit **Enter**.")

        self.next_button = ttk.Button(self.frame, text="Antwort prüfen & Weiter >>",
                                      command=self._check_answer, style='Big.TButton')
        self.next_button.pack(pady=20)
        ToolTip(self.next_button, "Prüft die Antwort und geht zur nächsten Frage.")

        self.cancel_button = ttk.Button(self.frame, text="Test abbrechen & zum Hauptmenü",
                                        command=self._cancel_session, style='TButton')
        self.cancel_button.pack(pady=40)
        ToolTip(self.cancel_button, "Bricht den Test ab. Der Fortschritt geht verloren.")

    def _cancel_session(self, event=None):
        if messagebox.askyesno("Abbrechen bestätigen",
                               "Möchten Sie den Test wirklich abbrechen? Der aktuelle Fortschritt geht dabei verloren.",
                               parent=self.window):
            if self.timer_id:
                self.window.after_cancel(self.timer_id)
            self.window.destroy()
            self.parent_app.show_main_menu()
            print("Test abgebrochen. Zurück zum Hauptmenü.")

    def _start_timer(self):
        self.time_left = self.time_limit
        self._update_timer_label()
        self._countdown()

    def _update_timer_label(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.config(text=f"Verbleibende Zeit: {minutes:02d}:{seconds:02d}")

    def _countdown(self):
        if self.time_left > 0:
            self.time_left -= 1
            self._update_timer_label()
            self.timer_id = self.window.after(1000, self._countdown)
        else:
            self._finish_session(timeout=True)

    def _update_question(self):
        q_data = self.all_questions[self.current_question_index]

        self.question_label.config(text=f"Frage {q_data['id']}/{self.num_questions}:\n{q_data['question']}")
        self.answer_entry.delete(0, tk.END)

        if self.current_question_index == self.num_questions - 1:
            self.next_button.config(text="Antwort prüfen & Beenden (Letzte Frage)")
        else:
            self.next_button.config(text="Antwort prüfen & Weiter >>")

        self.answer_entry.focus_set()

    def _check_answer(self, event=None):
        if self.current_question_index >= self.num_questions:
            self._finish_session()
            return

        user_input = self.answer_entry.get().strip()
        cleaned_input = user_input.replace('.', '').replace(',', '.')

        q_data = self.all_questions[self.current_question_index]

        try:
            user_answer = float(cleaned_input)
            q_data['user_answer'] = user_answer
        except ValueError:
            if cleaned_input == "":
                user_answer = None
                q_data['user_answer'] = None
            else:
                user_answer = "Ungültige Eingabe"
                q_data['user_answer'] = user_answer

        correct_answer = q_data['correct_answer']
        solution_steps = q_data.get('solution_steps', "Kein detaillierter Lösungsweg verfügbar.")
        is_correct = False

        if isinstance(user_answer, (int, float)) and abs(user_answer - correct_answer) < 0.1:
            is_correct = True

        drawing_info = q_data.get('drawing_info')

        if is_correct:
            FeedbackDialog(self.window,
                           "Antwortprüfung",
                           is_correct=True,
                           message="Sehr gut gemacht!")
        else:
            correct_answer_formatted = format_german(correct_answer)
            feedback_msg = (
                f"Deine Eingabe: {user_input if user_input else 'Keine Angabe'}\n"
                f"Das korrekte Ergebnis lautet: {correct_answer_formatted}\n\n"
                f"--- **Lösungsweg** ---\n{solution_steps}"
            )

            FeedbackDialog(self.window,
                           "Antwortprüfung",
                           is_correct=False,
                           message=feedback_msg,
                           drawing_info=drawing_info)

        self.current_question_index += 1

        if self.current_question_index == self.num_questions:
            self._finish_session()
        else:
            self._update_question()

    def _show_certificate(self):
        ZertifikatDialog(self.window, self.class_name)

    def _finish_session(self, timeout=False):
        if self.timer_id:
            self.window.after_cancel(self.timer_id)

        elapsed_time = (time.time() - self.start_time)
        if timeout:
            elapsed_time = self.time_limit
        else:
            elapsed_time = self.time_limit - self.time_left

        correct_count = 0
        total_count = self.num_questions

        for q in self.all_questions:
            if isinstance(q['user_answer'], (int, float)) and abs(q['user_answer'] - q['correct_answer']) < 0.1:
                correct_count += 1

        full_topic = "Halbjahrestest"
        self.parent_app.db.save_result(full_topic, self.class_name, correct_count, total_count, elapsed_time)

        passing_threshold = 0.90
        score = 0
        if total_count > 0:
            score = correct_count / total_count

        is_passed = score >= passing_threshold

        result_msg = "⏱️Testzeit abgelaufen!" if timeout else "✅Test beendet!"
        result_msg += (f"\n\nKlasse: {self.class_name}\n"
                       f"Thema: {full_topic}\n"
                       f"Richtige Antworten: {correct_count} von {total_count}\n"
                       f"Erreichte Punktzahl: {score*100:.1f}%\n"
                       f"Benötigt zum Bestehen: {passing_threshold*100}%\n\n"
                       f"Ergebnis in Datenbank gespeichert.")

        if is_passed:
            result_msg += "\n\nHERZLICHEN GLÜCKWUNSCH! Test bestanden!"
        else:
            result_msg += "\n\nLeider nicht bestanden. Versuche es erneut!"

        messagebox.showinfo("Testergebnis", result_msg, parent=self.window)

        if is_passed:
            self._show_certificate()

        self.window.destroy()
        self.parent_app.show_main_menu()


#=================================================================================
#--- HAUPTANWENDUNG ---------------------------------------------------------------
#=================================================================================

class MatheGenieApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mathegenie by Rainer Liegard")

        self.db = DatabaseManager()
        self.root.attributes('-fullscreen', True)

        self.current_frame = None
        self.schuljahr_options = [f"Klasse {j}.{h}" for j in range(1, 14) for h in range(1, 3)]

        self.selected_schuljahr = tk.StringVar(self.root)
        self.selected_schuljahr.set(self.schuljahr_options[0])
        self.schuljahr_dropdown = None

        self.show_splash_screen()

    def _parse_selected_class(self):
        """Extrahiert Jahr und Halbjahr aus self.selected_schuljahr und berechnet das Gesamtsemester."""
        class_name = self.selected_schuljahr.get()
        parts = class_name.split()
        if len(parts) > 1:
            grade_parts = parts[1].split('.')
            if len(grade_parts) == 2:
                try:
                    year = int(grade_parts[0])
                    semester = int(grade_parts[1])
                    total_semester = (year - 1) * 2 + semester
                    return year, semester, total_semester
                except ValueError:
                    pass
        return 1, 1, 1

    # --- MODIFIZIERT: Neue Klassenstufen ---
    def _get_min_class(self, topic):
        """Definiert das Mindest-Semester (Gesamtsemester-Index) für ein Thema."""
        mapping = {
            "Zahlenraum-Training": 1,
            "Terme & Gleichungen": 9,  # Kl 5.1
            "Geometrie": 9,             # Kl 5.1 (3D-Inhalte werden intern nach Jahr gesteuert)
            "Statistik": 13,            # Kl 7.1
            "Stochastik": 15,           # Kl 8.1
            "Polynomdivision": 19,    # Kl 10.1
            "Vektor-Berechnung": 19     # Kl 10.1
        }
        return mapping.get(topic, 1)

    def _show_toast_message(self, message):
        """Simuliert eine kurze, nicht-blockierende 'Toast'-Nachricht."""
        toast = tk.Toplevel(self.root)
        toast.wm_overrideredirect(True)

        label = tk.Label(toast, text=message,
                         bg="#2c3e50", fg="white",
                         font=("Arial", 14, "bold"),
                         padx=20, pady=10)
        label.pack()

        toast.update_idletasks()

        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        toast_width = toast.winfo_width()
        toast_height = toast.winfo_height()

        x = (root_width // 2) - (toast_width // 2)
        y = root_height - toast_height - 50

        toast.wm_geometry(f"+{x}+{y}")

        self.root.after(3000, toast.destroy)

    def clear_screen(self):
        """Entfernt alle Frames."""
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
        self.clear_screen()
        current_class = self.selected_schuljahr.get()
        AufgabenSession(self, topic, difficulty, current_class)

    def handle_progress_menu(self, event=None):
        self.show_progress_menu()

    def handle_formula_menu(self, event=None):
        self.show_formula_menu()

    def handle_semester_test(self, event=None):
        """Startet den Halbjahrestest."""
        self.clear_screen()
        current_class = self.selected_schuljahr.get()
        HalbjahrestestSession(self, current_class)

    # --- Untermenü und Hauptmenü ---

    def show_topic_submenu(self, topic, menu_frame):
        # 1. PRÜFUNG: Ist das Thema für die aktuelle Klasse freigegeben?
        _, _, current_total_semester = self._parse_selected_class()
        min_total_semester = self._get_min_class(topic)
        if current_total_semester < min_total_semester:
            year = (min_total_semester - 1) // 2 + 1
            semester = (min_total_semester - 1) % 2 + 1

            self._show_toast_message(f"🚫Thema '{topic}' ist erst ab Klasse {year}.{semester} verfügbar!")
            self.root.focus_set()
            return

        # 2. Untermenü anzeigen
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
            ("Leicht", "Basis-Aufgaben...", "#D4EDDA", 'Leicht'),
            ("Mittel", "Standard-Aufgaben...", "#FFF3CD", 'Mittel'),
            ("Schwer", "Erweiterte Aufgaben...", "#F8D7DA", 'Schwer')
        ]

        for i, (level_text, tooltip_text, color, level) in enumerate(difficulties):
            button_style = f'{level}.TButton'
            style.configure(button_style, font=('Arial', 20, 'bold'), padding=20, background=color)

            command_func = lambda t=topic, d=level: self.start_practice_session(t, d)

            button = ttk.Button(button_container, text=level_text, command=command_func, style=button_style)
            button.grid(row=0, column=i, padx=30, ipadx=50, ipady=30)

            ToolTip(button, tooltip_text)

        back_button = ttk.Button(submenu_frame, text="⬅️Zurück zum Hauptmenü",
                                 command=self.show_main_menu)
        back_button.pack(pady=50)
        ToolTip(back_button, "Kehrt zum Hauptmenü zurück.")

        self.root.focus_set()

    def show_progress_menu(self, event=None):
        # ... (Unverändert) ...
        self.clear_screen()

        progress_frame = tk.Frame(self.root, bg="#ecf0f1")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = progress_frame

        tk.Label(progress_frame, text="Lernfortschritt und Ergebnisse (SQLite-Datenbank)",
                 font=("Arial", 28, "bold"), bg="#ecf0f1").pack(pady=20)

        columns = ("ID", "Thema", "Klasse", "Richtig", "Gesamt", "Dauer (s)", "Datum")
        self.tree = ttk.Treeview(progress_frame, columns=columns, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=50, pady=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.CENTER)

        self.tree.column("ID", width=50, stretch=tk.NO)
        self.tree.column("Klasse", width=100, stretch=tk.NO)

        self.load_results_to_tree()

        control_frame = tk.Frame(progress_frame, bg="#ecf0f1")
        control_frame.pack(pady=10)

        delete_button = ttk.Button(control_frame, text="🗑️Ergebnis löschen",
                                   command=self.delete_selected_result)
        delete_button.pack(side=tk.LEFT, padx=10)
        ToolTip(delete_button, "Löscht das ausgewählte Ergebnis aus der Datenbank.")

        edit_button = ttk.Button(control_frame, text="🔄Bearbeiten (Simuliert)",
                                 command=self.simulate_edit_result)
        edit_button.pack(side=tk.LEFT, padx=10)
        ToolTip(edit_button, "Simuliert eine manuelle Korrektur des Ergebnisses.")

        back_button = ttk.Button(control_frame, text="⬅️Zurück zum Hauptmenü",
                                 command=self.show_main_menu)
        back_button.pack(side=tk.LEFT, padx=10)
        ToolTip(back_button, "Zurück zum Hauptmenü.")

        self.root.focus_set()

    def load_results_to_tree(self):
        # ... (Unverändert) ...
        for item in self.tree.get_children():
            self.tree.delete(item)

        results = self.db.get_all_results()
        for row in results:
            display_row = list(row)
            display_row[5] = f"{row[5]:.1f}" # Dauer formatieren
            self.tree.insert("", tk.END, values=display_row)

    def delete_selected_result(self, event=None):
        # ... (Unverändert) ...
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
        # ... (Unverändert) ...
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Bearbeiten", "Bitte wählen Sie ein Ergebnis zum Bearbeiten.")
            return

        old_values = self.tree.item(selected_item)['values']
        result_id = old_values[0]

        new_correct = int(old_values[3]) + 1
        new_total = int(old_values[4])
        new_duration = float(old_values[5]) * 0.9

        if new_correct > new_total: new_correct = new_total

        self.db.update_result(result_id, new_correct, new_total, new_duration)
        self.load_results_to_tree()
        messagebox.showinfo("Bearbeitet", f"Ergebnis ID {result_id} wurde simuliert bearbeitet.")

    # --- MODIFIZIERT: FORMELMENÜ (Massiv erweitert) ---
    def show_formula_menu(self, event=None):
        """Erstellt und zeigt die Ansicht mit den Formeln."""
        self.clear_screen()

        formula_frame = tk.Frame(self.root, bg="#ecf0f1")
        formula_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = formula_frame

        tk.Label(formula_frame, text="Formelsammlung",
                 font=("Arial", 28, "bold"), bg="#ecf0f1").pack(pady=20)

        canvas_frame = tk.Frame(formula_frame, bg="#ecf0f1")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=10)

        main_canvas = tk.Canvas(canvas_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=main_canvas.yview)

        scrollable_frame = tk.Frame(main_canvas, bg="#ffffff")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(
                scrollregion=main_canvas.bbox("all")
            )
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Inhalt für Formeln ---
        def add_heading(text):
            tk.Label(scrollable_frame, text=text, font=("Arial", 18, "bold", "underline"),
                     bg="#ffffff", justify=tk.LEFT, anchor="w").pack(fill="x", padx=20, pady=(15, 5))

        def add_text(text):
            tk.Label(scrollable_frame, text=text, font=("Arial", 12),
                     bg="#ffffff", justify=tk.LEFT, anchor="w", wraplength=800).pack(fill="x", padx=40, pady=2)

        def add_formula(text):
            tk.Label(scrollable_frame, text=text, font=("Courier", 14, "bold"),
                     bg="#f5f5f5", justify=tk.LEFT, anchor="w", relief="solid", borderwidth=1).pack(fill="x", padx=40, pady=5)

        # Helper-Funktion zum Zeichnen (angepasst für 3D)
        def add_sketch(info):
            canvas = tk.Canvas(scrollable_frame, width=220, height=150, bg="white", highlightthickness=1,
                               highlightbackground="black")
            shape = info.get('shape')

            # 2D
            if shape == 'Rechteck':
                l_text = f"Länge: {info.get('l', '?')}"
                w_text = f"Breite: {info.get('w', '?')}"
                canvas.create_rectangle(40, 40, 180, 110, outline="blue", width=2)
                canvas.create_text(110, 30, text=l_text, fill="black")
                canvas.create_text(30, 75, text=w_text, fill="black", anchor="e")

            elif shape == 'Kreis':
                r = info.get('r', '?')
                r_text = f"Radius: {r}"
                canvas.create_oval(60, 20, 160, 120, outline="red", width=2)
                canvas.create_line(110, 70, 160, 70, fill="red", dash=(4, 2))
                canvas.create_text(135, 80, text=r_text, fill="black", anchor="w")

            elif shape == 'Dreieck':
                b_text = f"g: {info.get('b', '?')}"
                h_text = f"h: {info.get('h', '?')}"
                canvas.create_polygon(50, 120, 170, 120, 50, 30, fill="#eeeeee", outline="purple", width=2)
                canvas.create_line(50, 120, 50, 30, fill="purple", dash=(4, 2))
                canvas.create_text(110, 130, text=b_text, fill="black")
                canvas.create_text(40, 75, text=h_text, fill="black", anchor="e")

            elif shape == 'Trapez':
                a_text = f"a: {info.get('a', '?')}"
                c_text = f"c: {info.get('c', '?')}"
                h_text = f"h: {info.get('h', '?')}"
                canvas.create_polygon(50, 110, 170, 110, 130, 40, 90, 40, fill="#eeeeee", outline="orange", width=2)
                canvas.create_line(50, 110, 50, 40, fill="orange", dash=(4, 2))
                canvas.create_text(110, 120, text=a_text, fill="black")
                canvas.create_text(110, 30, text=c_text, fill="black")
                canvas.create_text(40, 75, text=h_text, fill="black", anchor="e")

            # 3D
            elif shape == 'Würfel':
                a_text = f"a: {info.get('a', '?')}"
                canvas.create_rectangle(70, 70, 150, 150, outline="black", width=2)
                canvas.create_rectangle(50, 50, 130, 130, outline="grey", width=1)
                canvas.create_line(70, 70, 50, 50, outline="grey")
                canvas.create_line(150, 70, 130, 50, outline="grey")
                canvas.create_line(70, 150, 50, 130, outline="grey")
                canvas.create_line(150, 150, 130, 130, outline="grey")
                canvas.create_text(60, 110, text=a_text, fill="black")

            elif shape == 'Kugel':
                r = info.get('r', '?')
                r_text = f"Radius: {r}"
                canvas.create_oval(60, 30, 160, 130, outline="blue", width=2)
                canvas.create_oval(60, 75, 160, 85, outline="blue", dash=(4, 2))
                canvas.create_line(110, 80, 160, 80, fill="blue", dash=(2, 2))
                canvas.create_text(135, 90, text=r_text, fill="black", anchor="w")

            elif shape == 'Quader':
                l_text = f"l: {info.get('l', '?')}"
                w_text = f"b: {info.get('w', '?')}"
                h_text = f"h: {info.get('h', '?')}"
                canvas.create_rectangle(70, 70, 170, 130, outline="black", width=2)
                canvas.create_rectangle(50, 50, 150, 110, outline="grey", width=1)
                canvas.create_line(70, 70, 50, 50, outline="grey")
                canvas.create_line(170, 70, 150, 50, outline="grey")
                canvas.create_line(70, 130, 50, 110, outline="grey")
                canvas.create_line(170, 130, 150, 110, outline="grey")
                canvas.create_text(120, 60, text=l_text, fill="black")
                canvas.create_text(160, 60, text=w_text, fill="black")
                canvas.create_text(60, 100, text=h_text, fill="black")

            elif shape == 'Zylinder':
                r_text = f"r: {info.get('r', '?')}"
                h_text = f"h: {info.get('h', '?')}"
                canvas.create_oval(50, 110, 170, 130, outline="black", width=2, fill="#ddddff")
                canvas.create_line(50, 120, 50, 50, outline="black", width=2)
                canvas.create_line(170, 120, 170, 50, outline="black", width=2)
                canvas.create_oval(50, 40, 170, 60, outline="black", width=2, fill="#ddddff")
                canvas.create_line(110, 120, 110, 50, fill="grey", dash=(2,2))
                canvas.create_text(40, 85, text=h_text, fill="black")
                canvas.create_text(110, 30, text=r_text, fill="black")

            elif shape == 'Kegel':
                r_text = f"r: {info.get('r', '?')}"
                h_text = f"h: {info.get('h', '?')}"
                canvas.create_oval(50, 110, 170, 130, outline="black", width=2, fill="#ddddff")
                canvas.create_line(50, 120, 110, 30, outline="black", width=2)
                canvas.create_line(170, 120, 110, 30, outline="black", width=2)
                canvas.create_line(110, 120, 110, 30, fill="grey", dash=(2,2))
                canvas.create_text(40, 85, text=h_text, fill="black")
                canvas.create_text(110, 100, text=r_text, fill="black")

            canvas.pack(pady=10, padx=20)

        # --- 1. Algebra & Terme ---
        add_heading("Algebra & Terme")
        add_text("1. Binomische Formel: (a + b)² = a² + 2ab + b²")
        add_text("2. Binomische Formel: (a - b)² = a² - 2ab + b²")
        add_text("3. Binomische Formel: (a + b)(a - b) = a² - b²")

        add_text("\np-q-Formel (Lösung für x² + px + q = 0):")
        add_formula("x₁,₂ = -p/2 ± √((p/2)² - q)")

        add_text("\nabc-Formel / Mitternachtsformel (Lösung für ax² + bx + c = 0):")
        add_formula("x₁,₂ = [-b ± √(b² - 4ac)] / 2a")

        add_text("\nPolynomdivision (Satz vom Rest):")
        add_text("  •  Der Rest der Division P(x) : (x - a) ist gleich P(a).")

        # --- 2. Geometrie (2D) ---
        add_heading("Geometrie (2D)")
        add_text("Rechteck (l, w): U = 2(l + w) | A = l * w")
        add_sketch({'shape': 'Rechteck', 'l': 'l', 'w': 'w'})

        add_text("Kreis (r): U = 2 * Pi * r | A = Pi * r²")
        add_sketch({'shape': 'Kreis', 'r': 'r'})

        add_text("Dreieck (g, h): A = 0.5 * g * h")
        add_sketch({'shape': 'Dreieck', 'b': 'g', 'h': 'h'})

        add_text("Trapez (a, c, h): A = ((a + c) / 2) * h")
        add_sketch({'shape': 'Trapez', 'a': 'a', 'c': 'c', 'h': 'h'})

        # --- 3. Geometrie (3D) ---
        add_heading("Geometrie (3D)")
        add_text("Würfel (a): V = a³ | O = 6 * a²")
        add_sketch({'shape': 'Würfel', 'a': 'a'})

        add_text("Quader (l, b, h): V = l * b * h | O = 2(lb + lh + bh)")
        add_sketch({'shape': 'Quader', 'l': 'l', 'w': 'b', 'h': 'h'})

        add_text("Kugel (r): V = (4/3) * Pi * r³ | O = 4 * Pi * r²")
        add_sketch({'shape': 'Kugel', 'r': 'r'})

        add_text("Zylinder (r, h): V = Pi * r² * h | O = 2*Pi*r*h (Mantel) + 2*Pi*r² (Grundflächen)")
        add_sketch({'shape': 'Zylinder', 'r': 'r', 'h': 'h'})

        add_text("Kegel (r, h): V = (1/3) * Pi * r² * h | O = Pi*r² (Grund) + Pi*r*s (Mantel)")
        add_text(" (wobei s = √(r² + h²) die Seitenlinie ist) ")
        add_sketch({'shape': 'Kegel', 'r': 'r', 'h': 'h'})

        # --- 4. Statistik ---
        add_heading("Statistik")
        add_text("Mittelwert (Durchschnitt): (Summe aller Werte) / (Anzahl der Werte)")
        add_text("Median (Zentralwert): Der Wert in der Mitte der *sortierten* Datenreihe.")
        add_text("Modus (Modalwert): Der Wert, der am häufigsten vorkommt.")
        add_text("Spannweite: Größter Wert - Kleinster Wert")

        # --- 5. Stochastik ---
        add_heading("Stochastik")
        add_text("Laplace-Wahrscheinlichkeit P(E): |E| / |Ω|")
        add_text(" ( |E| = Günstige Ergebnisse, |Ω| = Alle Ergebnisse )")

        add_text("\nErwartungswert E(X) (Diskrete Verteilung):")
        add_formula("E(X) = x₁*P(X=x₁) + x₂*P(X=x₂) + ...")

        add_text("\nBinomialverteilung P(X=k) (n=Versuche, p=Treffer-P, k=Anzahl Treffer):")
        add_formula("P(X=k) = (n über k) * pᵏ * (1-p)ⁿ⁻ᵏ")


        # --- 6. Vektor-Berechnung ---
        add_heading("Vektor-Berechnung (v, w)")
        add_text("Addition: v + w = (v₁+w₁, v₂+w₂, v₃+w₃)")
        add_text("Betrag (Länge) |v|: √(v₁² + v₂² + v₃²)")
        add_text("Skalarprodukt v • w: v₁w₁ + v₂w₂ + v₃w₃ (Ergebnis ist eine Zahl!)")

        add_text("\nWinkel (α) zwischen Vektoren v und w:")
        add_formula("cos(α) = (v • w) / (|v| * |w|)")

        # --- Steuerelemente ---
        control_frame = tk.Frame(formula_frame, bg="#ecf0f1")
        control_frame.pack(pady=10)

        back_button = ttk.Button(control_frame, text="⬅️Zurück zum Hauptmenü",
                                 command=self.show_main_menu)
        back_button.pack(side=tk.LEFT, padx=10)
        ToolTip(back_button, "Zurück zum Hauptmenü.")

        self.root.focus_set()
    # --- ENDE FORMELMENÜ ---

    def show_main_menu(self):
        self.clear_screen()
        menu_frame = tk.Frame(self.root, bg="#ecf0f1")
        menu_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = menu_frame

        style = ttk.Style()
        style.configure('TButton', font=('Arial', 16), padding=10)
        style.configure('Big.TButton', font=('Arial', 24, 'bold'), padding=20)

        schuljahr_button_text = f"Aktuelle Klasse: {self.selected_schuljahr.get()}"
        schuljahr_button = ttk.Button(menu_frame,
                                      text=schuljahr_button_text,
                                      style='Big.TButton',
                                      name='schuljahr_button')
        schuljahr_button.place(relx=0.5, rely=0.20, anchor=tk.CENTER)
        ToolTip(schuljahr_button, "Zeigt die aktuell gewählte Lernklasse. Klicken, um die Klasse zu ändern.")

        self.schuljahr_dropdown = ttk.Combobox(menu_frame,
                                               textvariable=self.selected_schuljahr,
                                               values=self.schuljahr_options,
                                               font=('Arial', 14),
                                               state='readonly',
                                               justify=tk.CENTER)
        self.schuljahr_dropdown.place(relx=0.5, rely=0.30, anchor=tk.CENTER, width=350)
        ToolTip(self.schuljahr_dropdown, "Wählen Sie hier den aktuellen Lernstand von Klasse 1.1 bis 13.2.")

        def update_schuljahr_display(event):
            schuljahr_button.config(text=f"Aktuelle Klasse: {self.selected_schuljahr.get()}")

        self.schuljahr_dropdown.bind('<<ComboboxSelected>>', update_schuljahr_display)
        schuljahr_button.config(command=lambda: self.schuljahr_dropdown.focus_set())

        # --- MODIFIZIERTE button_info (MIT ALLEN NEUEN THEMEN) ---
        button_info = [
            # Themen (7)
            ("1. Zahlenraum-Training", "Addition/Subtraktion...", self.show_topic_submenu),
            ("2. Terme & Gleichungen", "Vereinfachen, Umstellen...", self.show_topic_submenu),
            ("3. Geometrie (2D/3D)", "Flächen, Umfang, Volumen...", self.show_topic_submenu),
            ("4. Statistik", "Mittelwert, Median...", self.show_topic_submenu),
            ("5. Stochastik", "Wahrscheinlichkeiten (Laplace)...", self.show_topic_submenu),
            ("6. Polynomdivision", "Satz vom Rest...", self.show_topic_submenu),
            ("7. Vektor-Berechnung", "Betrag, Skalarprodukt...", self.show_topic_submenu),

            # Steuerung (3)
            ("Formeln", "Zeigt eine Übersicht der wichtigsten Formeln.", self.handle_formula_menu),
            ("Lernfortschritt", "Zeigt gespeicherte Ergebnisse an.", self.handle_progress_menu),
            ("Halbjahrestest!", "Startet einen Test für das gewählte Halbjahr.", self.handle_semester_test)
        ]

        button_container = tk.Frame(menu_frame, bg="#ecf0f1")
        button_container.place(relx=0.5, rely=0.70, anchor=tk.CENTER)

        for i, (text, tooltip_text, handler) in enumerate(button_info):
            if handler == self.show_topic_submenu:

                button_text = text

                if "Geometrie" in text: topic_name = "Geometrie"
                elif "Zahlenraum" in text: topic_name = "Zahlenraum-Training"
                elif "Terme" in text: topic_name = "Terme & Gleichungen"
                elif "Statistik" in text: topic_name = "Statistik"
                elif "Stochastik" in text: topic_name = "Stochastik"
                elif "Polynomdivision" in text: topic_name = "Polynomdivision"
                elif "Vektor" in text: topic_name = "Vektor-Berechnung"
                else: topic_name = text

                command_func = lambda t=topic_name, f=menu_frame: self.show_topic_submenu(t, f)
            else:
                button_text = text
                command_func = handler

            button = ttk.Button(button_container, text=button_text, command=command_func)

            # Layout-Anpassung: 10 Buttons (4x3 Raster)
            button.grid(row=i // 3, column=i % 3, padx=15, pady=15, ipadx=20, ipady=10)
            ToolTip(button, tooltip_text)

        exit_button = ttk.Button(menu_frame, text="✖Beenden",
                                 command=self.root.quit,
                                 style='TButton')
        exit_button.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-20, y=20)
        ToolTip(exit_button, "Beendet die Anwendung.")

        self.root.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatheGenieApp(root)
    root.mainloop()