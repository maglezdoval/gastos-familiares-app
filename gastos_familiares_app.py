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
meses_es = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic" }
def obtener_nombre_mes(n):
    try: return meses_es.get(int(n), str(n))
    except: return str(n)

@st.cache_data
def convert_df_to_csv(df_to_convert):
    df_download = df_to_convert.copy()
    if 'importe' in df_download.columns: df_download.rename(columns={'importe': 'IMPORTE'}, inplace=True)
    if 'IMPORTE' in df_download.columns:
        df_download['IMPORTE'] = pd.to_numeric(df_download['IMPORTE'], errors='coerce')
        df_download['IMPORTE'] = df_download['IMPORTE'].map('{:.2f}'.format).str.replace('.', ',', regex=False); df_download['IMPORTE'].fillna('0,00', inplace=True)
    df_download = df_download.drop(columns=['original_index', 'temp_id'], errors='ignore')
    return df_download.to_csv(index=False, sep=';', decimal=',').encode('utf-8')

def clean_text(text):
    if not isinstance(text, str): return ""
    text = text.lower(); text = re.sub(r'\b\d{4,}\b', '', text); text = re.sub(r'\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?', '', text)
    text = re.sub(r'[^\w\s]', ' ', text); text = re.sub(r'\s+', ' ', text).strip(); return text

keywords_to_ignore = { 'pago', 'movil', 'en', 'compra', 'tarjeta', 'tarj', 'internet', 'comision', 'recibo', 'favor', 'de', 'la', 'el', 'los', 'las', 'a', 'con', 'sl', 'sa', 'sau', 's l', 'concepto', 'nº', 'ref', 'mandato', 'cuenta', 'gastos', 'varios', 'madrid', 'huelva', 'rozas', 'espanola', 'europe', 'fecha', 'num', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre', 'transferencia', 'trf', 'bizum', 'liquidacin', 'contrato', 'impuesto', 'cotizacion', 'tgss', 'iban', 'swift', 'com', 'www', 'http', 'https', 'cliente', 'importe', 'saldo', 'valor', 'atm', 'reintegro', 'oficina', 'suc', 'sr', 'sra', 'dna', 'bill', 'pending', 'uber', 'comercial', 'petroleo', 'obo', 'inv', 'for', 'sueldo', 'salar', 'nombre', 'miguel', 'angel', 'gonzalez', 'doval', 'alicia', 'jimenez', 'corpa', 'ordenante', 'beneficiario' }

def learn_categories(df, concepto_col, cat_col, subcat_col, importe_col, placeholder_cat, placeholder_sub):
    global category_knowledge; keyword_cat_counter = {}; amount_cat_counter = {}
    # Aprender solo de filas donde AMBAS están definidas (no son placeholder)
    df_categorized = df[(df[cat_col] != placeholder_cat) & (df[subcat_col] != placeholder_sub)].copy()
    if df_categorized.empty: return # No se puede aprender sin ejemplos completos
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
    global category_knowledge; concepto = row[concepto_col]; importe = row[importe_col]; concepto_lower = str(concepto).lower(); current_subcat_lower = str(row[subcat_col]).lower()
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
    # ... Más reglas ...

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
            importe_original_col = 'IMPORTE'; tipo_column_name = 'TIPO'; categoria_column_name = 'CATEGORÍA'; subcategoria_column_name = 'SUBCATEGORIA'; anio_column_name = 'AÑO'; mes_column_name = 'MES'; dia_column_name = 'DIA'; descripcion_column_name = 'CONCEPTO'; comercio_column_name = 'COMERCIO'; cuenta_column_name = 'CUENTA'
            importe_calculo_col = 'importe'
            required_columns = [importe_original_col, tipo_column_name, categoria_column_name, subcategoria_column_name, anio_column_name, mes_column_name, dia_column_name, descripcion_column_name, comercio_column_name, cuenta_column_name]
            missing = [col for col in required_columns if col not in df_processing.columns]; assert not missing, f"Faltan columnas: {', '.join(missing)}"
            df_processing.rename(columns={importe_original_col: importe_calculo_col}, inplace=True)
            df_processing[importe_calculo_col] = pd.to_numeric(df_processing[importe_calculo_col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            df_processing[anio_column_name] = df_processing[anio_column_name].astype(str); df_processing[mes_column_name] = df_processing[mes_column_name].astype(str).str.zfill(2); df_processing[dia_column_name] = df_processing[dia_column_name].astype(str).str.zfill(2)
            df_processing['Fecha'] = pd.to_datetime( df_processing[anio_column_name] + '-' + df_processing[mes_column_name] + '-' + df_processing[dia_column_name], format='%Y-%m-%d', errors='coerce')
            n_invalid = df_processing['Fecha'].isnull().sum();
            if n_invalid > 0: st.warning(f"{n_invalid} filas con fechas inválidas eliminadas.")
            df_processing.dropna(subset=['Fecha'], inplace=True)
            df_processing['Año'] = df_processing['Fecha'].dt.year.astype(int); df_processing['Mes'] = df_processing['Fecha'].dt.month.astype(int)
            placeholder_cat = 'SIN CATEGORÍA'; placeholder_sub = 'SIN SUBCATEGORÍA'
            # *** CORRECCIÓN fillna ***
            fill_cols = {
                categoria_column_name: placeholder_cat,
                subcategoria_column_name: placeholder_sub,
                comercio_column_name: '',  # <-- Mantiene string vacío
                cuenta_column_name: 'SIN CUENTA',
                tipo_column_name: 'SIN TIPO'
            }
            for col, placeholder in fill_cols.items():
                 if col in df_processing.columns:
                       df_processing[col] = df_processing[col].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], pd.NA).fillna(placeholder)
                       # Asegurarse que strings vacíos también se manejen (para COMERCIO)
                       if placeholder == '':
                           df_processing[col] = df_processing[col].replace('', placeholder) # No es estrictamente necesario si fillna ya hizo su trabajo, pero por si acaso

            learn_categories(df_processing, descripcion_column_name, categoria_column_name, subcategoria_column_name, importe_calculo_col, placeholder_cat, placeholder_sub)
            st.session_state.edited_df = df_processing.copy()
            st.session_state.data_processed = True
            st.sidebar.success("Datos procesados.")
            st.experimental_rerun()
        except Exception as e_proc:
            st.error(f"Error procesamiento: {e_proc}"); st.code(traceback.format_exc())
            st.session_state.edited_df = None; st.session_state.data_processed = False; return

    if st.session_state.get('data_processed', False) and st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy()
        tipo_column_name = 'TIPO'; categoria_column_name = 'CATEGORÍA'; subcategoria_column_name = 'SUBCATEGORIA'; anio_column_name = 'Año'; mes_column_name = 'Mes'; descripcion_column_name = 'CONCEPTO'; comercio_column_name = 'COMERCIO'; cuenta_column_name = 'CUENTA'; importe_calculo_col = 'importe'; placeholder_cat = 'SIN CATEGORÍA'; placeholder_sub = 'SIN SUBCATEGORÍA'

        # *** CORRECCIÓN MÁSCARA Y CONTEO ***
        # Identificar basado solo en CATEGORÍA
        uncategorized_mask = (df[categoria_column_name] == placeholder_cat)
        num_uncategorized = df[uncategorized_mask].shape[0]
        if num_uncategorized > 0: st.sidebar.warning(f"⚠️ {num_uncategorized} transacciones sin CATEGORÍA principal.")

        tab_gastos, tab_pl, tab_categorizar = st.tabs(["📊 Gastos", "📈 P&L EVO", "🏷️ Categorizar"])

        with tab_gastos:
            # ... (Código Pestaña Gastos sin cambios) ...
             st.header("Análisis Detallado de Gastos")
             valores_gasto = ["GASTO"]
             df_gastos_tab = df[df[tipo_column_name].isin(valores_gasto)].copy()
             if not df_gastos_tab.empty:
                 st.sidebar.header("Filtros de Gastos")
                 años_g_disp = sorted([int(a) for a in df_gastos_tab[anio_column_name].dropna().unique()])
                 año_g_sel = st.sidebar.selectbox("Año (Gastos):", años_g_disp, key='sel_año_g_tab')
                 df_g_año = df_gastos_tab[df_gastos_tab[anio_column_name] == año_g_sel]
                 if not df_g_año.empty:
                      cuentas_g_disp = sorted(df_g_año[cuenta_column_name].unique())
                      cuentas_g_sel = st.sidebar.multiselect("Cuentas (Gastos):", options=cuentas_g_disp, default=cuentas_g_disp, key='sel_cta_g_tab')
                      if cuentas_g_sel:
                           df_g_filtrado = df_g_año[df_g_año[cuenta_column_name].isin(cuentas_g_sel)].copy()
                           if not df_g_filtrado.empty:
                                st.subheader(f"Resumen ({año_g_sel} - Cts: {', '.join(cuentas_g_sel)})")
                                try: # Tabla Pivote Gastos
                                     pivot_g = df_g_filtrado.pivot_table(values=importe_calculo_col, index=categoria_column_name, columns=mes_column_name, aggfunc='sum', fill_value=0, margins=True, margins_name='Total')
                                     fmt_g = '{:,.0f} €'.format; style_g = [ {'selector': 'th.col_heading, th.row_heading', 'props': [('background-color', '#6c757d'), ('color', 'white'), ('font-weight', 'bold')]}, {'selector': 'th.col_heading', 'props': [('text-align', 'center')]}, {'selector': 'th.row_heading', 'props': [('text-align', 'left')]}, {'selector': 'tr:last-child td, td:last-child', 'props': [('font-weight', 'bold'), ('background-color', '#f8f9fa')]} ]
                                     st.dataframe(pivot_g.style.format(fmt_g).set_table_styles(style_g), use_container_width=True)
                                except Exception as e_piv_g: st.error(f"Error pivote gastos: {e_piv_g}")
                                # Detalle Gastos
                                st.subheader("Detalle Interactivo")
                                cats_g_filt = sorted(df_g_filtrado[categoria_column_name].unique()); mes_g_filt = sorted(df_g_filtrado[mes_column_name].unique())
                                if cats_g_filt and mes_g_filt:
                                     c1g, c2g = st.columns(2)
                                     with c1g: cat_g_sel = st.selectbox("Cat Gasto:", cats_g_filt, key='cat_g_det')
                                     with c2g: mes_g_sel = st.selectbox("Mes Gasto:", mes_g_filt, key='mes_g_det')
                                     df_g_det = df_g_filtrado[(df_g_filtrado[categoria_column_name] == cat_g_sel) & (df_g_filtrado[mes_column_name] == mes_g_sel)]
                                     if not df_g_det.empty:
                                          st.write(f"**Detalle Gasto: {cat_g_sel}, Mes {mes_g_sel}, Año {año_g_sel}**")
                                          det_g = df_g_det.groupby([subcategoria_column_name, descripcion_column_name, comercio_column_name, cuenta_column_name, 'Fecha'])[importe_calculo_col].sum().reset_index()
                                          det_g = det_g.sort_values(by=importe_calculo_col, ascending=True); det_g['Fecha'] = pd.to_datetime(det_g['Fecha']).dt.strftime('%Y-%m-%d'); det_g[importe_calculo_col] = det_g[importe_calculo_col].map('{:,.2f} €'.format)
                                          st.dataframe(det_g, use_container_width=True, height=300)
                                     else: st.info("No hay detalles de gasto para esta selección.")
                                else: st.info("No hay datos suficientes para el detalle de gastos.")
                           else: st.info("No hay gastos para la selección de cuentas/año.")
                      else: st.warning("Seleccione cuentas para el análisis de gastos.")
                 else: st.info(f"No hay gastos para el año {año_g_sel}.")
            else: st.info("No hay registros de tipo GASTO.")


        with tab_pl:
            # ... (Código Pestaña P&L sin cambios) ...
             st.header("Análisis P&L - Cuenta Familiar (EVO)")
             df_evo_tab = df[df[cuenta_column_name] == 'EVO'].copy()
             if not df_evo_tab.empty:
                 st.sidebar.header("Filtro P&L (EVO)")
                 años_evo_disp = sorted([int(a) for a in df_evo_tab[anio_column_name].dropna().unique()])
                 año_pl_sel = st.sidebar.selectbox("Año (P&L):", años_evo_disp, key='sel_año_pl_tab')
                 df_evo_año_tab = df_evo_tab[df_evo_tab[anio_column_name] == año_pl_sel]
                 if not df_evo_año_tab.empty:
                      tipos_ingreso = ['TRASPASO', 'INGRESO', 'REEMBOLSO']; df_ing = df_evo_año_tab[df_evo_año_tab[tipo_column_name].isin(tipos_ingreso)]; ing_mes = df_ing.groupby(mes_column_name)[importe_calculo_col].sum()
                      tipos_egreso = ['GASTO', 'RECIBO']; df_egr = df_evo_año_tab[df_evo_año_tab[tipo_column_name].isin(tipos_egreso)]; egr_mes_abs = df_egr.groupby(mes_column_name)[importe_calculo_col].sum().abs()
                      df_pl = pd.DataFrame({'Ingresos': ing_mes, 'Egresos': egr_mes_abs}).fillna(0); df_pl['Resultado'] = df_pl['Ingresos'] - df_pl['Egresos']
                      total_pl = df_pl.sum(); total_pl.name = 'Total Anual'; df_pl = pd.concat([df_pl, total_pl.to_frame().T]); df_pl.index = df_pl.index.map(obtener_nombre_mes)
                      fmt_pl = '{:,.2f} €'; df_pl_fmt = df_pl.style.format(fmt_pl).applymap(lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else 'color: black'), subset=['Resultado']).set_properties(**{'text-align': 'right'})
                      st.subheader(f"Tabla P&L Mensual ({año_pl_sel}) - Cuenta EVO"); st.dataframe(df_pl_fmt, use_container_width=True)
                      df_pl_ch = df_pl.drop('Total Anual')
                      try: mes_num_map = {v: k for k, v in meses_es.items()}; df_pl_ch.index = df_pl_ch.index.map(mes_num_map.get); df_pl_ch = df_pl_ch.sort_index()
                      except: pass
                      st.subheader(f"Gráfico P&L Mensual ({año_pl_sel}) - Cuenta EVO"); st.line_chart(df_pl_ch[['Ingresos', 'Egresos']])
                 else: st.info(f"No hay datos para EVO en {año_pl_sel}.")
             else: st.info("No se encontraron transacciones para la cuenta EVO.")

        with tab_categorizar:
            st.header("Revisión y Categorización de Transacciones")
            if num_uncategorized > 0:
                st.info(f"Hay {num_uncategorized} transacciones sin CATEGORÍA principal asignada.")
                # Botón Sugerir (usa la máscara nueva)
                if st.button("🤖 Sugerir CATEGORÍAS Principales Faltantes", key="suggest_cats"):
                    suggestions_applied_count = 0
                    df_suggest = st.session_state.edited_df.copy()
                    # *** Usa la máscara corregida ***
                    current_uncategorized_mask_suggest = (df_suggest[categoria_column_name] == placeholder_cat)
                    indices_to_update = df_suggest[current_uncategorized_mask_suggest].index
                    for index in indices_to_update:
                        row_to_process = df_suggest.loc[index]
                        suggested_cat, suggested_subcat = suggest_category(row_to_process, descripcion_column_name, importe_calculo_col, categoria_column_name, subcategoria_column_name)
                        applied_change_cat = False
                        # Solo aplicar si se sugirió una CATEGORÍA y la actual es el placeholder
                        if suggested_cat and df_suggest.loc[index, categoria_column_name] == placeholder_cat:
                            df_suggest.loc[index, categoria_column_name] = suggested_cat
                            applied_change_cat = True
                            # Si también se sugirió subcategoría Y la actual es placeholder, aplicarla
                            if suggested_subcat and df_suggest.loc[index, subcategoria_column_name] == placeholder_sub:
                                 df_suggest.loc[index, subcategoria_column_name] = suggested_subcat
                        if applied_change_cat: suggestions_applied_count += 1 # Contar solo si se aplicó la categoría principal
                    if suggestions_applied_count > 0:
                        st.session_state.edited_df = df_suggest.copy(); st.success(f"Se aplicaron {suggestions_applied_count} sugerencias de CATEGORÍA."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se encontraron sugerencias automáticas para CATEGORÍA.")
            else: st.success("¡Todas las transacciones tienen una CATEGORÍA principal asignada!")

            # Filtros y Editor
            st.subheader("Editar Transacciones")
            col_f1, col_f2, col_f3 = st.columns([1,1,2]);
            with col_f1:
                 # *** El checkbox ahora usa la máscara corregida ***
                 show_uncat_edit = st.checkbox("Mostrar solo sin CATEGORÍA", value=(num_uncategorized > 0), key='chk_uncat_edit')
            with col_f2: year_edit_opts = ["Todos"] + sorted([int(a) for a in df[anio_column_name].dropna().unique()]); year_edit_sel = st.selectbox("Año:", year_edit_opts, key='sel_año_edit')
            with col_f3: txt_edit_filter = st.text_input("Buscar Descripción:", key='txt_edit_filter')

            df_display_edit = st.session_state.edited_df.copy()
            # *** Aplicar máscara corregida al filtrar para el editor ***
            display_uncategorized_mask_edit = (df_display_edit[categoria_column_name] == placeholder_cat)
            if show_uncat_edit: df_display_edit = df_display_edit[display_uncategorized_mask_edit]
            if year_edit_sel != "Todos":
                 if anio_column_name in df_display_edit.columns: df_display_edit = df_display_edit[df_display_edit[anio_column_name] == year_edit_sel]
                 else: st.error(f"Error interno: Columna '{anio_column_name}' no encontrada.")
            if txt_edit_filter: df_display_edit = df_display_edit[df_display_edit[descripcion_column_name].str.contains(txt_edit_filter, case=False, na=False)]
            df_display_edit['original_index'] = df_display_edit.index

            # Opciones Selectbox Editor (sin cambios aquí, ya estaban corregidos)
            categorias_unicas_raw = st.session_state.edited_df[categoria_column_name].unique(); categorias_existentes_now = sorted([str(cat) for cat in categorias_unicas_raw if pd.notna(cat) and cat != placeholder_cat])
            subcategorias_unicas_raw = st.session_state.edited_df[subcategoria_column_name].unique(); subcategorias_existentes_now = sorted([str(sub) for sub in subcategorias_unicas_raw if pd.notna(sub) and sub != placeholder_sub])
            column_config_edit = { categoria_column_name: st.column_config.SelectboxColumn(f"{categoria_column_name}", options=categorias_existentes_now, required=False), subcategoria_column_name: st.column_config.SelectboxColumn(f"{subcategoria_column_name}", options=subcategorias_existentes_now, required=False), importe_calculo_col: st.column_config.NumberColumn("Importe", format="%.2f €"), 'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"), 'original_index': None, anio_column_name: None, mes_column_name: None, }

            # Data Editor
            edited_data = st.data_editor( df_display_edit, column_config=column_config_edit, use_container_width=True, num_rows="dynamic", key='data_editor_main', hide_index=True, height=400 )

            # Botón Aplicar Cambios Manuales (sin cambios)
            if st.button("💾 Aplicar Cambios Editados", key="apply_manual_changes"):
                changes_applied_manual = 0; df_current_session = st.session_state.edited_df; editable_cols = [categoria_column_name, subcategoria_column_name]
                for _, edited_row in edited_data.iterrows():
                    original_idx = edited_row['original_index']
                    if original_idx in df_current_session.index:
                        for col in editable_cols:
                            if col in edited_row and edited_row[col] != df_current_session.loc[original_idx, col]: df_current_session.loc[original_idx, col] = edited_row[col]; changes_applied_manual += 1
                if changes_applied_manual > 0: st.session_state.edited_df = df_current_session.copy(); st.success(f"{changes_applied_manual} cambios manuales aplicados."); convert_df_to_csv.clear(); st.experimental_rerun()
                else: st.info("No se detectaron cambios manuales.")

            # Descargar Datos (sin cambios)
            st.subheader("Descargar Datos"); st.caption("Descarga el CSV con las últimas categorías guardadas.")
            csv_data_to_download = convert_df_to_csv(st.session_state.edited_df)
            st.download_button( label="📥 Descargar CSV Actualizado", data=csv_data_to_download, file_name=f"Gastos_Categorizado_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='download_csv_categorized')

    # --- Manejo de Errores Final ---
    # (Este except captura errores de procesamiento y de las pestañas)
    # except Exception as e:
    #     st.error(f"Ocurrió un error inesperado en la aplicación: {e}")
    #     st.error("Detalle del error:")
    #     st.code(traceback.format_exc())
    #     st.session_state.edited_df = None
    #     st.session_state.data_processed = False


# --- Punto de Entrada ---
if __name__ == "__main__":
    main()
