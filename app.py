import streamlit as st
from supabase import create_client, Client

# --- CONFIGURAZIONE PAGINA STREAMLIT ---
st.set_page_config(
    page_title="SuperConveniente - Comparatore Offerte",
    page_icon="🛒",
    layout="wide"
)

# --- CONNESSIONE SUPABASE ---
# Assicurati di impostare SUPABASE_URL e SUPABASE_KEY nei secrets di Streamlit (o sostituiscili qui)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    # Fallback per test locali o Colab se non usi i secrets di Streamlit
    SUPABASE_URL = "IL_TUO_SUPABASE_URL"
    SUPABASE_KEY = " LA_TUA_SUPABASE_KEY"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- HEADER DELLA DASHBOARD ---
st.title("🛒 SuperConveniente - Monitor Offerte Volantini")
st.markdown("Confronta i prezzi dei volantini estratti e salvati nel database in tempo reale.")

# --- BARRA LATERALE (FILTRI) ---
st.sidebar.header("🔍 Filtri di Ricerca")

# Carica le località disponibili nel DB per popolare il filtro
@st.cache_data(ttl=600)
def get_localita():
    try:
        response = supabase.table("offerte").select("localita").execute()
        locs = list(set([item["localita"].capitalize() for item in response.data]))
        return sorted(locs)
    except Exception:
        return []

localita_disponibili = get_localita()
localita_selezionata = st.sidebar.selectbox(
    "Seleziona Punto Vendita / Località", 
    ["Tutti"] + localita_disponibili
)

query_prodotto = st.sidebar.text_input("Cerca prodotto (es. latte, pasta, coca...)")

# --- QUERY AL DATABASE SUPABASE ---
@st.cache_data(ttl=60)
def carica_offerte(localita, ricerca):
    try:
        query = supabase.table("offerte").select("*")
        
        if localita != "Tutti":
            query = query.ilike("localita", localita)
            
        if ricerca:
            query = query.ilike("prodotto", f"%{ricerca}%")
            
        response = query.order("prezzo", desc=False).execute()
        return response.data
    except Exception as e:
        st.error(f"Errore nel recupero dati da Supabase: {e}")
        return []

dati_offerte = carica_offerte(localita_selezionata, query_prodotto)

# --- CORPO PRINCIPALE ---
col1, col2, col3 = st.columns(3)
col1.metric("Offerte Trovate", len(dati_offerte))
if dati_offerte:
    prezzi = [item["prezzo"] for item in dati_offerte]
    col2.metric("Prezzo Minimo", f"€ {min(prezzi):.2f}")
    col3.metric("Prezzo Medio", f"€ {sum(prezzi)/len(prezzi):.2f}")

st.markdown("---")

if dati_offerte:
    st.subheader(f"📋 Risultati Offerte ({len(dati_offerte)})")
    
    # Rendi la visualizzazione pulita sotto forma di tabella interattiva
    import pandas as pd
    df = pd.DataFrame(dati_offerte)
    
    # Rinomina e seleziona le colonne per l'utente finale
    df_display = df[["supermercato", "localita", "marca", "prodotto", "prezzo", "unita"]].copy()
    df_display.columns = ["Supermercato", "Località", "Marca", "Prodotto", "Prezzo (€", "Unità"]
    
    st.dataframe(
        df_display, 
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("ℹ️ Nessuna offerta trovata con i filtri selezionati o database vuoto. Esegui prima lo script di scraping in Colab!")
