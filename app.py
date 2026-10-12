import streamlit as st
from supabase import create_client, Client

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Cerca Volantini & Offerte",
    page_icon="🛒",
    layout="centered"
)

# --- CONNESSIONE A SUPABASE ---
# Streamlit permette di memorizzare le chiavi in modo sicuro nei "Secrets"
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- INTERFACCIA GRAFICA ---
st.title("🛒 Trova Prezzi nei Volantini")
st.write("Cerca un prodotto per scoprire in quale supermercato costa meno!")

# Casella di ricerca
query = st.text_input("Cosa stai cercando?", placeholder="es. latte, caffè, pasta, olio...")

if query:
    with st.spinner("Cerco tra le offerte..."):
        try:
            # Esegue la query su Supabase
            response = (
                supabase.table("offerte")
                .select("supermercato, prodotto, prezzo, unita, data_inserimento")
                .ilike("prodotto", f"%{query.strip().lower()}%")
                .order("prezzo", desc=False)
                .execute()
            )
            
            risultati = response.data
            
            if not risultati:
                st.warning(f"Nessun risultato trovato per '{query}'.")
            else:
                st.success(f"Trovate {len(risultati)} offerte!")
                
                # Mostra i risultati in una tabella pulita e ordinata
                for r in risultati:
                    superm = r.get("supermercato", "").upper()
                    prod = r.get("prodotto", "").title()
                    prezzo = r.get("prezzo", 0.0)
                    unita = r.get("unita", "€")
                    
                    # Creiamo un box grafico per ogni offerta
                    with st.container():
                        col1, col2, col3 = st.columns([2, 4, 2])
                        with col1:
                            st.markdown(f"**🏪 {superm}**")
                        with col2:
                            st.markdown(f"{prod}")
                        with col3:
                            st.markdown(f"### `{prezzo:.2f} {unita}`")
                        st.divider()

        except Exception as e:
                st.error(f"Errore durante la connessione al database: {e}")
