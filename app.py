import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import requests  # Nécessaire pour envoyer l'e-mail via API
import matplotlib.pyplot as plt  # <--- ADD THIS
import matplotlib.dates as mdates  # <--- ADD THIS
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
    # Envoi direct vers l'adresse email configurée (FormSubmit s'occupe de la masquer plus tard)
    url = f"https://formsubmit.co/{CHEF_FINANCES_EMAIL}"
    
    # Payload utilisant la syntaxe de formulaire attendue par FormSubmit
    payload = {
        "_subject": f"🚨 Demande de remboursement Scout - {leader_name}",
        "_captcha": "false",  # Indispensable pour éviter que l'API bloque sur un robot-test de Google
        "Chef": leader_name,
        "Dépense": title,
        "Montant": f"{amount} $",
        "Catégorie": category,
        "Note": f"Salut ! {leader_name} vient de déclarer une dépense payée de sa poche. Pense à le rembourser."
    }
    
    try:
        # data= au lieu de json= simule un vrai formulaire de page web
        response = requests.post(url, data=payload)
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
        # Conversion propre en vraies dates (en gardant uniquement le jour YYYY-MM-DD pour le regroupement)
        df_copy["Date"] = pd.to_datetime(df_copy["Timestamp"], errors='coerce').dt.normalize()
        df_sorted = df_copy.dropna(subset=["Date"]).sort_values("Date")
        
        if not df_sorted.empty:
            # 1. Sommer les dépenses par jour au cas où il y en a plusieurs le même jour
            df_daily = df_sorted.groupby("Date")["Amount"].sum().reset_index()
            
            # 2. Créer la timeline fixe du 30 Juin au 31 Juillet 2026
            date_range = pd.date_range(start="2026-06-30", end="2026-07-31", freq="D")
            df_timeline = pd.DataFrame(index=date_range)
            df_timeline.index.name = "Date"
            
            # 3. Fusionner les dépenses réelles sur la timeline complète
            df_daily = df_daily.set_index("Date")
            df_combined = df_timeline.join(df_daily, how="left").fillna(0)
            
            # 4. Calcul du VRAI cumulé au fil des jours
            df_combined["💰 Dépenses Cumulées"] = df_combined["Amount"].cumsum()
            
            # Repères fixes
            limit_target = float(TOTAL_BUDGETED)  # 19300
            buffer_max = float(STARTING_BUDGET)   # 25200
            
            # 5. Construction du graphique STATIQUE avec Matplotlib (Pas de zoom, pas de mouvement)
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            fig, ax = plt.subplots(figsize=(10, 5))
            
            # Tracer les lignes
            ax.plot(df_combined.index, df_combined["💰 Dépenses Cumulées"], color="#29b5e8", linewidth=3, label="Dépenses Cumulées")
            ax.axhline(y=limit_target, color="#ff4b4b", linestyle="--", linewidth=2, label=f"Limite Target ({limit_target}$)")
            ax.axhline(y=buffer_max, color="#2ca02c", linestyle="-.", linewidth=2, label=f"Zone Buffer Max ({buffer_max}$)")
            
            # Forcer les limites STRICTES des axes (Cadre fixe)
            ax.set_xlim(pd.Timestamp("2026-06-30"), pd.Timestamp("2026-07-31"))
            ax.set_ylim(0, 25000)
            
            # Formatage des axes
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5)) # Un repère tous les 5 jours
            plt.xticks(rotation=45)
            
            ax.set_ylabel("Montant ($)")
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.legend(loc="upper left")
            
            # Affichage dans Streamlit en tant qu'image fixe
            st.pyplot(fig)
            
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