# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import re
from serpapi import GoogleSearch

# =============================================================================
# 2. CONFIGURACIÓN DE LA PÁGINA DE STREAMLIT
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
# =============================================================================
with st.sidebar:
    st.header("Configuración de la Búsqueda")

    with st.form("input_form"):
        api_key = st.text_input("Tu API Key de SerpApi", type="password")
        country_code = st.selectbox("País de Búsqueda (gl)", ['mx', 'ar', 'co', 'es', 'us', 'br'], index=0)
        language_code = st.selectbox("Idioma de Búsqueda (hl)", ['es', 'en', 'pt'], index=0)
        keywords_text = st.text_area(
            "Productos a buscar (uno por línea)",
            "Keyword 1\nKeyword 2\nKeyword 3" 
        )
        submitted = st.form_submit_button("📊 Analizar Precios")

# =============================================================================
# 4. LÓGICA PRINCIPAL DE LA APP
# =============================================================================
if submitted:
    if not api_key:
        st.error("Por favor, introduce tu API Key de SerpApi para continuar.")
    elif not keywords_text:
        st.error("Por favor, introduce al menos un producto para buscar.")
    else:
        keywords_list = [keyword.strip() for keyword in keywords_text.split('\n') if keyword.strip()]
        
        all_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, keyword in enumerate(keywords_list):
            status_text.info(f"🔎 Buscando: '{keyword}'...")
            
            try:
                params = {
                    "q": keyword,
                    "engine": "google",
                    "gl": country_code,
                    "hl": language_code,
                    "tbm": "shop",
                    "num": 10,
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
                            # CORRECCIÓN FINAL: Usamos 'product_link' en lugar de 'link'
                            'URL': item.get('product_link'), 
                            'Vendedor': item.get('source')
                        })
                else:
                    st.warning(f"No se encontraron resultados de shopping para '{keyword}'.")
            
            except Exception as e:
                st.error(f"Error al buscar '{keyword}': {e}")
            
            progress_bar.progress((i + 1) / len(keywords_list))

        status_text.success("✅ ¡Búsqueda completada! Procesando datos...")

        if all_results:
            df_results = pd.DataFrame(all_results)

            def clean_price(price_str):
                if not isinstance(price_str, str): return np.nan
                match = re.search(r'[\d,\.]+', price_str.replace(',', ''))
                return float(match.group(0)) if match else np.nan

            df_results['numeric_price'] = df_results['price'].apply(clean_price)
            df_results.dropna(subset=['numeric_price'], inplace=True)

            if not df_results.empty:
                df_results['q1'] = df_results.groupby('Keyword')['numeric_price'].transform('quantile', 0.25)
                df_results['q3'] = df_results.groupby('Keyword')['numeric_price'].transform('quantile', 0.75)
                
                conditions = [
                    (df_results['numeric_price'] < df_results['q1']),
                    (df_results['numeric_price'] > df_results['q3']),
                    (df_results['numeric_price'] >= df_results['q1']) & (df_results['numeric_price'] <= df_results['q3'])
                ]
                choices = ['bajo', 'alto', 'medio']
                df_results['price_level'] = np.select(conditions, choices, default='')
            else:
                df_results['price_level'] = ''

            desired_columns_order = ['Keyword', 'position', 'title', 'Vendedor', 'price', 'price_level', 'URL']
            df_results = df_results[desired_columns_order]

            st.header("Resultados del Análisis")
            
            st.dataframe(
                df_results,
                column_config={
                    "URL": st.column_config.LinkColumn("URL", display_text="🔗 Ver Producto"),
                    "position": st.column_config.NumberColumn("Pos.", format="%d"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            st.info(f"Total de filas generadas: {len(df_results)}")

            csv = df_results.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
               label="📥 Descargar resultados en CSV",
               data=csv,
               file_name=f"precios_relevamiento_{pd.Timestamp.now().strftime('%Y-%m-%d')}.csv",
               mime="text/csv",
            )
        else:
            st.warning("No se obtuvieron resultados para ninguna de las búsquedas.")
