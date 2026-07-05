import streamlit as st
import json
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

st.set_page_config(page_title="Outil de Création de Contenu Viral (Quiz)", layout="wide")

# ----------------------------------------------------------------------
# SESSION STATE INIT
# ----------------------------------------------------------------------
if "quiz_name" not in st.session_state:
    st.session_state.quiz_name = "Le Grand Quiz"
if "footer_text" not in st.session_state:
    st.session_state.footer_text = "Généré par l'Expert TikTok Quiz Creator."
if "theme_color" not in st.session_state:
    st.session_state.theme_color = "#5772BC"
if "questions" not in st.session_state:
    st.session_state.questions = [
        {"question": "Quelle est la capitale de la France ?",
         "options": ["Paris", "Lyon", "Marseille"],
         "correct": 0}
    ]

# ----------------------------------------------------------------------
# PDF GENERATION
# ----------------------------------------------------------------------
def generate_pdf(quiz_name, footer_text, theme_color, questions):
    """Builds an A4 quiz sheet PDF and returns it as bytes."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 20 * mm
    usable_width = width - 2 * margin_x
    color = HexColor(theme_color)

    y = height - 25 * mm

    # Title
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, y, quiz_name if quiz_name else "Quiz")
    y -= 6 * mm

    # Divider line under title
    c.setStrokeColor(color)
    c.setLineWidth(1)
    c.line(margin_x, y, width - margin_x, y)
    y -= 12 * mm

    def wrap_text(text, font_name, font_size, max_width):
        """Simple word-wrap that returns a list of lines fitting max_width."""
        words = text.split()
        lines = []
        current = ""
        for w in words:
            trial = (current + " " + w).strip()
            if stringWidth(trial, font_name, font_size) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines if lines else [""]

    letters = ["A", "B", "C", "D", "E", "F"]

    for idx, q in enumerate(questions, start=1):
        # Page break if not enough room
        if y < 35 * mm:
            c.showPage()
            y = height - 25 * mm

        # Question number + text
        c.setFillColor(HexColor("#000000"))
        num_str = f"{idx:02d})"
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(color)
        c.drawString(margin_x, y, num_str)

        q_text = q.get("question", "")
        c.setFillColor(HexColor("#000000"))
        c.setFont("Helvetica-Bold", 11)
        text_x = margin_x + 12 * mm
        max_w = usable_width - 12 * mm
        lines = wrap_text(q_text, "Helvetica-Bold", 11, max_w)
        for i, line in enumerate(lines):
            c.drawString(text_x, y - (i * 5 * mm), line)
        y -= (len(lines) - 1) * 5 * mm
        y -= 7 * mm

        # Options
        c.setFont("Helvetica", 10)
        options = q.get("options", [])
        for opt_idx, opt in enumerate(options):
            letter = letters[opt_idx] if opt_idx < len(letters) else str(opt_idx + 1)
            opt_text = f"{letter}) {opt}"
            opt_lines = wrap_text(opt_text, "Helvetica", 10, max_w - 5 * mm)
            for i, line in enumerate(opt_lines):
                c.drawString(text_x + 5 * mm, y - (i * 4.5 * mm), line)
            y -= (len(opt_lines) - 1) * 4.5 * mm
            y -= 5.5 * mm

        y -= 5 * mm  # space between questions

    # Footer on every page (redraw on last page; simple approach: draw on each page as it's created)
    # For simplicity here, footer only guaranteed on the last page.
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(HexColor("#666666"))
    c.drawCentredString(width / 2, 12 * mm, footer_text if footer_text else "")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def import_json(uploaded_file):
    """Parses an uploaded JSON quiz file. Returns (quiz_name, questions, error)."""
    try:
        raw = uploaded_file.read()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, None, f"Fichier JSON invalide : {e}"
    except Exception as e:
        return None, None, f"Erreur de lecture du fichier : {e}"

    if not isinstance(data, dict):
        return None, None, "Le JSON doit être un objet avec les clés 'themeName' et 'questions'."

    theme_name = data.get("themeName", "Quiz")
    questions_raw = data.get("questions")

    if not isinstance(questions_raw, list) or len(questions_raw) == 0:
        return None, None, "La clé 'questions' est manquante, vide, ou n'est pas une liste."

    parsed_questions = []
    for i, q in enumerate(questions_raw):
        if not isinstance(q, dict):
            return None, None, f"La question #{i+1} n'est pas un objet valide."
        q_text = q.get("question")
        options = q.get("options")
        if not q_text or not isinstance(options, list) or len(options) < 2:
            return None, None, (
                f"La question #{i+1} est incomplète "
                "(il faut 'question' et au moins 2 'options')."
            )
        parsed_questions.append({
            "question": q_text,
            "options": options,
            "correct": 0  # default; user can adjust manually after import
        })

    return theme_name, parsed_questions, None


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.title("✨ Outil de Création de Contenu Viral (Quiz)")

tab1, tab2 = st.tabs(["🖨️ Générateur de Quiz PDF", "🧠 Prompt d'Expert TikTok"])

# ========================================================================
# TAB 1 : PDF GENERATOR
# ========================================================================
with tab1:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Configuration du PDF (Styling)")

        st.session_state.quiz_name = st.text_input(
            "Nom d'affichage du Quiz PDF (ex: Le Grand Quiz)",
            value=st.session_state.quiz_name
        )
        st.session_state.theme_color = st.color_picker(
            "Couleur du thème", value=st.session_state.theme_color
        )
        st.session_state.footer_text = st.text_input(
            "Texte personnalisé du pied de page PDF",
            value=st.session_state.footer_text
        )

        st.subheader("2. Importer un Quiz JSON")
        uploaded = st.file_uploader("Importer Quiz JSON", type=["json"])
        if uploaded is not None:
            if st.button("📥 Charger ce fichier JSON"):
                theme_name, parsed_questions, error = import_json(uploaded)
                if error:
                    st.error(error)
                else:
                    st.session_state.quiz_name = theme_name
                    st.session_state.questions = parsed_questions
                    st.success("PDF généré et aperçu mis à jour avec succès.")
                    st.rerun()

        with st.expander("Structure du fichier JSON à importer"):
            st.code(json.dumps({
                "themeName": "Corps humain",
                "questions": [
                    {
                        "question": "Quel organe continue de fonctionner quelques secondes après ta mort ?",
                        "options": ["Le cœur", "Le cerveau", "Les poumons"]
                    }
                ]
            }, indent=2, ensure_ascii=False), language="json")

        st.subheader("3. Saisie des Questions (Pour le PDF)")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("➕ Ajouter une Question"):
                st.session_state.questions.append({
                    "question": "Nouvelle question ?",
                    "options": ["Réponse A", "Réponse B", "Réponse C"],
                    "correct": 0
                })
                st.rerun()
        with col_b:
            if st.button("🗑️ Supprimer la Dernière"):
                if len(st.session_state.questions) > 1:
                    st.session_state.questions.pop()
                    st.rerun()

        for idx, q in enumerate(st.session_state.questions):
            with st.expander(f"Question {idx + 1}: {q['question'][:40]}", expanded=False):
                q["question"] = st.text_area(
                    f"Texte de la question {idx + 1}",
                    value=q["question"],
                    key=f"q_text_{idx}"
                )
                new_options = []
                for opt_idx, opt in enumerate(q["options"]):
                    letter = ["A", "B", "C", "D", "E", "F"][opt_idx] if opt_idx < 6 else str(opt_idx + 1)
                    val = st.text_input(
                        f"Réponse {letter}",
                        value=opt,
                        key=f"q_{idx}_opt_{opt_idx}"
                    )
                    new_options.append(val)
                q["options"] = new_options

                if q["options"]:
                    letters_for_options = ["A", "B", "C", "D", "E", "F"][:len(q["options"])]
                    correct_idx = st.radio(
                        "Bonne réponse",
                        options=list(range(len(q["options"]))),
                        format_func=lambda i: letters_for_options[i],
                        index=min(q.get("correct", 0), len(q["options"]) - 1),
                        key=f"q_{idx}_correct",
                        horizontal=True
                    )
                    q["correct"] = correct_idx

    with col_right:
        st.subheader("Aperçu du PDF A4 (Format réel)")

        pdf_bytes = generate_pdf(
            st.session_state.quiz_name,
            st.session_state.footer_text,
            st.session_state.theme_color,
            st.session_state.questions
        )

        try:
            # Native PDF preview (Streamlit >= 1.41)
            st.pdf(pdf_bytes)
        except Exception:
            # Fallback for older Streamlit versions: base64 iframe embed
            import base64
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            st.markdown(
                f"""
                <div style="border:1px solid #ddd; padding:10px; background:#f9f9f9;">
                    <iframe src="data:application/pdf;base64,{b64}"
                            width="100%" height="700"></iframe>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.download_button(
            label=f"⬇️ Télécharger le PDF ({st.session_state.quiz_name or 'Quiz'})",
            data=pdf_bytes,
            file_name=f"{(st.session_state.quiz_name or 'quiz').replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

# ========================================================================
# TAB 2 : PROMPT EXPERT
# ========================================================================
with tab2:
    st.subheader("🎭 Configuration Dynamique du Prompt IA")

    col1, col2 = st.columns(2)
    with col1:
        theme = st.text_input("Thème spécifique du quiz IA", value="Corps humain")
    with col2:
        difficulte = st.selectbox("Niveau de difficulté", ["Facile", "Moyen", "Difficile"])

    col3, col4 = st.columns(2)
    with col3:
        nb_questions = st.number_input("Nombre de questions (max 10)", min_value=1, max_value=10, value=5)
    with col4:
        nb_reponses = st.number_input("Nombre de réponses proposées (min 2, max 6)", min_value=2, max_value=6, value=3)

    lettres_dispo = ["A", "B", "C", "D", "E", "F"][:nb_reponses]
    lettres_str = ", ".join(lettres_dispo)

    prompt_template = f"""Rôle : Expert en Quizzes Viraux TikTok
Tu es un expert en création de contenu TikTok spécialisé dans les quizzes viraux et en prompt engineering. Tu génères une série de {nb_questions} questions sur le thème "{theme}", avec un niveau de difficulté {difficulte}. Ton objectif principal est de créer un quiz optimisé pour maximiser les vues, la rétention et les commentaires.

RÈGLES DE CRÉATION DU QUIZ

1. Structure du quiz
- 1 thème global par quiz (défini par l'utilisateur : "{theme}").
- {nb_questions} questions :
  - Q1 = HOOK très fort (surprenante, provocante, intrigante, qui incite à rester).
  - Q2-Q{nb_questions} = questions équilibrées dont 1 à 2 subtilement ambiguës pour générer des commentaires et débats (mais sans être fausses ni borderline).

2. Style attendu
- Formulations courtes, directes, adaptées à TikTok.
- Alternance entre questions étonnantes, questions faciles pour flatter le joueur, questions ambiguës pour créer du débat, questions fun/visuelles/insolites.
- Le niveau de difficulté doit correspondre à {difficulte}.
- Jamais de contenu sensible, politique, violent, médical ou inapproprié.

3. Réponses
- Proposer {nb_reponses} options ({lettres_str}) pour chaque question.
- Indiquer la bonne réponse clairement dans la colonne dédiée.

4. Sortie attendue (obligatoire)
Tu dois générer DEUX sorties, l'une à la suite de l'autre, sans aucun texte intermédiaire :

A. Un tableau au format Markdown strict (avec {nb_reponses} colonnes de réponses) :
Thème | Question | {" | ".join([f"Réponse {l}" for l in lettres_dispo])} | Bonne réponse
---|---|{"|".join(["---"] * nb_reponses)}|---
...

B. Un fichier JSON téléchargeable (Format exact) :
{{
  "themeName": "Nom du quiz",
  "questions": [
    {{
      "question": "Texte de la question 1",
      "options": [{", ".join([f'"Réponse {l}"' for l in lettres_dispo])}]
    }}
  ]
}}

TA TÂCHE : Génère un quiz complet conforme aux règles ci-dessus. Assure-toi que la première question est extrêmement accrocheuse, qu'une ou deux questions sont subtilement ambiguës, que tout le contenu est vrai, clair et engageant, et que le JSON correspond exactement au tableau."""

    st.text_area("Prompt généré", value=prompt_template, height=500)
    st.caption("💡 Copiez ce texte (Ctrl+A puis Ctrl+C dans la zone ci-dessus) et collez-le dans ChatGPT ou Claude, puis récupérez le JSON généré pour l'importer dans l'onglet 'Générateur de Quiz PDF'.")
