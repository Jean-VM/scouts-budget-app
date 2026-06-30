import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import requests  # Nécessaire pour envoyer l'e-mail via API

# Configuration de la page mobile-friendly
st.set_page_config(page_title="Scout Budget 2026", page_icon="🏕️", layout="centered")

# --- CONFIGURATION DE L'EMAIL DU CHEF FINANCES ---
# ⚠️ REMPLACE PAR TON ADRESSE EMAIL ICI :
CHEF_FINANCES_EMAIL = "jean.vandermeulen1160@gmail.com"

# 1. Connexion sécurisée au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURATION DES DONNÉES DU CAMP ---
STARTING_BUDGET = 25200
TOTAL_BUDGETED = 19300  # Somme de toutes les catégories
BUFFER_ZONE = 5900      # Ce qu'il doit rester à la fin

# Liste des 11 chefs
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

# --- FONCTION POUR ENVOYER L'EMAIL ---
def send_email_notification(leader_name, title, amount, category):
    url = f"https://formsubmit.co/ajax/{CHEF_FINANCES_EMAIL}"
    payload = {
        "Sujet": f"🚨 Demande de remboursement Scout - {leader_name}",
        "Chef": leader_name,
        "Dépense": title,
        "Montant": f"{amount} $",
        "Catégorie": category,
        "Message": f"Salut ! {leader_name} vient de déclarer une dépense payée de sa poche. Pense à le rembourser."
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception:
        return False

# --- CHARGEMENT DES DONNÉES ---
try:
    df_expenses = conn.read(worksheet="Expenses", ttl=0)
    if df_expenses.empty or "Amount" not in df_expenses.columns:
        df_expenses = pd.DataFrame(columns=["Timestamp", "Name", "Title", "Amount", "Category", "Payment Method", "Reimbursement Status"])
    else:
        df_expenses["Amount"] = pd.to_numeric(df_expenses["Amount"], errors="coerce").fillna(0)
except Exception:
    df_expenses = pd.DataFrame(columns=["Timestamp", "Name", "Title", "Amount", "Category", "Payment Method", "Reimbursement Status"])

# --- NAVIGATION ---
tab1, tab2 = st.tabs(["📊 Tableau de Bord", "➕ Ajouter une Dépense"])

# ==========================================
# TAB 1 : TABLEAU DE BORD
# ==========================================
with tab1:
    st.title("🏕️ Suivi du Budget - Scout Camp")
    
    total_spent = df_expenses["Amount"].sum()
    remaining_total = STARTING_BUDGET - total_spent
    
    st.metric(label="💰 Total Dépensé", value=f"{total_spent:.2f} $ / {TOTAL_BUDGETED} $")
    
    if total_spent > TOTAL_BUDGETED:
        st.error(f"⚠️ DANGER ZONE !! On pioche dans les 5900$ de buffer ! Il reste {remaining_total:.2f}$ au total.")
    elif total_spent > (TOTAL_BUDGETED * 0.85):
        st.warning(f"🟠 On approche de la zone rouge. Danger imminent. Dépenses actuelles : {total_spent:.2f}$")
    else:
        st.success(f"🟢 Tout va bien, le buffer de 5900$ est intact. Capacité restante avant danger : {TOTAL_BUDGETED - total_spent:.2f}$")

    st.subheader("📈 Courbe, Limites Globales et Budgets par Catégorie")
    if not df_expenses.empty:
        df_copy = df_expenses.copy()
        # Conversion propre en vraies dates
        df_copy["Timestamp"] = pd.to_datetime(df_copy["Timestamp"], errors='coerce')
        df_sorted = df_copy.dropna(subset=["Timestamp"]).sort_values("Timestamp")
        
        if not df_sorted.empty:
            # 1. Calcul de la courbe principale (Dépenses réelles cumulées)
            df_sorted["💰 Dépenses Totales Cumulées"] = df_sorted["Amount"].cumsum()
            
            # 2. Ajout des lignes de repères globaux
            df_sorted["🔴 Limite Budget Cible (19.3k $)"] = TOTAL_BUDGETED
            df_sorted["🚨 Budget Max avec Buffer (25.2k $)"] = STARTING_BUDGET
            
            # 3. Ajout des lignes horizontales pour CHAQUE catégorie
            for cat, limit in CATEGORIES.items():
                df_sorted[f"📂 Limite {cat} ({limit} $)"] = limit
            
            # Liste complète des colonnes à afficher dans l'ordre de la légende
            columns_to_show = [
                "💰 Dépenses Totales Cumulées",
                "🔴 Limite Budget Cible (19.3k $)",
                "🚨 Budget Max avec Buffer (25.2k $)"
            ] + [f"📂 Limite {cat} ({limit} $)" for cat in CATEGORIES.keys()]
            
            # Préparation des données finales avec l'Axe X (Timestamp)
            df_chart = df_sorted.set_index("Timestamp")[columns_to_show]
            
            # 4. Attribution d'un beau code couleur explicite
            # Ordre des couleurs : Dépenses (Bleu vif), Cible (Rouge), Max (Noir/Alerte), puis les 6 catégories
            chart_colors = [
                "#29b5e8",  # Bleu vif pour le cumulé
                "#ff4b4b",  # Rouge pour la zone de danger théorique
                "#111111",  # Noir pour le hard-cap (Buffer épuisé)
                "#2ca02c",  # Vert (Bus)
                "#9467bd",  # Violet (Car & Fuel)
                "#8c564b",  # Marron (Wood)
                "#e377c2",  # Rose (Food)
                "#ff7f0e",  # Orange (Bread)
                "#bcbd22"   # Olive (General material)
            ]
            
            # Affichage du graphique de lignes
            st.line_chart(df_chart, color=chart_colors)
    else:
        st.info("Aucune dépense pour le moment. Le graphique affichera vos lignes de repères dès la première saisie.")

    st.subheader("📂 Statut par Catégorie")
    for cat, limit in CATEGORIES.items():
        cat_spent = df_expenses[df_expenses["Category"] == cat]["Amount"].sum()
        pct = min(cat_spent / limit, 1.0) if limit > 0 else 0
        
        st.write(f"**{cat}** : {cat_spent:.2f}$ / {limit}$")
        if cat_spent > limit:
            st.progress(pct)
            st.caption(f"❌ DÉPASSÉ DE {cat_spent - limit:.2f}$ !")
        else:
            st.progress(pct)

# ==========================================
# TAB 2 : FORMULAIRE D'AJOUT
# ==========================================
with tab2:
    st.title("➕ Nouvelle Dépense")
    
    st.write("**Qui es-tu ?**")
    name = st.radio("Sélectionne ton nom :", LEADERS, index=0, horizontal=True)
    
    title = st.text_input("Titre de la dépense (ex: '20kg de Pâtes')", "")
    amount = st.number_input("Montant (en $)", min_value=0.0, step=0.50, format="%.2f")
    category = st.selectbox("Catégorie :", list(CATEGORIES.keys()))
    
    is_troop_card = st.toggle("Payé avec la carte de l'Unité / de la Troupe", value=True)
    
    payment_method = "Carte Groupe" if is_troop_card else "Poche Perso"
    reimbursement = "Non" if is_troop_card else "OUI (À rembourser)"
    
    if not is_troop_card:
        st.info(f"💡 Une notification par e-mail sera envoyée automatiquement à {CHEF_FINANCES_EMAIL}")

    if st.button("🚀 Valider la dépense", use_container_width=True):
        if title == "" or amount <= 0:
            st.error("Veuillez entrer un titre et un montant valide.")
        else:
            with st.spinner("Enregistrement dans Google Sheets..."):
                # Création de la ligne
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
                
                # Sauvegarde robuste (Read -> Append -> Update)
                df_actuel = conn.read(worksheet="Expenses", ttl=0)
                df_mis_a_jour = pd.concat([df_actuel, new_row], ignore_index=True)
                conn.update(worksheet="Expenses", data=df_mis_a_jour)
                
                # Envoi du mail si remboursement nécessaire
                if reimbursement == "OUI (À rembourser)":
                    email_sent = send_email_notification(name, title, amount, category)
                    if email_sent:
                        st.toast("📧 E-mail de notification envoyé au chef finances !", icon="📩")
                    else:
                        st.toast("⚠️ Dépense sauvée, mais l'envoi du mail a échoué.", icon="❌")
                
                st.success("Dépense enregistrée avec succès !")
                st.balloons()