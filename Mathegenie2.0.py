# ==============================================================================
# PROJEKT: Mathegenie - Adaptiver Mathetrainer
# AUTOR:   Rainer Liegard
# DATUM:   07. November 2025
# VERSION: 2.0 (Persistenz von Benutzereinstellungen und Konfiguration)
# ==============================================================================
#
# Eine Tkinter-Anwendung zur Durchführung und Aufzeichnung von Mathematikübungen.
# Diese Version fügt eine grundlegende Konfigurationsspeicherung hinzu, um die
# Anwendung konsistenter für den Benutzer zu gestalten.
#
# Haupt-Features der Version 3.2:
# 1. **Einstellungen persistent speichern:** Die zuletzt ausgewählte Klasse
#    (`selected_schuljahr`) und andere UI-Einstellungen (z.B. der Fullscreen-Status
#    oder ein gewähltes Theme, falls implementiert) werden nun beim Beenden
#    gespeichert.
# 2. **Laden der Einstellungen:** Beim Start der Anwendung werden die gespeicherten
#    Einstellungen geladen, sodass die App mit dem Zustand der letzten Sitzung
#    beginnt. Dies erhöht die Benutzerfreundlichkeit (Usability).
# 3. **Konfigurationsdatei:** Implementierung einer einfachen Methode zur
#    Speicherung der Konfiguration, z.B. mithilfe des `configparser`-Moduls
#    oder einer JSON-Datei.
# 4. **Stabile Basis:** Die modulare Lehrplan-Steuerung (V3.0/3.1) und alle
#    vorherigen Features bleiben funktionsfähig.
#
# Abhängigkeiten & Voraussetzungen:
# - Python 3.x
# - Tkinter (Standard in Python)
# - sqlite3 (Standard in Python)
# - configparser / json (für Einstellungen)
#
################################################################################
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import random
from datetime import datetime
import time
import operator
import re # Import für RegEx (genutzt in _generate_terme)

# NEU: Helper-Funktion zur Formatierung von Zahlen im deutschen Format
def format_german(number):
    """Formatiert eine Zahl (int/float) ins deutsche Format (z.B. 1.453.557,0)"""
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

    sign = ''
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
            title_text = "✅ Richtig!"
            title_color = "#28a745"
        else:
            title_text = "❌ Leider falsch!"
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

    def _draw_sketch(self, info):
        """Zeichnet die Geometrie- oder Statistik-Skizze auf ein Canvas."""
        canvas = tk.Canvas(self, width=220, height=150, bg="white", highlightthickness=1, highlightbackground="black")

        shape = info.get('shape')

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

        # MODIFIZIERT: Skizze für Statistik
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

            # X-Achse (unten)
            canvas.create_line(padding, canvas_height - padding, canvas_width - padding, canvas_height - padding)

            bar_width = (canvas_width - 2 * padding) / len(data)
            bar_spacing = 2

            # Skalierung für Y-Achse
            max_bar_height = canvas_height - 2 * padding - 10 # 10px Puffer oben

            for i, val in enumerate(data):
                x0 = padding + i * bar_width + bar_spacing
                x1 = padding + (i + 1) * bar_width - bar_spacing

                bar_height = (val / max_val) * max_bar_height
                y0 = canvas_height - padding - bar_height
                y1 = canvas_height - padding

                canvas.create_rectangle(x0, y0, x1, y1, fill="#4a90e2", outline="black")
                # Text (Wert) über dem Balken
                canvas.create_text((x0 + x1) / 2, y0 - 8, text=str(val), font=("Arial", 10))

        else:
            canvas.create_text(110, 75, text="Keine Skizze verfügbar.")

        canvas.pack(pady=10, padx=20)


#=========================
#--- DATENBANK-VERWALTUNG
#=========================
class DatabaseManager:
    # ... (Keine Änderungen in dieser Klasse) ...
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
        """Bearbeitet ein Ergebnis anhand der ID (wird im Ul simuliert)."""
        self.cursor.execute("""
   UPDATE results SET correct_count=?, total_count=?, duration=?
   WHERE id=?
  """, (new_correct, new_total, new_duration, result_id))
        self.conn.commit()

#=================================================================================
#--- AUFGABEN-ALGORITHMEN
#=================================================================================
class AufgabenGenerator:
    # ... (Init, _parse_class, _get_params bleiben gleich) ...
    """Erstellt mathematische Aufgaben und deren Lösungen basierend auf Thema und Schwierigkeit."""
    def __init__(self, topic, difficulty, class_name, num_questions=10):
        self.topic = topic
        self.difficulty = difficulty
        self.class_name = class_name
        self.num_questions = num_questions
        self.questions = []
        self._generate_questions()
    def _parse_class(self):
        """Extrahiert Jahr und Halbjahr aus dem Klassennamen (z. B. 'Klasse 5.2' -> 5, 2). """
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
        """Definiert Zahlenbereiche, Operatoren und Komplexität basierend auf Klasse, Thema und Schwierigkeit."""
        year, semester = self._parse_class()
        #1. Basis-Parameter basierend auf Schuljahr
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
        #2. Anpassung basierend auf Thema
        if self.topic == "Terme & Gleichungen" or self.topic == "Geometrie" or self.topic == "Statistik":
            # MODIFIZIERT: Niedrigere Werte (max 50) für diese Themen
            params['range'] = (1, min(50, max_val))
        if year >= 7:
            params['allow_negatives'] = True
        if year >= 5:
            params['decimals'] = 1
        #3. Feintuning basierend auf Schwierigkeit (Leicht = Wiederholung, Schwer = Anwendung)
        if self.difficulty == "Leicht":
            params['range'] = (1, int(max_val * 0.4)) # Kleinerer Zahlenraum
            params['max_terms'] = 2
            params['decimals'] = 0
            params['allow_negatives'] = False
        elif self.difficulty == "Mittel":
            params['range'] = (1, max_val) # Normaler Zahlenraum
            params['max_terms'] = 3
            if year >= 5 and self.topic != "Zahlenraum-Training":
                params['decimals'] = 1
        elif self.difficulty == "Schwer":
            params['range'] = (max(1, max_val // 10), max_val) # Höherwertige Zahlen im Fokus
            params['max_terms'] = 4
            if year >= 5:
                params['decimals'] = 2
            if year >= 7:
                params['allow_negatives'] = True
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

            # MODIFIZIERT: Statistik gibt jetzt auch drawing_info zurück
            elif self.topic == "Statistik":
                q, a, steps, drawing_info = self._generate_statistik()

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

    #--- Themen-Algorithmen (MODIFIZIERT)
    def _generate_zahlenraum(self):
        """Erstellt arithmetische Aufgaben. Gibt (q, a, steps) zurück."""
        # ... (Keine Änderungen in dieser Funktion, gibt 3 Werte zurück) ...
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
            answer = random.randint(safe_lower, safe_upper)
            divisor = random.randint(2, 9)
            num1 = answer * divisor
            question = f"{num1} {op} {divisor} ="
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"1. Schritt: Führe die {op_name_map[op]} aus.\n"
                f" {num1}/{divisor} = {answer}\n"
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
        """Erstellt Aufgaben zum Vereinfachen von Termen. Gibt (q, a, steps) zurück."""
        # ... (Keine Änderungen in dieser Funktion, gibt 3 Werte zurück) ...
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
        term_str = " ".join([p if p.startswith('-') else f"+ {p}" for i, p in enumerate(term_parts)]).replace("+ -", "- ")
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

    def _generate_geometrie(self):
        """Erstellt geometrische Aufgaben. Gibt (q, a, steps, drawing_info) zurück."""
        # ... (Keine Änderungen in dieser Funktion, gibt 4 Werte zurück) ...
        params = self._get_params()
        shape = random.choice(['Rechteck', 'Kreis', 'Dreieck'])
        unit = "cm"
        max_dim = max(1, params['range'][1])

        question, answer, steps = "", 0, ""
        drawing_info = None

        if shape == 'Rechteck':
            length = random.randint(1, max_dim)
            width = random.randint(1, length)
            drawing_info = {'shape': 'Rechteck', 'l': length, 'w': width}
            q_type = random.choice(['Umfang', 'Fläche'])
            if q_type == 'Umfang':
                question = f"Berechne den Umfang eines Rechtecks mit Länge {length}{unit} und Breite {width}{unit}."
                answer = 2* (length + width)
                steps = (
                    f"**Aufgabe:** {question}\n\n"
                    f"1. Schritt: Formel für Rechteckumfang (U) notieren.\n"
                    f" - U = 2 * (Länge + Breite)\n"
                    f"2. Schritt: Werte einsetzen.\n"
                    f" - U = 2 * ({length} + {width})\n"
                    f"3. Schritt: Klammer berechnen.\n"
                    f" - U = 2 * ({length + width})\n"
                    f"4. Schritt: Multiplizieren.\n"
                    f" - U = {answer}\n\n"
                    f"**Ergebnis:** {answer} {unit}"
                )
            else: # Fläche
                question = f"Berechne die Fläche eines Rechtecks mit Länge {length}{unit} und Breite {width}{unit}."
                answer = length * width
                steps = (
                    f"**Aufgabe:** {question}\n\n"
                    f"1. Schritt: Formel für Rechteckfläche (A) notieren.\n"
                    f" - A = Länge * Breite\n"
                    f"2. Schritt: Werte einsetzen.\n"
                    f" - A = {length} * {width}\n"
                    f"3. Schritt: Multiplizieren.\n"
                    f" - A = {answer}\n\n"
                    f"**Ergebnis:** {answer} {unit}²"
                )
        elif shape == 'Kreis':
            radius = random.randint(1, max(2, max_dim // 5))
            drawing_info = {'shape': 'Kreis', 'r': radius}
            q_type = random.choice(['Umfang', 'Fläche'])
            pi_val = 3.14159
            if q_type == 'Umfang':
                question = f"Berechne den Umfang eines Kreises mit Radius {radius}{unit}. Runde auf {params['decimals']} Nachkommastellen (Nutze Pi={pi_val:.4f})."
                answer = 2 * pi_val * radius
                steps = (
                    f"**Aufgabe:** {question}\n\n"
                    f"1. Schritt: Formel für Kreisumfang (U) notieren.\n"
                    f" - U = 2 * Pi * r\n"
                    f"2. Schritt: Werte einsetzen.\n"
                    f" - U = 2 * {pi_val:.4f} * {radius}\n"
                    f"3. Schritt: Multiplizieren.\n"
                    f" - U = {answer}\n\n"
                    f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}"
                )
            else: # Fläche
                question = f"Berechne die Fläche eines Kreises mit Radius {radius}{unit}. Runde auf {params['decimals']} Nachkommastellen (Nutze Pi={pi_val:.4f})."
                answer = pi_val * (radius ** 2)
                steps = (
                    f"**Aufgabe:** {question}\n\n"
                    f"1. Schritt: Formel für Kreisfläche (A) notieren.\n"
                    f" - A = Pi * r²\n"
                    f"2. Schritt: Werte einsetzen.\n"
                    f" - A = {pi_val:.4f} * {radius}²\n"
                    f"3. Schritt: Potenz berechnen.\n"
                    f" - A = {pi_val:.4f} * {radius**2}\n"
                    f"4. Schritt: Multiplizieren.\n"
                    f" - A = {answer}\n\n"
                    f"**Ergebnis (gerundet):** {round(answer, params['decimals'])} {unit}²"
                )
            return question, round(answer, params['decimals']), steps, drawing_info

        else: # Dreieck (Fläche)
            base = random.randint(1, max_dim)
            height = random.randint(1, max(2, base))
            drawing_info = {'shape': 'Dreieck', 'b': base, 'h': height}
            question = f"Berechne die Fläche eines Dreiecks mit Grundseite {base}{unit} und Höhe {height}{unit}."
            answer = 0.5 * base * height
            steps = (
                f"**Aufgabe:** {question}\n\n"
                f"1. Schritt: Formel für Dreiecksfläche (A) notieren.\n"
                f" - A = 0.5 * Grundseite * Höhe\n"
                f"2. Schritt: Werte einsetzen.\n"
                f" - A = 0.5 * {base} * {height}\n"
                f"3. Schritt: Multiplizieren.\n"
                f" - A = {answer}\n\n"
                f"**Ergebnis:** {answer} {unit}²"
            )
        return question, round(answer, params['decimals']), steps, drawing_info

    def _generate_statistik(self):
        """Erstellt statistische Aufgaben. Gibt (q, a, steps, drawing_info) zurück."""
        params = self._get_params()
        data_size = random.randint(5, 10)
        max_data_val = max(1, max(5, params['range'][1] // 2))
        data = [random.randint(1, max_data_val) for _ in range(data_size)]

        # MODIFIZIERT: Skizzen-Daten erstellen
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
            # MODIFIZIERT: 4 Werte zurückgeben
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
            # MODIFIZIERT: 4 Werte zurückgeben
            return question, answer, steps, drawing_info

#=================================================================================

#--- ÜBUNGSSESSION KLASSE ---------------------------------------------------------
#=================================================================================

class AufgabenSession:
    # ... (Keine Änderungen in __init__, _get_time_limit, _create_session_window, ...)
    # ... (_cancel_session, _start_timer, _update_timer_label, _countdown, _update_question) ...

    """Verwaltet das Tkinter-Fenster für eine Übungssitzung."""
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
        """Liefert das Zeitlimit in Sekunden (Simulation der Komplexität)."""
        if difficulty == "Leicht":
            return 600
        elif difficulty == "Mittel":
            return 900
        else:
            return 1200

    def _create_session_window(self):
        """Erstellt das Übungsfenster (Toplevel)."""
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
        self._update_timer_label()
        self._countdown()

    def _update_timer_label(self):
        """Aktualisiert das Timer-Label im Format MM:SS."""
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.config(text=f"Verbleibende Zeit: {minutes:02d}:{seconds:02d}")

    def _countdown(self):
        """Aktualisiert den Timer jede Sekunde."""
        if self.time_left > 0:
            self.time_left -= 1
            self._update_timer_label()
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
            self.next_button.config(text="Antwort prüfen & Weiter >>")

        self.answer_entry.focus_set()

    #--- CHECK_ANSWER METHODE (nutzt FeedbackDialog) ---
    def _check_answer(self, event=None):
        """Prüft die Antwort des Benutzers, gibt Feedback und geht zur nächsten Frage."""
        if self.current_question_index >= self.num_questions:
            self._finish_session()
            return

        user_input = self.answer_entry.get().strip()
        cleaned_input = user_input.replace('.', '').replace(',', '.')

        q_data = self.generator.questions[self.current_question_index]

        # 1. Eingabe verarbeiten
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

        # 2. Antwort prüfen
        correct_answer = q_data['correct_answer']
        solution_steps = q_data.get('solution_steps', "Kein detaillierter Lösungsweg verfügbar.")
        is_correct = False

        if isinstance(user_answer, (int, float)) and abs(user_answer - correct_answer) < 0.1:
            is_correct = True

        # 3. Feedback anzeigen (Nutzt FeedbackDialog)
        drawing_info = q_data.get('drawing_info') # Holt die Skizzen-Daten

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

        # 4. Zur nächsten Frage wechseln
        self.current_question_index += 1

        if self.current_question_index == self.num_questions:
            self._finish_session()
        else:
            self._update_question()

    def _finish_session(self, timeout=False):
        # ... (Keine Änderungen in dieser Funktion) ...
        """Beendet die Übung, wertet aus und speichert in der DB."""
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

        result_msg = "⏱️ Übungszeit abgelaufen!" if timeout else "✅ Übung beendet!"
        result_msg += (f"\n\nKlasse: {self.class_name}\n"
                       f"Thema: {full_topic}\n"
                       f"Richtige Antworten: {correct_count} von {total_count}\n"
                       f"Genutzte Zeit: {elapsed_time:.1f}s / {self.time_limit}s\n"
                       f"Ergebnis in Datenbank gespeichert.")

        messagebox.showinfo("Übungsergebnis", result_msg)
        self.window.destroy()
        self.parent_app.show_main_menu()

#=================================================================================

#--- HAUPTANWENDUNG ---------------------------------------------------------------
#=================================================================================

class MatheGenieApp:
    # ... (Keine Änderungen in dieser Klasse) ...
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

    def _get_min_class(self, topic):
        """Definiert das Mindest-Semester (Gesamtsemester-Index) für ein Thema."""
        mapping = {
            "Zahlenraum-Training": 1,
            "Terme & Gleichungen": 9,
            "Geometrie": 9,
            "Statistik": 13,
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

    # --- Untermenü und Hauptmenü ---

    def show_topic_submenu(self, topic, menu_frame):
        # 1. PRÜFUNG: Ist das Thema für die aktuelle Klasse freigegeben?
        _, _, current_total_semester = self._parse_selected_class()
        min_total_semester = self._get_min_class(topic)
        if current_total_semester < min_total_semester:
            year = (min_total_semester - 1) // 2 + 1
            semester = (min_total_semester - 1) % 2 + 1

            self._show_toast_message(f"🚫 Thema '{topic}' ist erst ab Klasse {year}.{semester} verfügbar!")
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
            ("Leicht", "Wiederholung der Grundlagen...", "#D4EDDA", 'Leicht'),
            ("Mittel", "Standardaufgaben im vollen Zahlenraum...", "#FFF3CD", 'Mittel'),
            ("Schwer", "Anwendungsaufgaben und Transfer...", "#F8D7DA", 'Schwer')
        ]

        for i, (level_text, tooltip_text, color, level) in enumerate(difficulties):
            button_style = f'{level}.TButton'
            style.configure(button_style, font=('Arial', 20, 'bold'), padding=20, background=color)

            command_func = lambda t=topic, d=level: self.start_practice_session(t, d)

            button = ttk.Button(button_container, text=level_text, command=command_func, style=button_style)
            button.grid(row=0, column=i, padx=30, ipadx=50, ipady=30)

            ToolTip(button, tooltip_text)

        back_button = ttk.Button(submenu_frame, text="⬅️ Zurück zum Hauptmenü",
                                 command=self.show_main_menu)
        back_button.pack(pady=50)
        ToolTip(back_button, "Kehrt zum Hauptmenü zurück.")

        self.root.focus_set()

    def show_progress_menu(self, event=None):
        """Erstellt und zeigt die Ansicht mit dem Lernfortschritt."""
        self.clear_screen()

        progress_frame = tk.Frame(self.root, bg="#ecf0f1")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = progress_frame

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

        delete_button = ttk.Button(control_frame, text="🗑️ Ergebnis löschen",
                                   command=self.delete_selected_result)
        delete_button.pack(side=tk.LEFT, padx=10)
        ToolTip(delete_button, "Löscht das ausgewählte Ergebnis aus der Datenbank.")

        edit_button = ttk.Button(control_frame, text="🔄 Bearbeiten (Simuliert)",
                                 command=self.simulate_edit_result)
        edit_button.pack(side=tk.LEFT, padx=10)
        ToolTip(edit_button, "Simuliert eine manuelle Korrektur des Ergebnisses.")

        back_button = ttk.Button(control_frame, text="⬅️ Zurück zum Hauptmenü",
                                 command=self.show_main_menu)
        back_button.pack(side=tk.LEFT, padx=10)
        ToolTip(back_button, "Zurück zum Hauptmenü.")

        self.root.focus_set()
    def load_results_to_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        results = self.db.get_all_results()
        for row in results:
            display_row = list(row)
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

        new_correct = int(old_values[3]) + 1
        new_total = int(old_values[4])
        new_duration = float(old_values[5]) * 0.9

        if new_correct > new_total: new_correct = new_total

        self.db.update_result(result_id, new_correct, new_total, new_duration)
        self.load_results_to_tree()
        messagebox.showinfo("Bearbeitet", f"Ergebnis ID {result_id} wurde simuliert bearbeitet.")

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

        button_info = [
            ("1. Zahlenraum-Training", "Addition/Subtraktion/Multiplikation/Division...", self.show_topic_submenu),
            ("2. Terme & Gleichungen", "Vereinfachen, Umstellen und Auflösen...", self.show_topic_submenu),
            ("3. Geometrie", "Flächen, Umfang, Volumen...", self.show_topic_submenu),
            ("4. Statistik", "Häufigkeit, Wahrscheinlichkeit...", self.show_topic_submenu),
            ("Lernfortschritt", "Zeigt gespeicherte Ergebnisse an.", self.handle_progress_menu)
        ]

        button_container = tk.Frame(menu_frame, bg="#ecf0f1")
        button_container.place(relx=0.5, rely=0.70, anchor=tk.CENTER)

        for i, (text, tooltip_text, handler) in enumerate(button_info):
            if handler == self.show_topic_submenu:
                topic_name = text.split('.', 1)[1].strip()
                command_func = lambda t=topic_name, f=menu_frame: self.show_topic_submenu(t, f)
            else:
                command_func = handler

            button = ttk.Button(button_container, text=text, command=command_func)
            button.grid(row=i // 2, column=i % 2, padx=20, pady=15, ipadx=20, ipady=10)
            ToolTip(button, tooltip_text)

        exit_button = ttk.Button(menu_frame, text="✖ Beenden",
                                 command=self.root.quit,
                                 style='TButton')
        exit_button.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-20, y=20)
        ToolTip(exit_button, "Beendet die Anwendung.")

        self.root.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatheGenieApp(root)
    root.mainloop()