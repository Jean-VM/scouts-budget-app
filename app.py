import streamlit as st
# Le nouveau nom d'importation officiel de la bibliothèque :
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuration de la page mobile-friendly
st.set_page_config(page_title="Scout Budget 2026", page_icon="🏕️", layout="centered")

# 1. Connexion sécurisée au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURATION DES DONNÉES DU CAMP ---
STARTING_BUDGET = 25200
TOTAL_BUDGETED = 19300  # Somme de toutes les catégories
BUFFER_ZONE = 5900      # Ce qu'il doit rester à la fin

# Liste des 11 chefs par ordre alphabétique
LEADERS = [
    "Babar", "Fel", "guigui", "Jojo", "Koati", "loulou", 
    "nicogigi", "nichto", "Paf", "wombat", "XeimmmXeimmm"
]

# Catégories de dépenses et leurs limites
CATEGORIES = {
    "Bus": 7300,
    "Car & Fuel": 2500,
    "Wood for constructions": 1500,
    "Food": 6000,
    "Bread": 1000,
    "General material": 1000
}

# --- CHARGEMENT DES DONNÉES ---
# On lit l'onglet 'Expenses'
try:
    df_expenses = conn.read(worksheet="Expenses", ttl=0)
    # Nettoyage si le fichier est vide
    if df_expenses.empty or "Amount" not in df_expenses.columns:
        df_expenses = pd.DataFrame(columns=["Timestamp", "Name", "Title", "Amount", "Category", "Payment Method", "Reimbursement Status"])
    else:
        df_expenses["Amount"] = pd.to_numeric(df_expenses["Amount"], errors="coerce").fillna(0)
except Exception:
    df_expenses = pd.DataFrame(columns=["Timestamp", "Name", "Title", "Amount", "Category", "Payment Method", "Reimbursement Status"])

# --- NAVIGATION ---
# Un système d'onglets simple et gros pour les téléphones
tab1, tab2 = st.tabs(["📊 Tableau de Bord", "➕ Ajouter une Dépense"])

# ==========================================
# TAB 1 : TABLEAU DE BORD
# ==========================================
with tab1:
    st.title("🏕️ Suivi du Budget - Scout Camp")
    
    total_spent = df_expenses["Amount"].sum()
    remaining_total = STARTING_BUDGET - total_spent
    
    # Indicateur global
    st.metric(label="💰 Total Dépensé", value=f"{total_spent} $ / {TOTAL_BUDGETED} $")
    
    # --- LA ZONE DE DANGER (FUNNY ALERT) ---
    if total_spent > TOTAL_BUDGETED:
        st.error(f"⚠️ DANGER ZONE !! On pioche dans les 5900$ de buffer ! Il reste {remaining_total}$ au total.")
        st.toast("🚨 ALERTE ROUGE : CONTACTEZ LE CHEF FINANCES", icon="🚨")
    elif total_spent > (TOTAL_BUDGETED * 0.85):
        st.warning(f"🟠 On approche de la zone rouge. Danger imminent. Dépenses actuelles : {total_spent}$")
    else:
        st.success(f"🟢 Tout va bien, le buffer de 5900$ est intact. Capacité restante avant danger : {TOTAL_BUDGETED - total_spent}$")

    # --- LE GRAPHIQUE D'ÉVOLUTION ---
    st.subheader("📈 Courbe des dépenses")
    if not df_expenses.empty:
        # Trier par date pour la courbe cumulative
        df_expenses["Timestamp"] = pd.to_datetime(df_expenses["Timestamp"], errors='coerce')
        df_sorted = df_expenses.dropna(subset=["Timestamp"]).sort_values("Timestamp")
        
        if not df_sorted.empty:
            df_sorted["Cumsum"] = df_sorted["Amount"].cumsum()
            # Graphique de la courbe de dépenses
            st.line_chart(df_sorted.set_index("Timestamp")["Cumsum"])
    else:
        st.info("Aucune dépense pour le moment. La courbe apparaîtra ici.")

    # --- BARRES DE PROGRESSION PAR CATÉGORIE ---
    st.subheader("📂 Statut par Catégorie")
    for cat, limit in CATEGORIES.items():
        cat_spent = df_expenses[df_expenses["Category"] == cat]["Amount"].sum()
        pct = min(cat_spent / limit, 1.0) if limit > 0 else 0
        
        # Affichage propre
        st.write(f"**{cat}** : {cat_spent}$ / {limit}$")
        if cat_spent > limit:
            st.progress(pct)
            st.caption(f"❌ DÉPASSÉ DE {cat_spent - limit}$ !")
        else:
            st.progress(pct)

# ==========================================
# TAB 2 : FORMULAIRE D'AJOUT (GROS BOUTONS)
# ==========================================
with tab2:
    st.title("➕ Nouvelle Dépense")
    
    # 1. Sélection du Nom (Gros boutons radio horizontaux ou liste)
    st.write("**Qui es-tu ?**")
    name = st.radio("Sélectionne ton nom :", LEADERS, index=0, horizontal=True)
    
    # 2. Infos de la dépense
    title = st.text_input("Titre de la dépense (ex: '20kg de Pâtes', 'Plein du camion')", "")
    amount = st.number_input("Montant (en $)", min_value=0.0, step=0.50, format="%.2f")
    category = st.selectbox("Catégorie :", list(CATEGORIES.keys()))
    
    # 3. Moyen de paiement (Le fameux switch / toggle)
    is_troop_card = st.toggle("Payé avec la carte de l'Unité / de la Troupe", value=True)
    
    payment_method = "Carte Groupe" if is_troop_card else "Poche Perso"
    reimbursement = "Non" if is_troop_card else "OUI (À rembourser)"
    
    if not is_troop_card:
        st.info("💡 Une notification par email sera envoyée automatiquement au chef finances pour le remboursement.")

    # 4. Bouton de soumission robuste
    if st.button("🚀 Valider la dépense", use_container_width=True):
        if title == "" or amount <= 0:
            st.error("Veuillez entrer un titre et un montant valide.")
        else:
            with st.spinner("Enregistrement en cours dans Google Sheets... Ne fermez pas la page."):
                # Création de la ligne
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Name": name,
                    "Title": title,
                    "Amount": amount,
                    "Category": category,
                    "Payment Method": payment_method,
                    "Reimbursement Status": reimbursement
                }])
                
                # Envoi direct à Google Sheets (gère la simultanéité)
                conn.create(worksheet="Expenses", data=new_row)
                
                # Déclenchement de l'email si remboursement nécessaire (Phase 4)
                if reimbursement == "OUI (À rembourser)":
                    # Note : Nous configurerons l'envoi d'email réel à l'étape suivante.
                    st.toast(f"Notification de remboursement générée pour {name} !", icon="📧")
                
                st.success("Dépense enregistrée avec succès ! Retourne sur le Tableau de bord pour voir l'évolution.")
                st.balloons()