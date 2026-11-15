import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="Rastreador FENBAS",
    page_icon="🏊‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stButton > button {
        width: 100%;
        height: 3.2rem;
        font-size: 1.1rem;
        font-weight: 700;
        border-radius: 12px;
        margin-top: 0.4rem;
    }
    .stDownloadButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 12px;
    }
    .result-card {
        background-color: #f0f4f8;
        border-left: 5px solid #0077b6;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
        color: #102a43;
        font-family: sans-serif;
    }
    .result-title {
        font-weight: 700;
        font-size: 0.95rem;
        color: #005f99;
        margin-bottom: 4px;
    }
    .result-detail {
        font-family: monospace;
        font-size: 0.88rem;
        white-space: pre-wrap;
        word-break: break-word;
        background: #ffffff;
        padding: 8px;
        border-radius: 6px;
        border: 1px solid #d9e2ec;
    }
    @media (prefers-color-scheme: dark) {
        .result-card {
            background-color: #1e293b;
            border-left: 5px solid #38bdf8;
            color: #f8fafc;
        }
        .result-title {
            color: #38bdf8;
        }
        .result-detail {
            background: #0f172a;
            border: 1px solid #334155;
            color: #e2e8f0;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("### 🏊‍♂️ Rastreador FENBAS")
st.caption("Consulta rápida de tiempos y series en vivo desde el natatorio.")

with st.form("form_busqueda"):
    nombre_nadadora = st.text_input(
        "Nombre o Apellido (ej: Lena Marino o solo Marino)",
        value="Lena Marino",
        placeholder="Ej: LENA MARINO"
    )
    
    url_torneo = st.text_input(
        "URL del Torneo actual (index.htm)",
        value="https://fenbas.com.ar/resultados_online/156/index.htm",
        help="¡Atención! Verificá que sea la URL del torneo que se está nadando hoy."
    )
        
    buscar_btn = st.form_submit_button("🔍 BUSCAR RESULTADOS", type="primary")

def revisar_prueba(args):
    url_prueba, palabras_clave, headers = args
    resultados_prueba = []
    try:
        res_prueba = requests.get(url_prueba, headers=headers, timeout=8)
        res_prueba.encoding = res_prueba.apparent_encoding or 'latin-1'
        soup_prueba = BeautifulSoup(res_prueba.text, 'html.parser')
        
        titulo_prueba = soup_prueba.find('title')
        nombre_prueba = titulo_prueba.text.strip() if titulo_prueba else "Prueba"
        
        texto_pagina = soup_prueba.get_text()
        
        # Verificamos si TODas las palabras clave están presentes en la página
        texto_upper = texto_pagina.upper()
        if all(p in texto_upper for p in palabras_clave):
            lineas = texto_pagina.split('\n')
            for linea in lineas:
                linea_upper = linea.upper()
                # Si la línea contiene todas las palabras (ej: "MARINO", "LENA")
                if all(p in linea_upper for p in palabras_clave):
                    resultados_prueba.append({
                        'Prueba': nombre_prueba,
                        'Detalle / Resultado': linea.strip(),
                        'Enlace': url_prueba
                    })
    except Exception:
        pass
    return resultados_prueba

@st.cache_data(ttl=60, show_spinner=False)
def obtener_resultados_fenbas(url_index, palabras_clave):
    base_url = url_index.rsplit('/', 1)[0] + '/'
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url_index, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding or 'latin-1'
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"No se pudo conectar con FENBAS: {e}", []
        
    links = soup.find_all('a', href=True)
    hallazgos = []
    
    pruebas_links = list(dict.fromkeys([
        base_url + link['href'] 
        for link in links 
        if link['href'].lower().endswith('.htm') 
        and 'index' not in link['href'].lower() 
        and 'team' not in link['href'].lower() 
        and 'relays' not in link['href'].lower()
    ]))
    
    tareas = [(url, palabras_clave, headers) for url in pruebas_links]
    with ThreadPoolExecutor(max_workers=12) as executor:
        for res in executor.map(revisar_prueba, tareas):
            hallazgos.extend(res)
            
    // Eliminar duplicados exactos si la línea aparece repetida
    hallazgos_unicos = []
    vistos = set()
    for h in hallazgos:
        clave_unica = (h['Prueba'], h['Detalle / Resultado'])
        if clave_unica not in vistos:
            vistos.add(clave_unica)
            hallazgos_unicos.append(h)
            
    return None, hallazgos_unicos

if buscar_btn:
    if not url_torneo or not nombre_nadadora.strip():
        st.warning("Completá la URL y el nombre.")
    else:
        # Dividir el nombre en palabras clave individuales (ej: ["LENA", "MARINO", "MENNA"])
        palabras = [p.upper() for p in nombre_nadadora.strip().split() if len(p) > 1]
        
        if not palabras:
            st.warning("Ingresá un nombre válido.")
        else:
            with st.spinner(f"Buscando a {nombre_nadadora.upper()}..."):
                error, resultados = obtener_resultados_fenbas(url_torneo.strip(), palabras)
                
            if error:
                st.error(error)
            elif not resultados:
                st.info(f"No se encontraron registros para '{nombre_nadadora}' en este torneo.\n\n💡 Consejo: Asegurate de que la URL corresponda al torneo actual y probá buscando solo por el apellido (ej: 'Marino' o 'Menna').")
            else:
                st.success(f"✅ ¡{len(resultados)} resultado(s) encontrado(s)!")
                
                for item in resultados:
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="result-title">{item['Prueba']}</div>
                        <div class="result-detail">{item['Detalle / Resultado']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                df = pd.DataFrame(resultados)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Resultados')
                
                st.download_button(
                    label="📥 Descargar planilla Excel (.xlsx)",
                    data=output.getvalue(),
                    file_name=f"FENBAS_{nombre_nadadora.strip().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
