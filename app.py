import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Suivi Budgétaire Camp 2026", layout="centered")

# Configuration des paramètres généraux
CHEF_FINANCES_EMAIL = "jean.vandermeulen1160@gmail.com"
STARTING_BUDGET = 25200
TOTAL_BUDGETED = 19300  
BUFFER_ZONE = 5900      

LEADERS = [
    "Babar", "Fel", "guigui", "Jojo", "Koati", "loulou", 
    "nicogigi", "nichto", "Paf", "wombat", "XeimmmXeimmm"
]

CATEGORIES = {
    "Bus": 7300,
    "Car & Fuel": 2500,
    "Wood for constructions": 1500,
    "Food": 6000,
    "Bread": 1000,
    "General material": 1000
}

# Initialisation de la connexion Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Chargement et nettoyage des données
try:
    df_expenses = conn.read(worksheet="Expenses", ttl=0)
    if df_expenses.empty or "Amount" not in df_expenses.columns:
        df_expenses = pd.DataFrame(columns=["Timestamp", "Name", "Title", "Amount", "Category", "Payment Method", "Reimbursement Status"])
    else:
        df_expenses["Amount"] = pd.to_numeric(df_expenses["Amount"], errors="coerce").fillna(0)
except Exception:
    df_expenses = pd.DataFrame(columns=["Timestamp", "Name", "Title", "Amount", "Category", "Payment Method", "Reimbursement Status"])

# Système de navigation
tab1, tab2 = st.tabs(["Tableau de Bord", "Saisie d'une Dépense"])

# ==========================================
# ONGLEUR 1 : TABLEAU DE BORD
# ==========================================
with tab1:
    st.title("Suivi Budgétaire Consolidé")
    
    total_spent = df_expenses["Amount"].sum()
    remaining_total = STARTING_BUDGET - total_spent
    
    st.metric(label="Total Engagé", value=f"{total_spent:.2f} $ / {TOTAL_BUDGETED} $")
    
    # Alertes de gestion des risques
    if total_spent > TOTAL_BUDGETED:
        st.error(f"Dépassement du budget alloué. Prélèvement sur la réserve de secours. Solde total restant : {remaining_total:.2f} $.")
    elif total_spent > (TOTAL_BUDGETED * 0.85):
        st.warning(f"Seuil d'alerte atteint (85%). Volume des dépenses cumulées : {total_spent:.2f} $.")
    else:
        st.success(f"Situation nominale. Réserve de secours de {BUFFER_ZONE} $ préservée. Marge disponible avant alerte : {TOTAL_BUDGETED - total_spent:.2f} $.")

    # Section Graphique
    st.subheader("Analyse Graphique Temporelle et Limites")
    if not df_expenses.empty:
        df_copy = df_expenses.copy()
        df_copy["Timestamp"] = pd.to_datetime(df_copy["Timestamp"], errors='coerce')
        df_sorted = df_copy.dropna(subset=["Timestamp"]).sort_values("Timestamp")
        
        if not df_sorted.empty:
            # Initialisation du dictionnaire de données pour l'axe temporel
            chart_data = {
                "Dépenses Totales Cumulées": df_sorted["Amount"].cumsum(),
                f"Seuil Budget Cible ({TOTAL_BUDGETED} $)": [float(TOTAL_BUDGETED)] * len(df_sorted),
                f"Plafond Absolu ({STARTING_BUDGET} $)": [float(STARTING_BUDGET)] * len(df_sorted)
            }
            
            # Définition stricte de la charte graphique par catégorie
            category_styles = {
                "Bus": {"color_real": "#2ca02c", "color_lim": "#a1d99b"},
                "Car & Fuel": {"color_real": "#9467bd", "color_lim": "#bcbddc"},
                "Wood for constructions": {"color_real": "#8c564b", "color_lim": "#c49c94"},
                "Food": {"color_real": "#e377c2", "color_lim": "#f7b6d2"},
                "Bread": {"color_real": "#ff7f0e", "color_lim": "#ffbb78"},
                "General material": {"color_real": "#bcbd22", "color_lim": "#dbdb8d"}
            }
            
            # Définition de l'ordre des couleurs globales
            color_palette = [
                "#29b5e8",  # Dépenses Totales Cumulées (Bleu corporate)
                "#ff4b4b",  # Seuil Budget Cible (Rouge alerte)
                "#111111"   # Plafond Absolu (Noir)
            ]
            
            # Calcul des courbes réelles et théoriques par catégorie
            for cat, limit in CATEGORIES.items():
                styles = category_styles[cat]
                
                # Calcul de la dépense cumulative spécifique à la catégorie à chaque point temporel
                cat_mask = df_sorted["Category"] == cat
                df_sorted[f"cum_{cat}"] = df_sorted["Amount"].where(cat_mask, 0).cumsum()
                
                # Ajout des séries au graphique
                chart_data[f"Cumul Réel - {cat}"] = df_sorted[f"cum_{cat}"]
                chart_data[f"Limite Fixe - {cat} ({limit} $)"] = [float(limit)] * len(df_sorted)
                
                # Appariement des couleurs (Couleur vive pour le réel, version pastel pour sa limite)
                color_palette.append(styles["color_real"])
                color_palette.append(styles["color_lim"])
            
            # Génération du DataFrame pour l'affichage
            df_chart = pd.DataFrame(chart_data, index=df_sorted["Timestamp"])
            st.line_chart(df_chart, color=color_palette)
        else:
            st.info("Données chronologiques insuffisantes pour générer la courbe.")
    else:
        st.info("Aucun historique disponible.")

    # États de progression individuels par catégorie
    st.subheader("État des Budgets Sectoriels")
    for cat, limit in CATEGORIES.items():
        cat_spent = df_expenses[df_expenses["Category"] == cat]["Amount"].sum()
        pct = min(cat_spent / limit, 1.0) if limit > 0 else 0
        
        st.write(f"**{cat}** : {cat_spent:.2f} $ / {limit} $")
        st.progress(pct)

# ==========================================
# ONGLEUR 2 : SAISIE D'UNE DÉPENSE
# ==========================================
with tab2:
    st.title("Enregistrement d'un Flux Sortant")
    
    name = st.radio("Identité du déclarant :", LEADERS, index=0, horizontal=True)
    title = st.text_input("Désignation de la dépense (ex: Facture carburant, Approvisionnement nourriture)", "")
    amount = st.number_input("Montant exact (en USD)", min_value=0.0, step=0.05, format="%.2f")
    category = st.selectbox("Affectation budgétaire :", list(CATEGORIES.keys()))
    
    is_troop_card = st.toggle("Paiement via la carte de l'Unité", value=True)
    
    payment_method = "Carte Groupe" if is_troop_card else "Fonds Propres"
    reimbursement = "Non" if is_troop_card else "Oui"
    
    if not is_troop_card:
        st.info(f"Note : Un flux sortant sur fonds propres génère une procédure d'approbation de remboursement par courriel vers {CHEF_FINANCES_EMAIL}.")

    if st.button("Valider la transaction", use_container_width=True):
        if title == "" or amount <= 0:
            st.error("Données invalides. Veuillez spécifier un libellé et un montant strictement positif.")
        else:
            with st.spinner("Transmission des données vers le registre central..."):
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{
                    "Timestamp": timestamp_str,
                    "Name": name,
                    "Title": title,
                    "Amount": amount,
                    "Category": category,
                    "Payment Method": payment_method,
                    "Reimbursement Status": reimbursement
                }])
                
                # Transaction d'écriture sécurisée
                df_actuel = conn.read(worksheet="Expenses", ttl=0)
                df_mis_a_jour = pd.concat([df_actuel, new_row], ignore_index=True)
                conn.update(worksheet="Expenses", data=df_mis_a_jour)
                
                st.success("Transaction enregistrée avec succès dans le registre comptable.")
                
                # Génération de la procédure de remboursement (Lien direct mailto)
                if reimbursement == "Oui":
                    sujet = f"Demande de remboursement - {name}".replace(" ", "%20")
                    corps_mail = (
                        f"Bonjour,%0A%0A"
                        f"Une nouvelle écriture sur fonds propres nécessite une régularisation :%0A"
                        f"- Opérateur : {name}%0A"
                        f"- Intitulé : {title}%0A"
                        f"- Volume financier : {amount} $%0A"
                        f"- Poste budgétaire : {category}%0A%0A"
                        f"Veuillez valider le virement de régularisation.".replace(" ", "%20")
                    )
                    mailto_url = f"mailto:{CHEF_FINANCES_EMAIL}?subject={sujet}&body={corps_mail}"
                    
                    st.warning("Action requise : Veuillez formaliser la demande en soumettant le courriel pré-rempli ci-dessous.")
                    st.link_button("Transmettre la demande de remboursement", mailto_url, use_container_width=True)