import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import re
import numpy as np
from datetime import datetime

# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Relevamiento de Precios",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 App de Relevamiento de Precios")
st.write("Esta herramienta automatiza la búsqueda de precios para una lista de productos en Google Shopping.")

# --- DICCIONARIOS PARA PAÍS E IDIOMA ---
# Mapeo de nombres de países a sus códigos 'gl' de Google
COUNTRY_MAP = {
    "Argentina": "ar",
    "España": "es",
    "México": "mx",
    "Estados Unidos": "us",
    "Colombia": "co",
    "Chile": "cl",
    "Perú": "pe",
    "Brasil": "br"
}

# Mapeo de nombres de idiomas a sus códigos 'hl' de Google
LANGUAGE_MAP = {
    "Español": "es",
    "Inglés": "en",
    "Portugués": "pt"
}


# --- Barra Lateral (Sidebar) para Entradas del Usuario ---
with st.sidebar:
    st.header("Configuración de Búsqueda")
    
    # Campo para la API Key de SerpApi
    api_key = st.text_input("Ingresa tu API Key de SerpApi", type="password")

    # --- NUEVOS CAMPOS: PAÍS E IDIOMA ---
    country_name = st.selectbox("Selecciona el País", options=list(COUNTRY_MAP.keys()))
    language_name = st.selectbox("Selecciona el Idioma", options=list(LANGUAGE_MAP.keys()))
    
    # Obtener los códigos correspondientes a la selección del usuario
    country_code = COUNTRY_MAP[country_name]
    language_code = LANGUAGE_MAP[language_name]
    
    # Campo para la lista de productos
    st.subheader("Lista de Productos")
    products_input = st.text_area("Pega aquí tu lista de productos (uno por línea)", height=250)
    
    # Botón para iniciar el análisis
    submit_button = st.button("Buscar Precios")

# --- FUNCIÓN DE BÚSQUEDA ACTUALIZADA ---
def search_google_shopping(query, api_key, gl_code, hl_code):
    """
    Realiza una búsqueda para un producto en Google Shopping usando SerpApi,
    con parámetros de país (gl) e idioma (hl).
    """
    if not api_key:
        st.error("Por favor, ingresa tu API Key de SerpApi en la barra lateral.")
        return None
        
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "gl": gl_code,  # Código del país
        "hl": hl_code   # Código del idioma
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("shopping_results", [])
    except Exception as e:
        st.error(f"Ocurrió un error con la API para el producto '{query}': {e}")
        return []

# --- Función para limpiar y convertir precios a formato numérico ---
def clean_price(price_str):
    """
    Limpia una cadena de texto de precio, eliminando símbolos de moneda y
    convirtiéndola a un número flotante. Maneja formatos como '$ 1.499,90'.
    """
    if not isinstance(price_str, str):
        return np.nan

    try:
        cleaned_str = re.sub(r'[^\d,.]', '', price_str)
        
        # Detectar si el último separador es una coma (formato latino/europeo)
        if ',' in cleaned_str and '.' in cleaned_str:
            if cleaned_str.rfind(',') > cleaned_str.rfind('.'):
                # Formato 1.234,56 -> quitar puntos, cambiar coma por punto
                cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
            else:
                # Formato 1,234.56 -> quitar comas
                cleaned_str = cleaned_str.replace(',', '')
        else:
             # Si solo hay comas, asumimos que es decimal
            cleaned_str = cleaned_str.replace(',', '.')

        return float(cleaned_str)

    except (ValueError, TypeError):
        return np.nan

# --- Lógica Principal de la Aplicación ---
if submit_button and products_input:
    product_list = [product.strip() for product in products_input.split('\n') if product.strip()]
    
    if not product_list:
        st.warning("Por favor, ingresa al menos un producto.")
    else:
        all_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, product in enumerate(product_list):
            status_text.text(f"Buscando '{product}' en {country_name} ({language_name})...")
            # --- LLAMADA A LA FUNCIÓN ACTUALIZADA ---
            results = search_google_shopping(product, api_key, country_code, language_code)
            if results:
                for res in results:
                    res['product_searched'] = product
                all_results.extend(results)
            progress_bar.progress((i + 1) / len(product_list))
        
        status_text.success("¡Búsqueda completada!")

        if all_results:
            df_results = pd.DataFrame(all_results)
            
            df_columns = ['product_searched', 'title', 'price', 'source', 'link']
            # Asegurarse de que todas las columnas existan, rellenando con None si no
            for col in df_columns:
                if col not in df_results.columns:
                    df_results[col] = None

            df_results = df_results[df_columns]
            df_results.rename(columns={
                'product_searched': 'Producto Buscado',
                'title': 'Título del Producto',
                'price': 'Precio Original',
                'source': 'Vendedor',
                'link': 'Enlace'
            }, inplace=True)

            df_results['Precio Numérico'] = df_results['Precio Original'].apply(clean_price)
            df_results.dropna(subset=['Precio Numérico'], inplace=True)

            st.subheader("Resultados del Relevamiento")
            st.dataframe(df_results)

            csv = df_results.to_csv(index=False).encode('utf-8')
            now = datetime.now().strftime("%Y-%m-%d_%H-%M")
            file_name = f"relevamiento_precios_{country_code}_{now}.csv"
            
            st.download_button(
               label="Descargar resultados como CSV",
               data=csv,
               file_name=file_name,
               mime="text/csv",
            )
        else:
            st.info("No se encontraron resultados para los productos listados.")

elif submit_button:
    st.warning("Por favor, ingresa una lista de productos.")
