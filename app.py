import streamlit as st
from supabase import create_client, Client
import pandas as pd
from google import genai
from google.genai import types

# --- CONFIGURAZIONE PAGINA STREAMLIT ---
st.set_page_config(
    page_title="SuperConveniente - Comparatore Intelligente",
    page_icon="🛒",
    layout="wide"
)

# --- CONNESSIONI SICURE (TRAMITE SECRETS) ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY_1"]
except Exception as e:
    st.error("⚠️ Configurazione dei Secrets mancante! Assicurati di aver configurato correttamente le credenziali in Streamlit Cloud o nel file locale secrets.toml.")
    st.stop()

@st.cache_resource
def init_clients():
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    return supabase_client, ai_client

supabase, ai_client = init_clients()

# --- HEADER DELLA DASHBOARD ---
st.title("🛒 SuperConveniente - Trova il Prezzo Più Basso")
st.markdown("Cerca un prodotto a linguaggio naturale: la nostra IA interpreterà la tua richiesta e troverà l'offerta più economica tra tutti i punti vendita.")

# --- BARRA LATERALE (FILTRI & RICERCA IA) ---
st.sidebar.header("🔍 Ricerca Intelligente")
richiesta_utente = st.sidebar.text_input("Cosa stai cercando?", placeholder="es. maionese calve, latte scremato...")

# Opzione per abilitare o disabilitare l'aiuto di Gemini
usa_ia = st.sidebar.toggle("Usa IA per correggere/interpretare la ricerca", value=True)

# Funzione per far interpretare la ricerca a Gemini
def ottimizza_query_con_ia(testo_grezzo):
    if not ai_client or not testo_grezzo.strip():
        return testo_grezzo.strip().lower()
    
    prompt = f"""
    L'utente sta cercando un prodotto alimentare o per la casa in un volantino di un supermercato.
    La ricerca grezza è: "{testo_grezzo}"
    
    Estrai solo le parole chiave essenziali, il nome della marca o del prodotto normalizzate e corrette da eventuali errori di battitura, in minuscolo, senza fronzoli. 
    Restituisci SOLO la stringa di ricerca pulita.
    """
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip().lower()
    except Exception:
        return testo_grezzo.strip().lower()

# --- ELABORAZIONE RICERCA ---
query_cercata = richiesta_utente
if richiesta_utente and usa_ia:
    with st.spinner("🤖 Gemini sta analizzando e ottimizzando la tua ricerca..."):
        query_cercata = ottimizza_query_con_ia(richiesta_utente)
        if query_cercata != richiesta_utente.lower():
            st.sidebar.caption(f"🔎 Ricerca interpretata come: *{query_cercata}*")

# Caricamento Località per il filtro opzionale
@st.cache_data(ttl=600)
def get_localita():
    try:
        response = supabase.table("offerte").select("localita").execute()
        return sorted(list(set([item["localita"].capitalize() for item in response.data if item.get("localita")])))
    except Exception:
        return []

localita_scelta = st.sidebar.selectbox("Filtra per Punto Vendita (Opzionale)", ["Tutte le località"] + get_localita())

# --- QUERY AL DATABASE SUPABASE ---
@st.cache_data(ttl=30)
def cerca_offerte_db(termine_ricerca, localita):
    try:
        query = supabase.table("offerte").select("*")
        
        if termine_ricerca:
            query = query.ilike("prodotto", f"%{termine_ricerca}%")
            
        if localita != "Tutte le località":
            query = query.ilike("localita", localita)
            
        # Ordina per prezzo crescente per mostrare subito il più basso
        response = query.order("prezzo", desc=False).execute()
        return response.data
    except Exception as e:
        st.error(f"Errore di connessione a Supabase: {e}")
        return []

risultati = cerca_offerte_db(query_cercata, localita_scelta)

# --- VISUALIZZAZIONE RISULTATI ---
if richiesta_utente:
    st.markdown(f"### Risultati per: *{richiesta_utente}*")
    
    if risultati:
        # Il primo elemento è il prezzo più basso in assoluto grazie all'ordinamento
        miglior_offerta = risultati[0]
        
        # Evidenziamo il prezzo più basso in un box dedicato
        st.success(f"🏆 **Miglior Prezzo Trovato!**  \n"
                   f"📦 **{miglior_offerta['prodotto'].upper()}**  \n"
                   f"💰 **€ {miglior_offerta['prezzo']:.2f}** presso **{miglior_offerta['supermercato']}** ({miglior_offerta['localita'].capitalize()})")
        
        st.markdown("---")
        st.subheader("📋 Tutte le corrispondenze ordinate per prezzo")
        
        df = pd.DataFrame(risultati)
        df_display = df[["supermercato", "localita", "marca", "prodotto", "prezzo", "unita"]].copy()
        df_display.columns = ["Supermercato", "Località", "Marca", "Prodotto", "Prezzo (€)", "Unità"]
        
        st.dataframe(
            df_display, 
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning(f"Nessun prodotto trovato per '{richiesta_utente}' (cercato come '{query_cercata}'). Prova con un altro termine o verifica che i volantini siano stati importati nel database.")
else:
    st.info("👈 Digita un prodotto nella barra laterale per iniziare la ricerca intelligente.")
