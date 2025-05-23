import streamlit as st
import pandas as pd
import calendar
import traceback
import re
from collections import Counter, defaultdict

# --- Diccionario Global para Almacenar Conocimiento de Categorías ---
category_knowledge = {
    "keyword_map": {},
    "amount_map": {}
}

# --- Session State para Configuraciones ---
if 'edited_df' not in st.session_state: st.session_state.edited_df = None
if 'data_processed' not in st.session_state: st.session_state.data_processed = False
if 'last_uploaded_filename' not in st.session_state: st.session_state.last_uploaded_filename = None
if 'category_hierarchy' not in st.session_state: st.session_state.category_hierarchy = defaultdict(set)
if 'comercio_to_category_map' not in st.session_state: st.session_state.comercio_to_category_map = {}

# --- Funciones Auxiliares ---
meses_es = { 1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic" }
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

def clean_text(t):
    if not isinstance(t, str) or pd.isna(t): return ""
    t = t.lower(); t = re.sub(r'\b\d{4,}\b', '', t); t = re.sub(r'\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?', '', t); t = re.sub(r'[^\w\s]', ' ', t); t = re.sub(r'\s+', ' ', t).strip(); return t

keywords_to_ignore = { 'pago', 'movil', 'en', 'compra', 'tarjeta', 'tarj', 'internet', 'comision', 'recibo', 'favor', 'de', 'la', 'el', 'los', 'las', 'a', 'con', 'sl', 'sa', 'sau', 's l', 'concepto', 'nº', 'ref', 'mandato', 'cuenta', 'gastos', 'varios', 'madrid', 'huelva', 'rozas', 'espanola', 'europe', 'fecha', 'num', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre', 'transferencia', 'trf', 'bizum', 'liquidacin', 'contrato', 'impuesto', 'cotizacion', 'tgss', 'iban', 'swift', 'com', 'www', 'http', 'https', 'cliente', 'importe', 'saldo', 'valor', 'atm', 'reintegro', 'oficina', 'suc', 'sr', 'sra', 'dna', 'bill', 'pending', 'uber', 'comercial', 'petroleo', 'obo', 'inv', 'for', 'sueldo', 'salar', 'nombre', 'miguel', 'angel', 'gonzalez', 'doval', 'alicia', 'jimenez', 'corpa', 'ordenante', 'beneficiario' }

def learn_categories(df, concepto_col, cat_col, subcat_col, importe_col, placeholder_cat, placeholder_sub):
    global category_knowledge, keywords_to_ignore; kw_counter = {}; amt_counter = {}
    df_cat = df[ (df[cat_col] != placeholder_cat) & (df[subcat_col] != placeholder_sub) & (~df[cat_col].isin(['TRASPASO', 'RECIBO'])) ].copy()
    if df_cat.empty: return
    df_cat['clean'] = df_cat[concepto_col].apply(clean_text)
    for _, r in df_cat.iterrows():
        cat = r[cat_col]; sub = r[subcat_col]; imp = r[importe_col]
        amt_bin = int(round(imp / 10) * 10) if pd.notna(imp) and isinstance(imp, (int, float)) else 0
        cleaned_text_val = r['clean']
        if cleaned_text_val is None: cleaned_text_val = "" # Seguridad extra
        words = set(cleaned_text_val.split()) - keywords_to_ignore
        for w in words:
            if len(w) < 4: continue
            kw_counter.setdefault(w, Counter())[(cat, sub)] += 1
            amt_counter.setdefault((w, amt_bin), Counter())[(cat, sub)] += 1
    category_knowledge["keyword_map"] = {w: c.most_common(1)[0][0] for w, c in kw_counter.items() if c}
    category_knowledge["amount_map"] = {k: c.most_common(1)[0][0] for k, c in amt_counter.items() if c}
    st.sidebar.info(f"Aprendizaje: {len(category_knowledge['keyword_map'])} keywords.")

def suggest_category(row, concepto_col, importe_col, cat_col, subcat_col, com_col):
    global category_knowledge, keywords_to_ignore
    # --- 0. Mapeo Comercio -> Categoría ---
    comercio = row[com_col]
    if isinstance(comercio, str) and comercio != '' and comercio in st.session_state.comercio_to_category_map:
        default_cat = st.session_state.comercio_to_category_map[comercio]
        default_sub = next(iter(st.session_state.category_hierarchy.get(default_cat, {''})), '')
        return (default_cat, default_sub if default_sub else 'GENERAL')

    # --- 1. Reglas Explícitas ---
    concepto = row[concepto_col]; importe = row[importe_col]; concepto_lower = str(concepto).lower(); current_subcat_lower = str(row[subcat_col]).lower()
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
    # ... etc ...

    # --- 2. Conocimiento Aprendido ---
    cleaned_concepto = clean_text(concepto)
    if cleaned_concepto is None: cleaned_concepto = "" # Seguridad extra
    words = set(cleaned_concepto.split()) - keywords_to_ignore

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
    return best_suggestion if best_suggestion else None

def derive_category_hierarchy(df, cat_col, subcat_col, ph_cat, ph_sub):
    hierarchy = defaultdict(set)
    df_valid = df[(df[cat_col] != ph_cat) & (df[subcat_col] != ph_sub)].copy()
    for cat, group in df_valid.groupby(cat_col):
        hierarchy[cat].update(group[subcat_col].unique())
    return hierarchy

def derive_comercio_map(df, com_col, cat_col, ph_cat):
    comercio_map = {}
    df_valid = df[(df[com_col] != '') & (df[cat_col] != ph_cat)].copy()
    if not df_valid.empty:
        # Usar apply para manejar casos donde mode() podría estar vacío
        comercio_map = df_valid.groupby(com_col)[cat_col].apply(lambda x: x.mode()[0] if not x.mode().empty else None).dropna().to_dict()
    return comercio_map

# --- Función Principal Main ---
def main():
    st.set_page_config(layout="wide")
    st.title('Análisis Financiero y Configuración')

    if 'edited_df' not in st.session_state: st.session_state.edited_df = None
    if 'data_processed' not in st.session_state: st.session_state.data_processed = False
    if 'last_uploaded_filename' not in st.session_state: st.session_state.last_uploaded_filename = None
    if 'category_hierarchy' not in st.session_state: st.session_state.category_hierarchy = defaultdict(set)
    if 'comercio_to_category_map' not in st.session_state: st.session_state.comercio_to_category_map = {}

    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"], key="file_uploader")

    if uploaded_file is not None:
        if 'last_uploaded_filename' not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
             st.session_state.edited_df = None; st.session_state.data_processed = False; st.session_state.last_uploaded_filename = uploaded_file.name; convert_df_to_csv.clear()
             st.session_state.category_hierarchy = defaultdict(set); st.session_state.comercio_to_category_map = {}
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
            imp_orig = 'IMPORTE'; tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano_col = 'AÑO'; mes_col = 'MES'; dia_col = 'DIA'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA' # Nombres originales/claves
            imp_calc = 'importe' # Nombre para cálculos
            ano_calc = 'Año'; mes_calc = 'Mes' # Nombres para columnas calculadas
            req_cols = [imp_orig, tipo, cat, subcat, ano_col, mes_col, dia_col, desc, com, cta];
            missing = [c for c in req_cols if c not in df_processing.columns]; assert not missing, f"Faltan: {', '.join(missing)}"
            df_processing.rename(columns={imp_orig: imp_calc}, inplace=True)
            df_processing[imp_calc] = pd.to_numeric(df_processing[imp_calc].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            df_processing[ano_col]=df_processing[ano_col].astype(str); df_processing[mes_col]=df_processing[mes_col].astype(str).str.zfill(2); df_processing[dia_col]=df_processing[dia_col].astype(str).str.zfill(2)
            df_processing['Fecha'] = pd.to_datetime( df_processing[ano_col] + '-' + df_processing[mes_col] + '-' + df_processing[dia_col], format='%Y-%m-%d', errors='coerce')
            n_inv = df_processing['Fecha'].isnull().sum();
            if n_inv > 0: st.warning(f"{n_inv} filas con fechas inválidas eliminadas.")
            df_processing.dropna(subset=['Fecha'], inplace=True)
            df_processing[ano_calc] = df_processing['Fecha'].dt.year.astype(int); df_processing[mes_calc] = df_processing['Fecha'].dt.month.astype(int) # Usar nombres calculados
            ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'
            fill_cols = {cat: ph_cat, subcat: ph_sub, com: '', cta: 'SIN CUENTA', tipo: 'SIN TIPO'}
            for c, ph in fill_cols.items():
                 if c in df_processing.columns:
                       df_processing[c] = df_processing[c].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], pd.NA).fillna(ph)
                       if ph == '': df_processing[c] = df_processing[c].replace('', ph)
            mask_traspaso = df_processing[tipo] == 'TRASPASO'; df_processing.loc[mask_traspaso, cat] = 'TRASPASO'; df_processing.loc[mask_traspaso, subcat] = 'TRASPASO INTERNO'
            mask_recibo = df_processing[tipo] == 'RECIBO'; df_processing.loc[mask_recibo, cat] = 'RECIBO'; df_processing.loc[mask_recibo, subcat] = 'PAGO RECIBO'
            st.session_state.category_hierarchy = derive_category_hierarchy(df_processing, cat, subcat, ph_cat, ph_sub)
            st.session_state.comercio_to_category_map = derive_comercio_map(df_processing, com, cat, ph_cat)
            learn_categories(df_processing, desc, cat, subcat, imp_calc, ph_cat, ph_sub)
            st.session_state.edited_df = df_processing.copy()
            st.session_state.data_processed = True
            st.sidebar.success("Datos procesados.")
            st.experimental_rerun()
        except Exception as e_proc: st.error(f"Error procesando: {e_proc}"); st.code(traceback.format_exc()); st.session_state.edited_df = None; st.session_state.data_processed = False; return

    if st.session_state.get('data_processed', False) and st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy()
        # Definir nombres de columna a usar en las pestañas
        tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'Año'; mes = 'Mes'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'; imp_calc = 'importe'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

        uncategorized_mask = (df[cat] == ph_cat); num_uncategorized = df[uncategorized_mask].shape[0]
        if num_uncategorized > 0: st.sidebar.warning(f"⚠️ {num_uncategorized} trans. sin CATEGORÍA.")

        tab_gastos, tab_pl, tab_categorizar, tab_config = st.tabs(["📊 Gastos", "📈 P&L EVO", "🏷️ Categorizar", "⚙️ Configuración"])

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

        with tab_categorizar:
            st.header("Revisión y Categorización")
            # Definir variables locales para esta pestaña si es necesario simplificar
            cat_editor = cat; subcat_editor = subcat; desc_editor = desc; imp_calc_editor = imp_calc; imp_orig_editor = 'IMPORTE'; ph_cat_editor = ph_cat; ph_sub_editor = ph_sub; com_editor = com; ano_editor = ano; mes_editor = mes

            if num_uncategorized > 0:
                st.info(f"Hay {num_uncategorized} trans. sin CATEGORÍA.")
                if st.button("🤖 Sugerir CATEGORÍAS Faltantes", key="suggest_cats"):
                    # Redefinir para el scope del botón
                    cat_btn=cat_editor; subcat_btn=subcat_editor; desc_btn=desc_editor; imp_calc_btn=imp_calc_editor; imp_orig_btn='IMPORTE'; ph_cat_btn=ph_cat_editor; ph_sub_btn=ph_sub_editor; com_btn=com_editor
                    suggestions_applied = 0; df_suggest = st.session_state.edited_df.copy()
                    if imp_orig_btn in df_suggest.columns: df_suggest.rename(columns={imp_orig_btn: imp_calc_btn}, inplace=True)
                    if imp_calc_btn not in df_suggest.columns: raise KeyError("Falta importe")
                    if not pd.api.types.is_numeric_dtype(df_suggest[imp_calc_btn]): df_suggest[imp_calc_btn] = pd.to_numeric(df_suggest[imp_calc_btn].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
                    suggest_mask = (df_suggest[cat_btn] == ph_cat_btn); indices_to_update = df_suggest[suggest_mask].index
                    for index in indices_to_update:
                        row = df_suggest.loc[index]; sugg_result = suggest_category(row, desc_btn, imp_calc_btn, cat_btn, subcat_btn, com_btn)
                        applied_c = False
                        if sugg_result is not None:
                           sugg_cat, sugg_sub = sugg_result
                           if sugg_cat and df_suggest.loc[index, cat_btn] == ph_cat_btn: df_suggest.loc[index, cat_btn] = sugg_cat; applied_c = True
                           if sugg_sub and df_suggest.loc[index, subcat_btn] == ph_sub_btn:
                               if applied_c or (sugg_cat is None and df_suggest.loc[index, cat_btn] != ph_cat_btn): df_suggest.loc[index, subcat_btn] = sugg_sub; applied_c = True
                        if applied_c: suggestions_applied += 1
                    if suggestions_applied > 0: st.session_state.edited_df = df_suggest.copy(); st.success(f"Se aplicaron {suggestions_applied} sugerencias."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se encontraron sugerencias.")
            else: st.success("¡Todo categorizado!")

            st.subheader("Editar Transacciones")
            col_f1, col_f2, col_f3 = st.columns([1,1,2]);
            with col_f1: show_uncat_edit = st.checkbox("Solo sin CATEGORÍA", value=(num_uncategorized > 0), key='chk_uncat_edit', disabled=(num_uncategorized == 0))
            with col_f2: year_opts = ["Todos"] + sorted([int(a) for a in df[ano_editor].dropna().unique()]); year_sel = st.selectbox("Año:", year_opts, key='sel_a_edit')
            with col_f3: txt_filter = st.text_input("Buscar Desc:", key='txt_edit_filter')
            df_display_edit = st.session_state.edited_df.copy(); display_mask = (df_display_edit[cat_editor] == ph_cat_editor)
            if show_uncat_edit: df_display_edit = df_display_edit[display_mask]
            if year_sel != "Todos":
                 if ano_editor in df_display_edit.columns: df_display_edit = df_display_edit[df_display_edit[ano_editor] == year_sel]
                 else: st.error(f"Columna '{ano_editor}' no encontrada.")
            if txt_filter: df_display_edit = df_display_edit[df_display_edit[desc_editor].str.contains(txt_filter, case=False, na=False)]
            df_display_edit['original_index'] = df_display_edit.index
            cats_opts = sorted([str(c) for c in st.session_state.edited_df[cat_editor].unique() if pd.notna(c) and c != ph_cat_editor])
            subcats_opts = sorted([str(s) for s in st.session_state.edited_df[subcat_editor].unique() if pd.notna(s) and s != ph_sub_editor])
            col_cfg = { cat_editor: st.column_config.SelectboxColumn(cat_editor, options=cats_opts, required=False),
                        subcat_editor: st.column_config.SelectboxColumn(subcat_editor, options=subcats_opts, required=False),
                        imp_calc_editor: st.column_config.NumberColumn("Importe", format="%.2f €"),
                        'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"),
                        'original_index': None, ano_editor: None, mes_editor: None, }
            edited_data = st.data_editor( df_display_edit, column_config=col_cfg, use_container_width=True, num_rows="dynamic", key='data_editor_main', hide_index=True, height=400 )

            if st.button("💾 Aplicar Cambios Editados", key="apply_manual_changes"):
                # Redefinir locales para este botón
                cat_btn_apply = cat_editor; subcat_btn_apply = subcat_editor; desc_btn_apply = desc_editor; ph_sub_btn_apply = ph_sub_editor

                changes_manual = 0; df_session = st.session_state.edited_df; edit_cols = [cat_btn_apply, subcat_btn_apply]
                invalid_combinations = []; valid_hierarchy = st.session_state.category_hierarchy
                temp_df_session = df_session.copy()
                indices_edited = edited_data['original_index']
                if indices_edited.is_unique:
                    temp_df_session.loc[indices_edited, edit_cols] = edited_data[edit_cols].values
                    for idx in indices_edited:
                        edited_cat = temp_df_session.loc[idx, cat_btn_apply]; edited_subcat = temp_df_session.loc[idx, subcat_btn_apply]
                        if edited_cat in valid_hierarchy and edited_subcat not in valid_hierarchy[edited_cat] and edited_subcat != ph_sub_btn_apply and edited_subcat != '':
                            invalid_combinations.append({ "Índice": idx, "Concepto": temp_df_session.loc[idx, desc_btn_apply], "Cat": edited_cat, "SubCat Inválida": edited_subcat, "SubCats Válidas": ", ".join(sorted(list(valid_hierarchy[edited_cat]))) if valid_hierarchy[edited_cat] else "Ninguna" })
                    if not invalid_combinations:
                        st.session_state.edited_df = temp_df_session.copy()
                        changes_manual = len(indices_edited)
                        st.success(f"{changes_manual} filas actualizadas."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else:
                        st.error("Combinaciones Cat/SubCat inválidas. Cambios NO aplicados."); st.dataframe(pd.DataFrame(invalid_combinations), use_container_width=True)
                else: st.error("Error: Índices duplicados.")

            st.subheader("Descargar Datos"); st.caption("Descarga el CSV con las últimas categorías.")
            csv_dl = convert_df_to_csv(st.session_state.edited_df)
            st.download_button( label="📥 Descargar CSV Actualizado", data=csv_dl, file_name=f"Gastos_Cat_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='dl_cat')

        with tab_config:
            st.header("⚙️ Configuración")
            st.write("Gestiona relaciones Categoría/Subcategoría y Comercio/Categoría.")
            st.caption("Cambios guardados temporalmente en la sesión.")
            cat_cfg = cat; subcat_cfg = subcat; com_cfg = com; ph_cat_cfg = ph_cat

            st.subheader("Jerarquía Categoría -> Subcategorías")
            hierarchy = st.session_state.category_hierarchy
            if hierarchy:
                for category_cfg_item, subcategories_cfg in sorted(hierarchy.items()):
                    with st.expander(f"**{category_cfg_item}** ({len(subcategories_cfg)} subcat.)"):
                        if subcategories_cfg: st.write(", ".join(sorted(list(subcategories_cfg))))
                        else: st.write("_(Ninguna subcategoría encontrada)_")
            else: st.info("No se pudo derivar jerarquía.")

            st.subheader("Asignar Categoría por Defecto a Comercios")
            comercio_map = st.session_state.comercio_to_category_map
            all_comercios = sorted([c for c in df[com_cfg].unique() if c != ''])
            all_categories_cfg = sorted([c for c in df[cat_cfg].unique() if c != ph_cat_cfg])
            comercio_cfg_list = [{"COMERCIO": c, "CATEGORÍA Asignada": comercio_map.get(c, None)} for c in all_comercios]
            df_comercio_cfg = pd.DataFrame(comercio_cfg_list)
            comercio_editor_cfg = { "COMERCIO": st.column_config.TextColumn("Comercio", disabled=True), "CATEGORÍA Asignada": st.column_config.SelectboxColumn("Cat. por Defecto", options=[None] + all_categories_cfg, required=False) }
            st.info("💡 Edita 'Cat. por Defecto' para asignar/cambiar.")
            edited_comercio_data = st.data_editor(df_comercio_cfg, column_config=comercio_editor_cfg, key="comercio_cfg_editor", hide_index=True, use_container_width=True, num_rows="fixed")

            if st.button("💾 Guardar Mapeo de Comercios", key="save_comercio_map"):
                new_map = {row["COMERCIO"]: row["CATEGORÍA Asignada"] for _, row in edited_comercio_data.iterrows() if row["CATEGORÍA Asignada"] is not None and row["CATEGORÍA Asignada"] != ''}
                if new_map != st.session_state.comercio_to_category_map:
                    st.session_state.comercio_to_category_map = new_map
                    st.success("Mapeo Comercio -> Categoría actualizado.")
                    # Re-derivar jerarquía por si afecta
                    ph_sub_cfg = ph_sub # Necesitamos ph_sub aquí
                    st.session_state.category_hierarchy = derive_category_hierarchy(st.session_state.edited_df, cat_cfg, subcat_cfg, ph_cat_cfg, ph_sub_cfg)
                else: st.info("No se detectaron cambios en el mapeo.")

    # --- Manejo de Errores Final ---
    # Comentado para depuración
    # except Exception as e:
    #     st.error(f"Ocurrió un error inesperado: {e}"); st.code(traceback.format_exc())
    #     st.session_state.edited_df = None; st.session_state.data_processed = False

if __name__ == "__main__":
    main()
