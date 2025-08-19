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

# --- Barra Lateral (Sidebar) para Entradas del Usuario ---
with st.sidebar:
    st.header("Configuración")
    
    # Campo para la API Key de SerpApi
    api_key = st.text_input("Ingresa tu API Key de SerpApi", type="password")
    
    # Campo para la lista de productos
    st.subheader("Lista de Productos")
    products_input = st.text_area("Pega aquí tu lista de productos (uno por línea)", height=250)
    
    # Botón para iniciar el análisis
    submit_button = st.button("Buscar Precios")

# --- Función para buscar en Google Shopping ---
def search_google_shopping(query, api_key):
    """
    Realiza una búsqueda para un producto en Google Shopping usando SerpApi.
    """
    if not api_key:
        st.error("Por favor, ingresa tu API Key de SerpApi en la barra lateral.")
        return None
        
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "location": "Buenos Aires, Buenos Aires, Argentina" # Puedes ajustar la ubicación si es necesario
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("shopping_results", [])
    except Exception as e:
        st.error(f"Ocurrió un error con la API para el producto '{query}': {e}")
        return []

# --- Función para limpiar y convertir precios a formato numérico ---
# ESTA ES LA FUNCIÓN CORREGIDA
def clean_price(price_str):
    """
    Limpia una cadena de texto de precio, eliminando símbolos de moneda y
    convirtiéndola a un número flotante. Maneja formatos como '$ 1.499,90'.
    """
    # Si el valor no es una cadena de texto (ej. ya es un número o está vacío), devolver NaN.
    if not isinstance(price_str, str):
        return np.nan

    try:
        # 1. Quitar cualquier cosa que no sea un dígito, una coma o un punto.
        #    Esto elimina símbolos de moneda como '$', 'ARS', etc. y espacios.
        cleaned_str = re.sub(r'[^\d,.]', '', price_str)
        
        # 2. Asumimos el formato de Argentina/Latinoamérica donde '.' es separador de miles y ',' es decimal.
        #    Primero, quitamos los puntos (separadores de miles).
        cleaned_str = cleaned_str.replace('.', '')
        
        #    Segundo, reemplazamos la coma (separador decimal) por un punto.
        cleaned_str = cleaned_str.replace(',', '.')
        
        # 3. Convertir la cadena limpia a un número flotante.
        return float(cleaned_str)

    except (ValueError, TypeError):
        # Si después de la limpieza algo falla en la conversión, devolver NaN.
        # Esto hace la función muy segura ante formatos inesperados.
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
            status_text.text(f"Buscando: {product}...")
            results = search_google_shopping(product, api_key)
            if results:
                for res in results:
                    res['product_searched'] = product # Añadir el producto buscado a cada resultado
                all_results.extend(results)
            progress_bar.progress((i + 1) / len(product_list))
        
        status_text.success("¡Búsqueda completada!")

        if all_results:
            df_results = pd.DataFrame(all_results)
            
            # --- Procesamiento y Limpieza del DataFrame ---
            # Seleccionar y renombrar columnas relevantes
            df_results = df_results[['product_searched', 'title', 'price', 'source', 'link']]
            df_results.rename(columns={
                'product_searched': 'Producto Buscado',
                'title': 'Título del Producto',
                'price': 'Precio',
                'source': 'Vendedor',
                'link': 'Enlace'
            }, inplace=True)

            # Aplicar la función de limpieza de precios
            df_results['Precio Numérico'] = df_results['Precio'].apply(clean_price)
            
            # Eliminar filas donde no se pudo obtener un precio numérico
            df_results.dropna(subset=['Precio Numérico'], inplace=True)

            # --- Mostrar Resultados ---
            st.subheader("Resultados del Relevamiento")
            st.dataframe(df_results)

            # --- Opción para Descargar ---
            csv = df_results.to_csv(index=False).encode('utf-8')
            
            # Generar nombre de archivo con fecha y hora
            now = datetime.now().strftime("%Y-%m-%d_%H-%M")
            file_name = f"relevamiento_precios_{now}.csv"
            
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
