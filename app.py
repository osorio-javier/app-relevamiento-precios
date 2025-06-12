# -*- coding: utf-8 -*-
# =============================================================================
# 1. IMPORTAR LIBRERÍAS
#    - Se importa streamlit, la base de la app.
#    - Se quitan las librerías específicas de Colab.
# =============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import re
from serpapi import GoogleSearch  # Usamos el cliente de SerpApi directamente

# =============================================================================
# 2. CONFIGURACIÓN DE LA PÁGINA DE STREAMLIT
#    - Esto le da un título a la pestaña del navegador y un ícono.
# =============================================================================
st.set_page_config(
    page_title="Relevamiento de Precios",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Herramienta de Relevamiento de Precios")
st.write("Esta herramienta automatiza la búsqueda de precios en Google Shopping para una lista de productos y los clasifica según su valor.")

# =============================================================================
# 3. INPUTS DEL USUARIO EN LA BARRA LATERAL (SIDEBAR)
#    - Movemos todos los inputs a una barra lateral para una interfaz más limpia.
#    - Usamos st.form para que la app no se recargue con cada cambio,
#      sino solo al presionar el botón "Analizar".
# =============================================================================
with st.sidebar:
    st.header("Configuración de la Búsqueda")

    # Usamos un formulario para agrupar los inputs
    with st.form("input_form"):
        # CAMBIO: Pedimos la API key de forma segura, no está en el código.
        api_key = st.text_input("Tu API Key de SerpApi", type="password")

        # CAMBIO: El usuario puede elegir el país de una lista.
        country_code = st.selectbox("País de Búsqueda", ['mx', 'ar', 'co', 'es', 'us'], index=0)

        # CAMBIO: Las palabras clave se ingresan en un área de texto.
        keywords_text = st.text_area(
            "Productos a buscar (uno por línea)",
            "Sennheiser HD 450BT\nSennheiser MOMENTUM 4\nSennheiser IE 200"
        )

        # El botón que inicia todo el proceso
        submitted = st.form_submit_button("📊 Analizar Precios")

# =============================================================================
# 4. LÓGICA PRINCIPAL DE LA APP
#    - Este bloque de código se ejecuta SÓLO si el usuario presionó el botón.
# =============================================================================
if submitted:
    # Verificación de que los inputs necesarios están presentes
    if not api_key:
        st.error("Por favor, introduce tu API Key de SerpApi para continuar.")
    elif not keywords_text:
        st.error("Por favor, introduce al menos un producto para buscar.")
    else:
        # Procesamos la lista de keywords desde el texto
        keywords_list = [keyword.strip() for keyword in keywords_text.split('\n') if keyword.strip()]
        
        # El resto de tu lógica, adaptada para mostrar feedback en la app
        all_results = []
        
        # Placeholder para mostrar el progreso
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, keyword in enumerate(keywords_list):
            status_text.info(f"🔎 Buscando: '{keyword}'...")
            
            try:
                params = {
                    "q": keyword,
                    "engine": "google",
                    "gl": country_code,
                    "hl": "es-419",
                    "tbm": "shop",
                    "api_key": api_key
                }
                search = GoogleSearch(params)
                result = search.get_dict()

                shopping_results = result.get('shopping_results', [])
                if shopping_results:
                    for item in shopping_results:
                        all_results.append({
                            'Keyword': keyword,
                            'position': item.get('position'),
                            'title': item.get('title'),
                            'price': item.get('price'),
                            'URL': item.get('link')
                        })
                else:
                    st.warning(f"No se encontraron resultados de shopping para '{keyword}'.")
            
            except Exception as e:
                st.error(f"Error al buscar '{keyword}': {e}")
            
            # Actualizamos la barra de progreso
            progress_bar.progress((i + 1) / len(keywords_list))

        status_text.success("✅ ¡Búsqueda completada! Procesando datos...")

        if all_results:
            df_results = pd.DataFrame(all_results)

            # --- LÓGICA DE LIMPIEZA Y ANÁLISIS (Tu código original) ---
            def clean_price(price_str):
                if not isinstance(price_str, str): return np.nan
                match = re.search(r'[\d,\.]+', price_str.replace(',', ''))
                return float(match.group(0)) if match else np.nan

            df_results['numeric_price'] = df_results['price'].apply(clean_price)
            df_results.dropna(subset=['numeric_price'], inplace=True)

            df_results['q1'] = df_results.groupby('Keyword')['numeric_price'].transform('quantile', 0.25)
            df_results['q3'] = df_results.groupby('Keyword')['numeric_price'].transform('quantile', 0.75)
            
            conditions = [
                (df_results['numeric_price'] < df_results['q1']),
                (df_results['numeric_price'] > df_results['q3']),
                (df_results['numeric_price'] >= df_results['q1']) & (df_results['numeric_price'] <= df_results['q3'])
            ]
            choices = ['bajo', 'alto', 'medio']
            df_results['price_level'] = np.select(conditions, choices, default='')

            desired_columns_order = ['Keyword', 'position', 'title', 'price', 'price_level', 'URL']
            df_results = df_results[desired_columns_order]

            # --- MOSTRAR RESULTADOS EN LA APP ---
            st.header("Resultados del Análisis")
            st.dataframe(df_results)
            
            st.info(f"Total de filas generadas: {len(df_results)}")

            # --- BOTÓN DE DESCARGA (reemplaza a files.download) ---
            csv = df_results.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
               label="📥 Descargar resultados en CSV",
               data=csv,
               file_name=f"precios_relevamiento_{pd.Timestamp.now().strftime('%Y-%m-%d')}.csv",
               mime="text/csv",
            )
        else:
            st.warning("No se obtuvieron resultados para ninguna de las búsquedas.")
