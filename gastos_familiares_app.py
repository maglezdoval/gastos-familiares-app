import streamlit as st
import pandas as pd
import calendar
import traceback
import re
from collections import Counter

# --- Diccionario Global para Almacenar Conocimiento de Categorías ---
category_knowledge = {
    "keyword_map": {},
    "amount_map": {}
}

# --- Funciones Auxiliares ---

# Mapeo manual de meses
meses_es = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}
# *** FUNCIÓN CORREGIDA ***
def obtener_nombre_mes(numero_mes):
    """Convierte número de mes a nombre abreviado."""
    try:
        # Intenta convertir a entero y buscar en el diccionario
        return meses_es.get(int(numero_mes), str(numero_mes))
    except (ValueError, TypeError):
        # Si falla la conversión o la búsqueda, devuelve como string
        return str(numero_mes)

@st.cache_data
def convert_df_to_csv(df_to_convert):
    """Prepara el DataFrame para descarga en formato CSV original."""
    df_download = df_to_convert.copy()
    if 'importe' in df_download.columns:
        df_download.rename(columns={'importe': 'IMPORTE'}, inplace=True)
    if 'IMPORTE' in df_download.columns:
        df_download['IMPORTE'] = pd.to_numeric(df_download['IMPORTE'], errors='coerce')
        df_download['IMPORTE'] = df_download['IMPORTE'].map('{:.2f}'.format).str.replace('.', ',', regex=False)
        df_download['IMPORTE'].fillna('0,00', inplace=True)
    df_download = df_download.drop(columns=['original_index', 'temp_id'], errors='ignore')
    return df_download.to_csv(index=False, sep=';', decimal=',').encode('utf-8')

def clean_text(text):
    """Limpia el texto del concepto para extraer keywords."""
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'\b\d{4,}\b', '', text)
    text = re.sub(r'\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Lista de palabras a ignorar (definida globalmente para usarla en learn y suggest)
keywords_to_ignore = {
    'pago', 'movil', 'en', 'compra', 'tarjeta', 'tarj', 'internet', 'comision', 'recibo',
    'favor', 'de', 'la', 'el', 'los', 'las', 'a', 'con', 'sl', 'sa', 'sau', 's l',
    'concepto', 'nº', 'ref', 'mandato', 'cuenta', 'gastos', 'varios', 'madrid', 'huelva',
    'rozas', 'espanola', 'europe', 'fecha', 'num', 'enero', 'febrero', 'marzo', 'abril',
    'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
    'transferencia', 'trf', 'bizum', 'liquidacin', 'contrato', 'impuesto',
    'cotizacion', 'tgss', 'iban', 'swift', 'com', 'www', 'http', 'https', 'cliente',
    'importe', 'saldo', 'valor', 'atm', 'reintegro', 'oficina', 'suc', 'sr', 'sra', 'dna',
    'bill', 'pending', 'uber', 'comercial', 'petroleo', 'obo', 'inv', 'for', 'sueldo',
    'salar', 'nombre', 'miguel', 'angel', 'gonzalez', 'doval', 'alicia', 'jimenez', 'corpa',
    'ordenante', 'beneficiario'
}

def learn_categories(df, concepto_col, cat_col, subcat_col, importe_col, placeholder_cat, placeholder_sub):
    """Aprende patrones de categorización del DataFrame."""
    global category_knowledge, keywords_to_ignore # Asegurar que usa la global
    keyword_cat_counter = {}
    amount_cat_counter = {}
    df_categorized = df[(df[cat_col] != placeholder_cat) & (df[subcat_col] != placeholder_sub)].copy()
    if df_categorized.empty: return
    df_categorized['cleaned_concepto'] = df_categorized[concepto_col].apply(clean_text)
    for _, row in df_categorized.iterrows():
        cat = row[cat_col]; subcat = row[subcat_col]; importe_val = row[importe_col]
        amount_bin = int(round(importe_val / 10) * 10) if pd.notna(importe_val) and isinstance(importe_val, (int, float)) else 0
        words = set(row['cleaned_concepto'].split()) - keywords_to_ignore
        for word in words:
            if len(word) < 4: continue
            keyword_cat_counter.setdefault(word, Counter())[(cat, subcat)] += 1
            amount_cat_counter.setdefault((word, amount_bin), Counter())[(cat, subcat)] += 1
    category_knowledge["keyword_map"] = {word: counter.most_common(1)[0][0] for word, counter in keyword_cat_counter.items() if counter}
    category_knowledge["amount_map"] = {key: counter.most_common(1)[0][0] for key, counter in amount_cat_counter.items() if counter}
    st.sidebar.info(f"Aprendizaje: {len(category_knowledge['keyword_map'])} keywords.")

def suggest_category(row, concepto_col, importe_col, cat_col, subcat_col):
    """Sugiere categoría y subcategoría para una fila."""
    global category_knowledge, keywords_to_ignore # Asegurar que usa la global
    concepto = row[concepto_col]; importe = row[importe_col]; concepto_lower = str(concepto).lower(); current_subcat_lower = str(row[subcat_col]).lower()
    # --- 1. Reglas Explícitas (AJUSTAR) ---
    if "mercadona" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "carrefour" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "dia supermercado" in concepto_lower or "dia s.a" in concepto_lower : return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "lidl" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "ahorramas" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "supercor" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "alcampo" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO')
    if "el corte ingles" in concepto_lower: return ('COMPRAS', 'EL CORTE INGLES')
    if "amazon" in concepto_lower or "amzn" in concepto_lower: return ('COMPRAS', 'AMAZON')
    if "glovo" in concepto_lower: return ('ALIMENTACIÓN', 'ONLINE')
    if "apple.com/bill" in concepto_lower: return ('SUSCRIPCIONES', 'APPLE ONE')
    if "netflix.com" in concepto_lower: return ('SUSCRIPCIONES', 'NETFLIX')
    if "spotify" in concepto_lower: return ('SUSCRIPCIONES', 'SPOTIFY')
    if "hbo" in concepto_lower or "max help.max.co" in concepto_lower: return ('SUSCRIPCIONES', 'HBO MAX')
    if "disney plus" in concepto_lower: return ('SUSCRIPCIONES', 'DISNEY')
    if "movistar" in concepto_lower or "telefonica" in concepto_lower: return ('SUSCRIPCIONES', 'MOVISTAR')
    if "iberdrola" in concepto_lower: return ('SUMINISTROS', 'ELECTRICIDAD')
    if "endesax.com" in concepto_lower: return ('SUMINISTROS', 'ELECTRICIDAD')
    if "naturgy" in concepto_lower: return ('SUMINISTROS', 'GAS')
    if "canal de isabel ii" in concepto_lower: return ('SUMINISTROS', 'AGUA')
    if "podo" in concepto_lower or "geo alternativa" in concepto_lower : return ('SUMINISTROS', 'ELECTRICIDAD/GAS')
    if ("cepsa" in concepto_lower or "repsol" in concepto_lower or "galp" in concepto_lower or "shell" in concepto_lower) and ("carburante" in current_subcat_lower or "gasolin" in concepto_lower): return ('COCHE', 'CARBURANTE')
    if "farmacia" in concepto_lower or "fcia." in concepto_lower: return ('SALUD', 'FARMACIA')
    if "colegio punta galea" in concepto_lower: return ('COLEGIO', 'MENSUALIDAD')
    if "paypal *uber" in concepto_lower or "cabify" in concepto_lower: return ('TRANSPORTE', 'TAXI')
    if "renfe" in concepto_lower or "emt " in concepto_lower or "metro de madrid" in concepto_lower: return ('TRANSPORTE', 'PUBLICO')
    if "autopista" in concepto_lower or "peaje" in concepto_lower: return ('COCHE', 'PEAJE')
    if "parking" in concepto_lower or "aparcamiento" in concepto_lower or "easypark" in concepto_lower: return ('COCHE', 'PARKING')
    if "alquiler castillo" in concepto_lower: return ('ALQUILER', 'CASTILLO DE AREVALO')
    if "itevelesa" in concepto_lower: return ('COCHE', 'ITV')
    if "decathlon" in concepto_lower: return ('ROPA', 'DEPORTE')
    if "leroy merlin" in concepto_lower or " leroymerlin" in concepto_lower: return ('VARIOS HOGAR', 'MANTENIMIENTO')
    if "ikea" in concepto_lower: return ('VARIOS HOGAR', 'MUEBLES')
    if "alexso" in concepto_lower: return ('CUIDADO PERSONAL', 'PELUQUERÍA')
    if "duet sports" in concepto_lower or "ute padel" in concepto_lower: return ('ACTIVIDADES', 'PADEL')
    # ... Añadir más reglas ...

    # --- 2. Usar Conocimiento Aprendido ---
    cleaned_concepto = clean_text(concepto); words = set(cleaned_concepto.split()) - keywords_to_ignore
    amount_bin = int(round(importe / 10) * 10) if pd.notna(importe) and isinstance(importe, (int, float)) else 0
    best_suggestion = None
    for word in words:
        if len(word) < 4: continue
        key_amount = (word, amount_bin);
        if key_amount in category_knowledge["amount_map"]: best_suggestion = category_knowledge["amount_map"][key_amount]; break
    if best_suggestion is None:
        for word in words:
             if len(word) < 4: continue
             if word in category_knowledge["keyword_map"]: best_suggestion = category_knowledge["keyword_map"][word]; break
    return best_suggestion if best_suggestion else (None, None)

# --- Función Principal Main ---
def main():
    st.set_page_config(layout="wide")
    st.title('Análisis Financiero Personal y Categorización')

    if 'edited_df' not in st.session_state: st.session_state.edited_df = None
    if 'data_processed' not in st.session_state: st.session_state.data_processed = False
    if 'last_uploaded_filename' not in st.session_state: st.session_state.last_uploaded_filename = None

    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"], key="file_uploader")

    if uploaded_file is not None:
        if 'last_uploaded_filename' not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
             st.session_state.edited_df = None; st.session_state.data_processed = False; st.session_state.last_uploaded_filename = uploaded_file.name; convert_df_to_csv.clear()
        if st.session_state.edited_df is None:
            try:
                df_load = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', dtype={'AÑO': str, 'MES': str, 'DIA': str})
                st.session_state.edited_df = df_load.copy(); st.session_state.data_processed = False
                st.success(f"Archivo '{uploaded_file.name}' cargado. Procesando..."); st.experimental_rerun()
            except Exception as e: st.error(f"Error al cargar: {e}"); st.session_state.edited_df = None; return
    elif st.session_state.edited_df is None: st.info("Sube tu archivo CSV."); return

    if st.session_state.edited_df is not None and not st.session_state.data_processed:
        df_processing = st.session_state.edited_df.copy()
        try:
            df_processing.columns = df_processing.columns.str.strip()
            imp_orig = 'IMPORTE'; tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'AÑO'; mes = 'MES'; dia = 'DIA'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'
            imp_calc = 'importe'
            req_cols = [imp_orig, tipo, cat, subcat, ano, mes, dia, desc, com, cta];
            missing = [c for c in req_cols if c not in df_processing.columns]; assert not missing, f"Faltan columnas: {', '.join(missing)}"
            df_processing.rename(columns={imp_orig: imp_calc}, inplace=True)
            df_processing[imp_calc] = pd.to_numeric(df_processing[imp_calc].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            df_processing[ano]=df_processing[ano].astype(str); df_processing[mes]=df_processing[mes].astype(str).str.zfill(2); df_processing[dia]=df_processing[dia].astype(str).str.zfill(2)
            df_processing['Fecha'] = pd.to_datetime( df_processing[ano] + '-' + df_processing[mes] + '-' + df_processing[dia], format='%Y-%m-%d', errors='coerce')
            n_inv = df_processing['Fecha'].isnull().sum();
            if n_inv > 0: st.warning(f"{n_inv} filas con fechas inválidas eliminadas.")
            df_processing.dropna(subset=['Fecha'], inplace=True)
            df_processing['Año'] = df_processing['Fecha'].dt.year.astype(int); df_processing['Mes'] = df_processing['Fecha'].dt.month.astype(int)
            ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'
            fill_cols = {cat: ph_cat, subcat: ph_sub, com: '', cta: 'SIN CUENTA', tipo: 'SIN TIPO'}
            for c, ph in fill_cols.items():
                 if c in df_processing.columns:
                       df_processing[c] = df_processing[c].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], pd.NA).fillna(ph)
                       if ph == '': df_processing[c] = df_processing[c].replace('', ph) # Solo reemplaza '' si el placeholder es ''
            learn_categories(df_processing, desc, cat, subcat, imp_calc, ph_cat, ph_sub)
            st.session_state.edited_df = df_processing.copy()
            st.session_state.data_processed = True
            st.sidebar.success("Datos procesados.")
            st.experimental_rerun()
        except Exception as e_proc: st.error(f"Error procesando: {e_proc}"); st.code(traceback.format_exc()); st.session_state.edited_df = None; st.session_state.data_processed = False; return

    # --- Mostrar Contenido Principal ---
    if st.session_state.get('data_processed', False) and st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy()
        tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'Año'; mes = 'Mes'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'; imp_calc = 'importe'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

        uncategorized_mask = (df[cat] == ph_cat); num_uncategorized = df[uncategorized_mask].shape[0]
        if num_uncategorized > 0: st.sidebar.warning(f"⚠️ {num_uncategorized} transacciones sin CATEGORÍA.")

        tab_gastos, tab_pl, tab_categorizar = st.tabs(["📊 Gastos", "📈 P&L EVO", "🏷️ Categorizar"])

        # --- PESTAÑA 1: Gastos ---
        with tab_gastos:
             st.header("Análisis Detallado de Gastos")
             val_gasto = ["GASTO"]; df_g_tab = df[df[tipo].isin(val_gasto)].copy()
             if not df_g_tab.empty:
                 st.sidebar.header("Filtros Gastos"); años_g = sorted([int(a) for a in df_g_tab[ano].dropna().unique()]); año_g_s = st.sidebar.selectbox("Año (G):", años_g, key='sel_a_g')
                 df_g_a = df_g_tab[df_g_tab[ano] == año_g_s]
                 if not df_g_a.empty:
                      ctas_g = sorted(df_g_a[cta].unique()); ctas_g_s = st.sidebar.multiselect("Cuentas (G):", options=ctas_g, default=ctas_g, key='sel_cta_g')
                      if ctas_g_s:
                           df_g_f = df_g_a[df_g_a[cta].isin(ctas_g_s)].copy()
                           if not df_g_f.empty:
                                st.subheader(f"Resumen ({año_g_s} - {', '.join(ctas_g_s)})")
                                try:
                                     piv_g = df_g_f.pivot_table(values=imp_calc, index=cat, columns=mes, aggfunc='sum', fill_value=0, margins=True, margins_name='Total')
                                     fmt = '{:,.0f} €'; sty = [ {'selector': 'th.col_heading, th.row_heading', 'props': [('background-color', '#6c757d'), ('color', 'white'), ('font-weight', 'bold')]}, {'selector': 'th.col_heading', 'props': [('text-align', 'center')]}, {'selector': 'th.row_heading', 'props': [('text-align', 'left')]}, {'selector': 'tr:last-child td, td:last-child', 'props': [('font-weight', 'bold'), ('background-color', '#f8f9fa')]} ]
                                     st.dataframe(piv_g.style.format(fmt).set_table_styles(sty), use_container_width=True)
                                except Exception as e: st.error(f"Error pivote G: {e}")
                                st.subheader("Detalle"); cats_f = sorted(df_g_f[cat].unique()); mes_f = sorted(df_g_f[mes].unique())
                                if cats_f and mes_f:
                                     c1,c2=st.columns(2);
                                     with c1: cat_s=st.selectbox("Cat:", cats_f, key='cat_det_g');
                                     with c2: mes_s=st.selectbox("Mes:", mes_f, key='mes_det_g')
                                     df_det=df_g_f[(df_g_f[cat]==cat_s)&(df_g_f[mes]==mes_s)]
                                     if not df_det.empty:
                                          st.write(f"**Detalle: {cat_s}, Mes {mes_s}, Año {año_g_s}**")
                                          det=df_det.groupby([subcat, desc, com, cta, 'Fecha'])[imp_calc].sum().reset_index().sort_values(by=imp_calc, ascending=True)
                                          det['Fecha']=pd.to_datetime(det['Fecha']).dt.strftime('%Y-%m-%d'); det[imp_calc]=det[imp_calc].map('{:,.2f} €'.format)
                                          st.dataframe(det, use_container_width=True, height=300)
                                     else: st.info("No hay detalle.")
                                else: st.info("No hay datos para detalle.")
                           else: st.info("No hay gastos para filtro.")
                      else: st.warning("Seleccione cuentas (G).")
                 else: st.info(f"No hay gastos para {año_g_s}.")
             else: st.info("No hay GASTOS.")

        # --- PESTAÑA 2: P&L ---
        with tab_pl:
             st.header("Análisis P&L - Cuenta Familiar (EVO)"); df_evo = df[df[cta] == 'EVO'].copy()
             if not df_evo.empty:
                 st.sidebar.header("Filtro P&L"); años_pl = sorted([int(a) for a in df_evo[ano].dropna().unique()]); año_pl_s = st.sidebar.selectbox("Año (P&L):", años_pl, key='sel_a_pl')
                 df_evo_a = df_evo[df_evo[ano] == año_pl_s]
                 if not df_evo_a.empty:
                      tip_in = ['TRASPASO', 'INGRESO', 'REEMBOLSO']; df_i = df_evo_a[df_evo_a[tipo].isin(tip_in)]; ing_m = df_i.groupby(mes)[imp_calc].sum()
                      tip_eg = ['GASTO', 'RECIBO']; df_e = df_evo_a[df_evo_a[tipo].isin(tip_eg)]; egr_m = df_e.groupby(mes)[imp_calc].sum().abs()
                      df_pnl = pd.DataFrame({'Ingresos': ing_m, 'Egresos': egr_m}).fillna(0); df_pnl['Resultado'] = df_pnl['Ingresos'] - df_pnl['Egresos']
                      tot_pl = df_pnl.sum(); tot_pl.name = 'Total'; df_pnl = pd.concat([df_pnl, tot_pl.to_frame().T]); df_pnl.index = df_pnl.index.map(obtener_nombre_mes)
                      fmt = '{:,.2f} €'; df_pnl_f = df_pnl.style.format(fmt).applymap(lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else 'color: black'), subset=['Resultado']).set_properties(**{'text-align': 'right'})
                      st.subheader(f"Tabla P&L ({año_pl_s}) - EVO"); st.dataframe(df_pnl_f, use_container_width=True)
                      df_pnl_c = df_pnl.drop('Total');
                      try: m_map={v:k for k,v in meses_es.items()}; df_pnl_c.index=df_pnl_c.index.map(m_map.get); df_pnl_c=df_pnl_c.sort_index()
                      except: pass
                      st.subheader(f"Gráfico P&L ({año_pl_s}) - EVO"); st.line_chart(df_pnl_c[['Ingresos', 'Egresos']])
                 else: st.info(f"No hay datos EVO en {año_pl_s}.")
             else: st.info("No hay datos EVO.")

                # --- PESTAÑA 3: Categorizar ---
        with tab_categorizar:
            st.header("Revisión y Categorización")

            # Asegurarse de que las variables de columna estén definidas en este scope también
            # (Aunque ya están definidas fuera, redefinirlas aquí soluciona el UnboundLocalError en los callbacks de botón)
            tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'Año'; mes = 'Mes'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'; imp_calc = 'importe'; imp_orig = 'IMPORTE'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

            # Recalcular máscara y número basado en el df actual de sesión
            current_uncategorized_mask = (df[cat] == ph_cat)
            current_num_uncategorized = df[current_uncategorized_mask].shape[0]


            if current_num_uncategorized > 0:
                st.info(f"Hay {current_num_uncategorized} transacciones sin CATEGORÍA principal.")
                # --- Botón para Sugerir (CON CORRECCIÓN DE SCOPE) ---
                if st.button("🤖 Sugerir CATEGORÍAS Faltantes", key="suggest_cats"):
                    # *** Redefinir variables necesarias DENTRO del callback ***
                    cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; desc = 'CONCEPTO'; imp_calc = 'importe'; imp_orig = 'IMPORTE'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

                    suggestions_applied = 0
                    df_suggest = st.session_state.edited_df.copy() # Trabajar sobre copia de sesión

                    # Asegurar que 'importe' existe y es numérico en la copia
                    if imp_orig in df_suggest.columns:
                        df_suggest.rename(columns={imp_orig: imp_calc}, inplace=True)
                    elif imp_calc not in df_suggest.columns:
                        st.error(f"Error crítico: Falta columna '{imp_calc}' para sugerir.")
                        st.stop()
                    if not pd.api.types.is_numeric_dtype(df_suggest[imp_calc]):
                         df_suggest[imp_calc] = pd.to_numeric(df_suggest[imp_calc].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                    # Identificar índices a actualizar en la copia
                    suggest_mask = (df_suggest[cat] == ph_cat) # Usar ph_cat redefinido localmente
                    indices_to_update = df_suggest[suggest_mask].index

                    # Iterar y aplicar sugerencias a la copia
                    for index in indices_to_update:
                        row = df_suggest.loc[index]
                        # Usar variables redefinidas localmente
                        sugg_cat, sugg_sub = suggest_category(row, desc, imp_calc, cat, subcat)
                        applied_c = False
                        # Usar ph_cat y ph_sub redefinidos localmente
                        if sugg_cat and df_suggest.loc[index, cat] == ph_cat:
                            df_suggest.loc[index, cat] = sugg_cat
                            applied_c = True
                        if sugg_sub and df_suggest.loc[index, subcat] == ph_sub:
                            if applied_c or (sugg_cat is None and df_suggest.loc[index, cat] != ph_cat):
                                df_suggest.loc[index, subcat] = sugg_sub
                                applied_c = True
                        if applied_c: suggestions_applied += 1

                    # Actualizar sesión si hubo cambios
                    if suggestions_applied > 0:
                        st.session_state.edited_df = df_suggest.copy()
                        st.success(f"Se aplicaron {suggestions_applied} sugerencias.")
                        convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se encontraron sugerencias.")
            else:
                st.success("¡Todo categorizado!")

            # --- Filtros y Editor ---
            st.subheader("Editar Transacciones")
            col_f1, col_f2, col_f3 = st.columns([1,1,2]);
            with col_f1:
                 # Usar el número recalculado
                 show_uncat_edit = st.checkbox("Solo sin CATEGORÍA", value=(current_num_uncategorized > 0), key='chk_uncat_edit', disabled=(current_num_uncategorized == 0))
            with col_f2: year_opts = ["Todos"] + sorted([int(a) for a in df[ano].dropna().unique()]); year_sel = st.selectbox("Año:", year_opts, key='sel_a_edit') # ano definido fuera
            with col_f3: txt_filter = st.text_input("Buscar Desc:", key='txt_edit_filter')

            # Aplicar filtros para mostrar en editor (usando df de sesión)
            df_display_edit = st.session_state.edited_df.copy()
            # Recalcular máscara sobre este df display
            display_mask = (df_display_edit[cat] == ph_cat) # cat y ph_cat definidos al inicio de la pestaña
            if show_uncat_edit: df_display_edit = df_display_edit[display_mask]
            if year_sel != "Todos":
                 if ano in df_display_edit.columns: df_display_edit = df_display_edit[df_display_edit[ano] == year_sel] # ano definido fuera
                 else: st.error(f"Columna '{ano}' no encontrada.") # ano definido fuera
            if txt_filter: df_display_edit = df_display_edit[df_display_edit[desc].str.contains(txt_filter, case=False, na=False)] # desc definido fuera
            df_display_edit['original_index'] = df_display_edit.index

            # Opciones Selectbox Editor
            cats_opts = sorted([str(c) for c in st.session_state.edited_df[cat].unique() if pd.notna(c) and c != ph_cat]) # cat y ph_cat definidos al inicio de la pestaña
            subcats_opts = sorted([str(s) for s in st.session_state.edited_df[subcat].unique() if pd.notna(s) and s != ph_sub]) # subcat y ph_sub definidos al inicio de la pestaña

            col_cfg = { cat: st.column_config.SelectboxColumn(cat, options=cats_opts, required=False), subcat: st.column_config.SelectboxColumn(subcat, options=subcats_opts, required=False), imp_calc: st.column_config.NumberColumn("Importe", format="%.2f €"), 'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"), 'original_index': None, ano: None, mes: None, } # cat, subcat, imp_calc, ano, mes definidos fuera o al inicio pestaña
            edited_data = st.data_editor( df_display_edit, column_config=col_cfg, use_container_width=True, num_rows="dynamic", key='data_editor_main', hide_index=True, height=400 )

            # Botón Aplicar Cambios Manuales
            if st.button("💾 Aplicar Cambios Editados", key="apply_manual_changes"):
                # *** Redefinir variables necesarias DENTRO del callback ***
                cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; # Redefinir las que se usan aquí

                changes_manual = 0; df_session = st.session_state.edited_df; edit_cols = [cat, subcat]
                indices_edited = edited_data['original_index']
                if indices_edited.is_unique:
                    # Actualización más eficiente usando .loc y .values
                    df_session.loc[indices_edited, edit_cols] = edited_data[edit_cols].values
                    # Para contar cambios reales, necesitaríamos comparar antes y después
                    changes_manual = len(indices_edited) # Simplificación: asumir que todas las filas mostradas cambiaron
                    st.session_state.edited_df = df_session.copy()
                    st.success(f"{changes_manual} filas actualizadas en sesión.")
                    convert_df_to_csv.clear(); st.experimental_rerun()
                else:
                    # Fallback si hay índices duplicados (menos probable con el índice original)
                    st.warning("Detectados índices no únicos, aplicando cambios fila por fila.")
                    for _, edited_row in edited_data.iterrows():
                        orig_idx = edited_row['original_index']
                        if orig_idx in df_session.index:
                            for c in edit_cols:
                                 if c in edited_row and edited_row[c] != df_session.loc[orig_idx, c]:
                                      df_session.loc[orig_idx, c] = edited_row[c]; changes_manual += 1
                    if changes_manual > 0:
                        st.session_state.edited_df = df_session.copy()
                        st.success(f"{changes_manual} cambios manuales aplicados."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se detectaron cambios manuales.")


            # Descargar Datos
            st.subheader("Descargar Datos"); st.caption("Descarga el CSV con las últimas categorías.")
            # Usar variable definida fuera o al inicio de pestaña
            csv_dl = convert_df_to_csv(st.session_state.edited_df)
            st.download_button( label="📥 Descargar CSV Actualizado", data=csv_dl, file_name=f"Gastos_Cat_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='dl_cat')

        # --- Fin Pestaña 3 ---
# --- Manejo de Errores Final ---
# (Comentado para facilitar depuración, descomentar en producción)
#    except Exception as e:
#        st.error(f"Ocurrió un error inesperado: {e}")
#        st.error("Detalle del error:"); st.code(traceback.format_exc())
#        st.session_state.edited_df = None; st.session_state.data_processed = False

if __name__ == "__main__":
    main()
