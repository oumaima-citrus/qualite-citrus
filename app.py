import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from datetime import date
from fpdf import FPDF
import streamlit as st
st.set_page_config(
    page_title="Application Qualité Citrus",
    page_icon="🍊",
    layout="wide"
)
st.markdown("""
<style>
/* الخلفية */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f7fff4 0%, #ffffff 45%, #fff7ed 100%);
}

/* العنوان */
h1 {
    color: #1f2937;
    font-weight: 800;
    text-align: center;
}

/* العناوين الصغيرة */
h2, h3 {
    color: #374151;
    font-weight: 700;
}

/* الكروت */
.block-container {
    padding-top: 2rem;
    max-width: 1050px;
}

/* الأزرار */
.stButton > button {
    border-radius: 16px;
    height: 52px;
    font-weight: 700;
    border: 1px solid #e5e7eb;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    transition: 0.2s;
}

.stButton > button:hover {
    transform: translateY(-2px);
    border-color: #f97316;
    color: #f97316;
}

/* زر التحميل PDF */
.stDownloadButton > button {
    border-radius: 16px;
    height: 52px;
    font-weight: 700;
    background: #f97316;
    color: white;
    border: none;
    box-shadow: 0 4px 12px rgba(249,115,22,0.25);
}

/* input */
.stTextInput input, .stNumberInput input, .stDateInput input {
    border-radius: 12px;
}

/* metrics */
[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
}

/* tables */
[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
}

/* separators */
hr {
    margin-top: 25px;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)

DB_FILE = "citrus_mogador.db"
CAMPAGNE_AUTO = "2026/2027"


# ---------------- DATABASE ----------------
# ---------------- DATABASE ----------------
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compte TEXT NOT NULL,
            date_controle TEXT NOT NULL,
            numero_lot TEXT NOT NULL,
            variete TEXT NOT NULL,
            producteur TEXT,
            ferme TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS controles_produit_fini (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            matricule TEXT NOT NULL,
            calibre TEXT NOT NULL,
            total_fruits INTEGER NOT NULL,
            defauts INTEGER NOT NULL,
            conformes INTEGER NOT NULL,
            taux_conforme REAL NOT NULL,
            taux_non_conforme REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lot_id) REFERENCES lots(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS controles_ecarts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            matricule TEXT NOT NULL,
            calibre TEXT NOT NULL,
            total_fruits INTEGER NOT NULL,
            fruits_conformes INTEGER NOT NULL,
            ecarts INTEGER NOT NULL,
            taux_conforme REAL NOT NULL,
            taux_non_conforme REAL NOT NULL,
            verification TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lot_id) REFERENCES lots(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS details_defauts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            controle_ecart_id INTEGER NOT NULL,
            type_defaut TEXT NOT NULL,
            quantite INTEGER NOT NULL,
            pourcentage REAL NOT NULL,
            FOREIGN KEY (controle_ecart_id) REFERENCES controles_ecarts(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS types_defauts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    """)

    default_defauts = [
        "Défaut de coloration (vert)",
        "Marbrures",
        "Blessures",
        "Blessures de pédoncule",
        "Pédoncule long",
        "Affaissement de cellule",
        "Frottement",
        "Coup de soleil",
        "Dégâts escargots",
        "Dégâts de grêle",
        "Fruit écrasé",
        "Fruit brûlé",
        "Fruit attaché",
        "Blessures écorce",
        "Pédoncule pourri",
        "Acariens",
        "Fruit déformé",
        "Fruit mou",
        "Alternaria",
        "Éclatement",
        "Fruit vert",
        "Déformé"
    ]

    for d in default_defauts:
        cur.execute("INSERT OR IGNORE INTO types_defauts (nom) VALUES (?)", (d,))

    conn.commit()
    conn.close()


def insert_lot(compte, date_controle, numero_lot, variete, producteur, ferme):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lots (compte, date_controle, numero_lot, variete, producteur, ferme)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (compte, str(date_controle), numero_lot, variete, producteur, ferme))
    lot_id = cur.lastrowid
    conn.commit()
    conn.close()
    return lot_id


def insert_produit_fini(lot_id, matricule, calibre, total_fruits, defauts, conformes, taux_conforme, taux_non_conforme):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO controles_produit_fini
        (lot_id, matricule, calibre, total_fruits, defauts, conformes, taux_conforme, taux_non_conforme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lot_id,
        matricule,
        calibre,
        total_fruits,
        defauts,
        conformes,
        taux_conforme,
        taux_non_conforme
    ))
    conn.commit()
    conn.close()


def insert_ecarts(lot_id, matricule, calibre, total_fruits, fruits_conformes, ecarts, taux_conforme, taux_non_conforme, verification, detail_defauts):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO controles_ecarts
        (lot_id, matricule, calibre, total_fruits, fruits_conformes, ecarts, taux_conforme, taux_non_conforme, verification)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lot_id,
        matricule,
        calibre,
        total_fruits,
        fruits_conformes,
        ecarts,
        taux_conforme,
        taux_non_conforme,
        verification
    ))

    controle_ecart_id = cur.lastrowid

    for item in detail_defauts:
        cur.execute("""
            INSERT INTO details_defauts
            (controle_ecart_id, type_defaut, quantite, pourcentage)
            VALUES (?, ?, ?, ?)
        """, (
            controle_ecart_id,
            item["type_defaut"],
            item["quantite"],
            item["pourcentage"]
        ))

    conn.commit()
    conn.close()


def get_types_defauts():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, nom FROM types_defauts ORDER BY nom ASC",
        conn
    )
    conn.close()
    return df


def get_historique_pf(filtre_lot=""):
    conn = get_connection()
    query = """
        SELECT
            pf.id,
            l.compte AS campagne,
            l.date_controle,
            l.numero_lot,
            l.variete,
            pf.matricule,
            pf.calibre,
            pf.total_fruits,
            pf.defauts,
            pf.conformes,
            pf.taux_conforme,
            pf.taux_non_conforme,
            pf.created_at
        FROM controles_produit_fini pf
        JOIN lots l ON pf.lot_id = l.id
        WHERE 1=1
    """

    params = []

    if filtre_lot:
        query += " AND l.numero_lot LIKE ?"
        params.append(f"%{filtre_lot}%")

    query += " ORDER BY pf.id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_historique_ecarts(filtre_lot=""):
    conn = get_connection()
    query = """
        SELECT
            e.id,
            l.compte AS campagne,
            l.date_controle,
            l.numero_lot,
            l.variete,
            e.matricule,
            e.calibre,
            e.total_fruits,
            e.fruits_conformes,
            e.ecarts,
            e.taux_conforme,
            e.taux_non_conforme,
            e.verification,
            e.created_at
        FROM controles_ecarts e
        JOIN lots l ON e.lot_id = l.id
        WHERE 1=1
    """

    params = []

    if filtre_lot:
        query += " AND l.numero_lot LIKE ?"
        params.append(f"%{filtre_lot}%")

    query += " ORDER BY e.id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_dashboard_data():
    conn = get_connection()

    pf_count = pd.read_sql_query(
        "SELECT COUNT(*) AS n FROM controles_produit_fini",
        conn
    )["n"][0]

    ec_count = pd.read_sql_query(
        "SELECT COUNT(*) AS n FROM controles_ecarts",
        conn
    )["n"][0]

    pf_avg = pd.read_sql_query(
        "SELECT AVG(taux_conforme) AS avg_pf FROM controles_produit_fini",
        conn
    )["avg_pf"][0]

    ec_avg = pd.read_sql_query(
        "SELECT AVG(taux_conforme) AS avg_ec FROM controles_ecarts",
        conn
    )["avg_ec"][0]

    defauts_df = pd.read_sql_query("""
        SELECT
            type_defaut,
            SUM(quantite) AS total_quantite
        FROM details_defauts
        GROUP BY type_defaut
        ORDER BY total_quantite DESC
    """, conn)

    conn.close()
    return pf_count, ec_count, pf_avg, ec_avg, defauts_df


def generate_pdf_report():
    conn = get_connection()

    pf_df = pd.read_sql_query("""
        SELECT
            l.compte AS campagne,
            l.date_controle,
            l.numero_lot,
            l.variete,
            pf.calibre,
            COUNT(*) AS nombre_controles,
            SUM(pf.total_fruits) AS total_fruits,
            SUM(pf.defauts) AS total_defauts,
            AVG(pf.taux_conforme) AS moyenne_taux_conforme,
            AVG(pf.taux_non_conforme) AS moyenne_taux_non_conforme
        FROM controles_produit_fini pf
        JOIN lots l ON pf.lot_id = l.id
        GROUP BY
            l.compte,
            l.date_controle,
            l.numero_lot,
            l.variete,
            pf.calibre
        ORDER BY pf.calibre
    """, conn)

    ecarts_df = pd.read_sql_query("""
        SELECT
            l.compte AS campagne,
            l.date_controle,
            l.numero_lot,
            l.variete,
            e.calibre,
            COUNT(*) AS nombre_controles,
            SUM(e.total_fruits) AS total_fruits,
            SUM(e.fruits_conformes) AS total_conformes,
            SUM(e.ecarts) AS total_ecarts,
            AVG(e.taux_conforme) AS moyenne_taux_conforme,
            AVG(e.taux_non_conforme) AS moyenne_taux_non_conforme
        FROM controles_ecarts e
        JOIN lots l ON e.lot_id = l.id
        GROUP BY
            l.compte,
            l.date_controle,
            l.numero_lot,
            l.variete,
            e.calibre
        ORDER BY e.calibre
    """, conn)

    defauts_df = pd.read_sql_query("""
        SELECT
            d.type_defaut,
            SUM(d.quantite) AS quantite_totale
        FROM details_defauts d
        GROUP BY d.type_defaut
        ORDER BY quantite_totale DESC
    """, conn)

    conn.close()

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Rapport Qualite Citrus", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resume Produit Fini par calibre", ln=True)
    pdf.set_font("Arial", size=9)

    if pf_df.empty:
        pdf.cell(0, 8, "Aucun controle Produit Fini.", ln=True)
    else:
        for _, row in pf_df.iterrows():
            texte = (
                f"Lot {row['numero_lot']} | Calibre {row['calibre']} | "
                f"Controles: {row['nombre_controles']} | "
                f"Total fruits: {row['total_fruits']} | "
                f"Defauts: {row['total_defauts']} | "
                f"Moy. conforme: {row['moyenne_taux_conforme']:.2f}% | "
                f"Moy. non conforme: {row['moyenne_taux_non_conforme']:.2f}%"
            )
            pdf.multi_cell(0, 7, texte)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resume Ecarts par calibre", ln=True)
    pdf.set_font("Arial", size=9)

    if ecarts_df.empty:
        pdf.cell(0, 8, "Aucun controle Ecarts.", ln=True)
    else:
        for _, row in ecarts_df.iterrows():
            texte = (
                f"Lot {row['numero_lot']} | Calibre {row['calibre']} | "
                f"Controles: {row['nombre_controles']} | "
                f"Total fruits: {row['total_fruits']} | "
                f"Conformes: {row['total_conformes']} | "
                f"Ecarts: {row['total_ecarts']} | "
                f"Moy. conforme: {row['moyenne_taux_conforme']:.2f}% | "
                f"Moy. non conforme: {row['moyenne_taux_non_conforme']:.2f}%"
            )
            pdf.multi_cell(0, 7, texte)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Detail global des defauts", ln=True)
    pdf.set_font("Arial", size=9)

    if defauts_df.empty:
        pdf.cell(0, 8, "Aucun defaut enregistre.", ln=True)
    else:
        total_defauts = defauts_df["quantite_totale"].sum()

        for _, row in defauts_df.iterrows():
            pct = (
                row["quantite_totale"] / total_defauts * 100
                if total_defauts > 0
                else 0
            )

            texte = (
                f"{row['type_defaut']} : "
                f"{row['quantite_totale']} "
                f"({pct:.2f}%)"
            )
            pdf.cell(0, 7, texte, ln=True)

    return pdf.output(dest="S").encode("latin-1")
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compte TEXT NOT NULL,
            date_controle TEXT NOT NULL,
            numero_lot TEXT NOT NULL,
            variete TEXT NOT NULL,
            producteur TEXT,
            ferme TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS controles_produit_fini (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            matricule TEXT NOT NULL,
            calibre TEXT NOT NULL,
            total_fruits INTEGER NOT NULL,
            defauts INTEGER NOT NULL,
            conformes INTEGER NOT NULL,
            taux_conforme REAL NOT NULL,
            taux_non_conforme REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lot_id) REFERENCES lots(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS controles_ecarts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            matricule TEXT NOT NULL,
            calibre TEXT NOT NULL,
            total_fruits INTEGER NOT NULL,
            fruits_conformes INTEGER NOT NULL,
            ecarts INTEGER NOT NULL,
            taux_conforme REAL NOT NULL,
            taux_non_conforme REAL NOT NULL,
            verification TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lot_id) REFERENCES lots(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS details_defauts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            controle_ecart_id INTEGER NOT NULL,
            type_defaut TEXT NOT NULL,
            quantite INTEGER NOT NULL,
            pourcentage REAL NOT NULL,
            FOREIGN KEY (controle_ecart_id) REFERENCES controles_ecarts(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS types_defauts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    """)

    default_defauts = [
        "Défaut de coloration (vert)",
        "Marbrures",
        "Blessures",
        "Blessures de pédoncule",
        "Pédoncule long",
        "Affaissement de cellule",
        "Frottement",
        "Coup de soleil",
        "Dégâts escargots",
        "Dégâts de grêle",
        "Fruit écrasé",
        "Fruit brûlé",
        "Fruit attaché",
        "Blessures écorce",
        "Pédoncule pourri",
        "Acariens",
        "Fruit déformé",
        "Fruit mou",
        "Alternaria",
        "Éclatement",
        "Fruit vert",
        "Déformé"
    ]

    for d in default_defauts:
        cur.execute("INSERT OR IGNORE INTO types_defauts (nom) VALUES (?)", (d,))

    conn.commit()
    conn.close()


def insert_lot(compte, date_controle, numero_lot, variete, producteur, ferme):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lots (compte, date_controle, numero_lot, variete, producteur, ferme)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (compte, str(date_controle), numero_lot, variete, producteur, ferme))
    lot_id = cur.lastrowid
    conn.commit()
    conn.close()
    return lot_id


def insert_produit_fini(lot_id, matricule, calibre, total_fruits, defauts, conformes, taux_conforme, taux_non_conforme):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO controles_produit_fini
        (lot_id, matricule, calibre, total_fruits, defauts, conformes, taux_conforme, taux_non_conforme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (lot_id, matricule, calibre, total_fruits, defauts, conformes, taux_conforme, taux_non_conforme))
    conn.commit()
    conn.close()


def insert_ecarts(lot_id, matricule, calibre, total_fruits, fruits_conformes, ecarts, taux_conforme, taux_non_conforme, verification, detail_defauts):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO controles_ecarts
        (lot_id, matricule, calibre, total_fruits, fruits_conformes, ecarts, taux_conforme, taux_non_conforme, verification)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (lot_id, matricule, calibre, total_fruits, fruits_conformes, ecarts, taux_conforme, taux_non_conforme, verification))

    controle_ecart_id = cur.lastrowid

    for item in detail_defauts:
        cur.execute("""
            INSERT INTO details_defauts (controle_ecart_id, type_defaut, quantite, pourcentage)
            VALUES (?, ?, ?, ?)
        """, (controle_ecart_id, item["type_defaut"], item["quantite"], item["pourcentage"]))

    conn.commit()
    conn.close()


def get_types_defauts():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, nom FROM types_defauts ORDER BY nom ASC", conn)
    conn.close()
    return df


def get_historique_pf(filtre_lot=""):
    conn = get_connection()
    query = """
        SELECT
            pf.id,
            l.compte AS campagne,
            l.date_controle,
            l.numero_lot,
            l.variete,
            pf.matricule,
            pf.calibre,
            pf.total_fruits,
            pf.defauts,
            pf.conformes,
            pf.taux_conforme,
            pf.taux_non_conforme,
            pf.created_at
        FROM controles_produit_fini pf
        JOIN lots l ON pf.lot_id = l.id
        WHERE 1=1
    """
    params = []

    if filtre_lot:
        query += " AND l.numero_lot LIKE ?"
        params.append(f"%{filtre_lot}%")

    query += " ORDER BY pf.id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_historique_ecarts(filtre_lot=""):
    conn = get_connection()
    query = """
        SELECT
            e.id,
            l.compte AS campagne,
            l.date_controle,
            l.numero_lot,
            l.variete,
            e.matricule,
            e.calibre,
            e.total_fruits,
            e.fruits_conformes,
            e.ecarts,
            e.taux_conforme,
            e.taux_non_conforme,
            e.verification,
            e.created_at
        FROM controles_ecarts e
        JOIN lots l ON e.lot_id = l.id
        WHERE 1=1
    """
    params = []

    if filtre_lot:
        query += " AND l.numero_lot LIKE ?"
        params.append(f"%{filtre_lot}%")

    query += " ORDER BY e.id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_dashboard_data():
    conn = get_connection()

    pf_count = pd.read_sql_query("SELECT COUNT(*) as n FROM controles_produit_fini", conn)["n"][0]
    ec_count = pd.read_sql_query("SELECT COUNT(*) as n FROM controles_ecarts", conn)["n"][0]

    pf_avg = pd.read_sql_query("SELECT AVG(taux_conforme) as avg_pf FROM controles_produit_fini", conn)["avg_pf"][0]
    ec_avg = pd.read_sql_query("SELECT AVG(taux_conforme) as avg_ec FROM controles_ecarts", conn)["avg_ec"][0]

    defauts_df = pd.read_sql_query("""
        SELECT type_defaut, SUM(quantite) as total_quantite
        FROM details_defauts
        GROUP BY type_defaut
        ORDER BY total_quantite DESC
    """, conn)

    conn.close()
    return pf_count, ec_count, pf_avg, ec_avg, defauts_df


init_db()


# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "page1"

if "lot_data" not in st.session_state:
    st.session_state.lot_data = {
        "compte": CAMPAGNE_AUTO,
        "date_controle": date.today(),
        "lot": "",
        "variete": "",
        "producteur": "",
        "ferme": ""
    }

if "current_lot_id" not in st.session_state:
    st.session_state.current_lot_id = None


def top_icons(show_back=True):
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("➕", help="Nouveau lot", use_container_width=True):
            st.session_state.lot_data = {
                "compte": CAMPAGNE_AUTO,
                "date_controle": date.today(),
                "lot": "",
                "variete": "",
                "producteur": "",
                "ferme": ""
            }
            st.session_state.current_lot_id = None
            st.session_state.page = "page1"
            st.rerun()

    with col2:
        if st.button("🔍", help="Recherche", use_container_width=True):
            st.session_state.page = "recherche"
            st.rerun()

    with col3:
        if show_back:
            if st.button("↩", help="Retour menu", use_container_width=True):
                st.session_state.page = "menu"
                st.rerun()
        else:
            st.button("↩", disabled=True, use_container_width=True)

    with col4:
        if st.button("📊", help="Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()

    with col5:
        st.button("🖨", help="Impression / PDF plus tard", disabled=True, use_container_width=True)


# ---------------- PAGE 1 ----------------
if st.session_state.page == "page1":
    st.title("Application Qualité Citrus 🍊")
    st.header("Page 1 : Informations du lot")

    compte = CAMPAGNE_AUTO
    st.text_input("Campagne", value=compte, disabled=True)

    date_controle = st.date_input("Date de contrôle", value=st.session_state.lot_data["date_controle"])
    lot = st.text_input("Numéro de lot", value=st.session_state.lot_data["lot"])
    variete = st.text_input("Variété", value=st.session_state.lot_data["variete"])
    producteur = st.text_input("Producteur", value=st.session_state.lot_data["producteur"])
    ferme = st.text_input("Ferme", value=st.session_state.lot_data["ferme"])

    if st.button("Valider", use_container_width=True):
        if not lot or not variete:
            st.error("Veuillez remplir au moins : Numéro de lot et Variété.")
        else:
            st.session_state.lot_data = {
                "compte": compte,
                "date_controle": date_controle,
                "lot": lot,
                "variete": variete,
                "producteur": producteur,
                "ferme": ferme
            }

            lot_id = insert_lot(compte, date_controle, lot, variete, producteur, ferme)
            st.session_state.current_lot_id = lot_id
            st.session_state.page = "menu"
            st.rerun()


# ---------------- PAGE 2 MENU ----------------
elif st.session_state.page == "menu":
    st.title("Application Qualité Citrus 🍊")
    top_icons(show_back=False)

    st.header("Menu de contrôle")

    st.subheader("Lot en cours")
    st.write(f"**Campagne :** {st.session_state.lot_data['compte']}")
    st.write(f"**Date de contrôle :** {st.session_state.lot_data['date_controle']}")
    st.write(f"**Numéro de lot :** {st.session_state.lot_data['lot']}")
    st.write(f"**Variété :** {st.session_state.lot_data['variete']}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Contrôle Produit Fini", use_container_width=True):
            st.session_state.page = "produit_fini"
            st.rerun()

    with col2:
        if st.button("Contrôle des Écarts", use_container_width=True):
            st.session_state.page = "ecarts"
            st.rerun()


# ---------------- PRODUIT FINI ----------------
elif st.session_state.page == "produit_fini":
    st.title("Application Qualité Citrus 🍊")
    top_icons(show_back=True)

    st.header("Contrôle Produit Fini")

    st.subheader("Informations du lot")
    st.write(f"**Campagne :** {st.session_state.lot_data['compte']}")
    st.write(f"**Date de contrôle :** {st.session_state.lot_data['date_controle']}")
    st.write(f"**Numéro de lot :** {st.session_state.lot_data['lot']}")
    st.write(f"**Variété :** {st.session_state.lot_data['variete']}")

    st.markdown("---")
    st.subheader("Saisie")

    matricule = st.text_input("Matricule contrôleur")
    calibre = st.text_input("Calibre")
    total_fruits = st.number_input("Nombre total de fruits", min_value=0, step=1)
    defauts = st.number_input("Nombre de défauts", min_value=0, step=1)

    conformes = total_fruits - defauts if total_fruits >= defauts else 0

    if total_fruits > 0 and defauts <= total_fruits:
        taux_non_conforme = (defauts / total_fruits) * 100
        taux_conforme = (conformes / total_fruits) * 100
    else:
        taux_non_conforme = 0.0
        taux_conforme = 0.0

    resultats_pf = pd.DataFrame([
        {
            "Nombre conforme": int(conformes),
            "Taux conforme (%)": round(taux_conforme, 2),
            "Taux non conforme (%)": round(taux_non_conforme, 2)
        }
    ])

    st.markdown("---")
    st.subheader("Résultats automatiques")
    st.dataframe(resultats_pf, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Valider Produit Fini", use_container_width=True):
            if not matricule or not calibre:
                st.error("Veuillez remplir le matricule et le calibre.")
            elif total_fruits <= 0:
                st.error("Le nombre total de fruits doit être supérieur à 0.")
            elif defauts > total_fruits:
                st.error("Le nombre de défauts ne peut pas dépasser le total.")
            elif st.session_state.current_lot_id is None:
                st.error("Aucun lot actif.")
            else:
                insert_produit_fini(
                    st.session_state.current_lot_id,
                    matricule,
                    calibre,
                    int(total_fruits),
                    int(defauts),
                    int(conformes),
                    float(taux_conforme),
                    float(taux_non_conforme)
                )
                st.success("Contrôle Produit Fini enregistré.")
                st.session_state.page = "menu"
                st.rerun()

    with col2:
        if st.button("Retour menu", use_container_width=True):
            st.session_state.page = "menu"
            st.rerun()


# ---------------- ECARTS ----------------
# ---------------- ECARTS ----------------
elif st.session_state.page == "ecarts":
    st.title("Application Qualité Citrus 🍊")
    top_icons(show_back=True)

    st.header("Contrôle des Écarts")

    st.subheader("Informations du lot")
    st.write(f"**Campagne :** {st.session_state.lot_data['compte']}")
    st.write(f"**Date de contrôle :** {st.session_state.lot_data['date_controle']}")
    st.write(f"**Numéro de lot :** {st.session_state.lot_data['lot']}")
    st.write(f"**Variété :** {st.session_state.lot_data['variete']}")

    st.markdown("---")
    st.subheader("Saisie du contrôle")

    matricule = st.text_input("Matricule contrôleur")
    calibre = st.text_input("Calibre")
    total_fruits = st.number_input("Nombre total de fruits", min_value=0, step=1)
    fruits_conformes = st.number_input("Nombre de fruits conformes", min_value=0, step=1)

    ecarts = total_fruits - fruits_conformes if total_fruits >= fruits_conformes else 0

    if total_fruits > 0 and fruits_conformes <= total_fruits:
        taux_conforme = (fruits_conformes / total_fruits) * 100
        taux_non_conforme = (ecarts / total_fruits) * 100
    else:
        taux_conforme = 0.0
        taux_non_conforme = 0.0

    st.markdown("---")
    st.subheader("Validation calcul")

    if "show_results_ecarts" not in st.session_state:
        st.session_state.show_results_ecarts = False

    if st.button("Valider calcul Écarts", use_container_width=True):
        if not matricule or not calibre:
            st.error("Veuillez remplir le matricule et le calibre.")
        elif total_fruits <= 0:
            st.error("Le nombre total de fruits doit être supérieur à 0.")
        elif fruits_conformes > total_fruits:
            st.error("Le nombre de fruits conformes ne peut pas dépasser le total.")
        else:
            st.session_state.show_results_ecarts = True

    if st.session_state.show_results_ecarts:
        resultats_ecarts = pd.DataFrame([
            {
                "Nombre fruits conformes": int(fruits_conformes),
                "Nombre fruits non conformes": int(ecarts),
                "Taux conforme (%)": round(taux_conforme, 2),
                "Taux non conforme (%)": round(taux_non_conforme, 2)
            }
        ])

        st.markdown("---")
        st.subheader("Résultats")
        st.dataframe(resultats_ecarts, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Détail des défauts")

    if "nb_lignes_defauts" not in st.session_state:
        st.session_state.nb_lignes_defauts = 1

    defauts_df = get_types_defauts()
    liste_defauts = defauts_df["nom"].tolist()

    data = []
    detail_defauts = []
    somme_defauts = 0

    for i in range(st.session_state.nb_lignes_defauts):
        st.markdown(f"### Défaut {i + 1}")

        col_a, col_b = st.columns([2, 1])

        with col_a:
            choix = st.selectbox(
                f"Type défaut {i + 1}",
                [""] + liste_defauts,
                key=f"choix_ecart_{i}",
                help="Clique puis tape le début du défaut"
            )

        with col_b:
            qte = st.number_input(
                f"Quantité {i + 1}",
                min_value=0,
                step=1,
                key=f"qte_ecart_{i}"
            )

        pourcentage = (qte / ecarts * 100) if ecarts > 0 else 0.0

        if choix:
            data.append({
                "Type défaut": choix,
                "Quantité": int(qte),
                "Pourcentage (%)": round(pourcentage, 2)
            })

        if choix and qte > 0:
            detail_defauts.append({
                "type_defaut": choix,
                "quantite": int(qte),
                "pourcentage": float(pourcentage)
            })

        if qte > 0:
            somme_defauts += qte

    if st.button("➕ Ajouter défaut", use_container_width=True):
        st.session_state.nb_lignes_defauts += 1
        st.rerun()

    st.markdown("---")
    st.subheader("Tableau des défauts")

    df = pd.DataFrame(data)

    if df.empty:
        st.info("Aucun défaut sélectionné.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    verification = "OK" if somme_defauts == ecarts else "A vérifier"

    st.markdown("---")
    st.subheader("Enregistrement")

    if st.button("Valider et enregistrer Écarts", use_container_width=True):
        if not matricule or not calibre:
            st.error("Veuillez remplir le matricule et le calibre.")
        elif total_fruits <= 0:
            st.error("Le nombre total de fruits doit être supérieur à 0.")
        elif fruits_conformes > total_fruits:
            st.error("Le nombre de fruits conformes ne peut pas dépasser le total.")
        elif somme_defauts != ecarts:
            st.error(
                f"La somme des défauts doit être égale aux écarts. "
                f"Somme défauts = {somme_defauts}, écarts = {ecarts}."
            )
        elif st.session_state.current_lot_id is None:
            st.error("Aucun lot actif.")
        else:
            insert_ecarts(
                st.session_state.current_lot_id,
                matricule,
                calibre,
                int(total_fruits),
                int(fruits_conformes),
                int(ecarts),
                float(taux_conforme),
                float(taux_non_conforme),
                verification,
                detail_defauts
            )

            st.session_state.nb_lignes_defauts = 1
            st.session_state.show_results_ecarts = False
            st.success("Contrôle des écarts enregistré.")
            st.session_state.page = "menu"
            st.rerun()


# ---------------- RECHERCHE ----------------
elif st.session_state.page == "recherche":
    st.title("Application Qualité Citrus 🍊")
    top_icons(show_back=True)

    st.header("Recherche")

    filtre_lot = st.text_input("Rechercher par numéro de lot")

    st.markdown("---")
    st.subheader("Historique Produit Fini")
    hist_pf = get_historique_pf(filtre_lot=filtre_lot)
    if hist_pf.empty:
        st.info("Aucun contrôle Produit Fini trouvé.")
    else:
        st.dataframe(hist_pf, use_container_width=True)

    st.markdown("---")
    st.subheader("Historique Écarts")
    hist_ec = get_historique_ecarts(filtre_lot=filtre_lot)
    if hist_ec.empty:
        st.info("Aucun contrôle Écarts trouvé.")
    else:
        st.dataframe(hist_ec, use_container_width=True)


# ---------------- DASHBOARD ----------------
# ---------------- DASHBOARD ----------------
elif st.session_state.page == "dashboard":
    st.title("Application Qualité Citrus 🍊")
    top_icons(show_back=True)

    st.header("Tableau de bord / Analyse des défauts")

    pf_count, ec_count, pf_avg, ec_avg, defauts_df = get_dashboard_data()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Contrôles PF", pf_count)
    col2.metric("Contrôles Écarts", ec_count)
    col3.metric("Moyenne PF", f"{(pf_avg or 0):.2f}%")
    col4.metric("Moyenne Écarts", f"{(ec_avg or 0):.2f}%")

    st.markdown("---")
    st.subheader("Analyse globale des défauts")

    if defauts_df.empty:
        st.info("Aucun défaut enregistré.")
    else:
        total_defauts = defauts_df["total_quantite"].sum()

        defauts_df["Pourcentage (%)"] = (
            defauts_df["total_quantite"] / total_defauts * 100
        ).round(2)

        st.dataframe(defauts_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Diagramme : Quantité par type de défaut")

        chart_bar = (
            alt.Chart(defauts_df)
            .mark_bar()
            .encode(
                x=alt.X("type_defaut:N", title="Type de défaut", sort="-y"),
                y=alt.Y("total_quantite:Q", title="Quantité"),
                color=alt.Color("type_defaut:N", legend=None),
                tooltip=[
                    alt.Tooltip("type_defaut:N", title="Défaut"),
                    alt.Tooltip("total_quantite:Q", title="Quantité"),
                    alt.Tooltip("Pourcentage (%):Q", title="Pourcentage")
                ]
            )
            .properties(height=400)
        )

        st.altair_chart(chart_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("Diagramme : Pourcentage par défaut")

        chart_pie = (
            alt.Chart(defauts_df)
            .mark_arc(innerRadius=50)
            .encode(
                theta=alt.Theta("total_quantite:Q"),
                color=alt.Color("type_defaut:N", title="Défaut"),
                tooltip=[
                    alt.Tooltip("type_defaut:N", title="Défaut"),
                    alt.Tooltip("total_quantite:Q", title="Quantité"),
                    alt.Tooltip("Pourcentage (%):Q", title="Pourcentage")
                ]
            )
            .properties(height=450)
        )

        st.altair_chart(chart_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("Analyse par contrôle")

    conn = get_connection()

    analyse_controles = pd.read_sql_query("""
        SELECT
            e.id AS controle_ecart_id,
            l.numero_lot,
            l.date_controle,
            l.variete,
            e.matricule,
            e.calibre,
            e.total_fruits,
            e.fruits_conformes,
            e.ecarts,
            d.type_defaut,
            d.quantite,
            d.pourcentage
        FROM details_defauts d
        JOIN controles_ecarts e ON d.controle_ecart_id = e.id
        JOIN lots l ON e.lot_id = l.id
        ORDER BY e.id DESC
    """, conn)

    conn.close()

    if analyse_controles.empty:
        st.info("Aucun détail par contrôle enregistré.")
    else:
        st.dataframe(analyse_controles, use_container_width=True, hide_index=True)

        controle_ids = analyse_controles["controle_ecart_id"].unique().tolist()

        controle_choisi = st.selectbox(
            "Choisir un contrôle pour analyse détaillée",
            controle_ids
        )

        df_controle = analyse_controles[
            analyse_controles["controle_ecart_id"] == controle_choisi
        ]

        st.markdown("### Défauts du contrôle choisi")

        st.dataframe(df_controle, use_container_width=True, hide_index=True)

        chart_controle = (
            alt.Chart(df_controle)
            .mark_bar()
            .encode(
                x=alt.X("type_defaut:N", title="Type de défaut", sort="-y"),
                y=alt.Y("pourcentage:Q", title="Pourcentage (%)"),
                color=alt.Color("type_defaut:N", legend=None),
                tooltip=[
                    alt.Tooltip("type_defaut:N", title="Défaut"),
                    alt.Tooltip("quantite:Q", title="Quantité"),
                    alt.Tooltip("pourcentage:Q", title="Pourcentage")
                ]
            )
            .properties(height=350)
        )

        st.altair_chart(chart_controle, use_container_width=True)