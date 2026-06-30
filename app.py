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
    url = f"https://formsubmit.co/el/guzado"
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

    st.subheader("📈 Évolution des Dépenses & Zone de Confiance")
    if not df_expenses.empty:
        df_copy = df_expenses.copy()
        df_copy["Timestamp"] = pd.to_datetime(df_copy["Timestamp"], errors='coerce')
        df_sorted = df_copy.dropna(subset=["Timestamp"]).sort_values("Timestamp")
        
        if not df_sorted.empty:
            # 1. Calcul du cumulé réel
            df_sorted["💰 Dépenses Cumulées"] = df_sorted["Amount"].cumsum()
            
            # 2. Création du cadre temporel fixe (30 Juin au 31 Juillet 2026)
            # On génère une plage de dates pour forcer l'axe X à s'étendre proprement
            date_range = pd.date_range(start="2026-06-30", end="2026-07-31", freq="D")
            df_timeline = pd.DataFrame(index=date_range)
            df_timeline.index.name = "Timestamp"
            
            # Associer les dépenses réelles à notre ligne du temps fixe
            df_chart_data = df_sorted.set_index("Timestamp")[["💰 Dépenses Cumulées"]]
            df_combined = df_timeline.join(df_chart_data, how="left")
            
            # Remplir les jours sans dépenses par la dernière valeur connue (propagation)
            df_combined["💰 Dépenses Cumulées"] = df_combined["💰 Dépenses Cumulées"].ffill().fillna(0)
            
            # 3. Ajout des repères demandés
            df_combined["🔴 Limite Target"] = float(TOTAL_BUDGETED) # 19300
            df_combined["🟢 Zone Buffer (Max)"] = float(STARTING_BUDGET) # 25200
            
            # S'assurer que le graphique n'affiche rien au-dessus de notre cadre max (~25000)
            # Streamlit ajuste automatiquement l'axe Y en fonction du maximum des données fournies
            
            # 4. Affichage du graphique simplifié
            # Ordre des colonnes dictant la superposition
            columns_to_graph = ["💰 Dépenses Cumulées", "🔴 Limite Target", "🟢 Zone Buffer (Max)"]
            
            st.line_chart(
                df_combined[columns_to_graph],
                color=["#29b5e8", "#ff4b4b", "#2ca02c"]  # Bleu pour les dépenses, Rouge pour la limite, Vert pour le Buffer
            )
        else:
            st.info("En attente de données valides avec une date pour afficher le graphique.")
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