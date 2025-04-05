import streamlit as st
import pandas as pd
import calendar
import traceback
import re
from collections import Counter, defaultdict # Añadir defaultdict

# --- Diccionario Global para Almacenar Conocimiento de Categorías ---
category_knowledge = {
    "keyword_map": {},
    "amount_map": {}
}

# --- Session State para Configuraciones ---
# Inicializar al principio para asegurar que existen
if 'category_hierarchy' not in st.session_state:
    st.session_state.category_hierarchy = defaultdict(set) # {Categoria: {Subcat1, Subcat2}}
if 'comercio_to_category_map' not in st.session_state:
    st.session_state.comercio_to_category_map = {} # {Comercio: CategoriaDefault}

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
        words = set(r['clean'].split()) - keywords_to_ignore
        for w in words:
            if len(w) < 4: continue
            kw_counter.setdefault(w, Counter())[(cat, sub)] += 1
            amt_counter.setdefault((w, amt_bin), Counter())[(cat, sub)] += 1
    category_knowledge["keyword_map"] = {w: c.most_common(1)[0][0] for w, c in kw_counter.items() if c}
    category_knowledge["amount_map"] = {k: c.most_common(1)[0][0] for k, c in amt_counter.items() if c}
    st.sidebar.info(f"Aprendizaje: {len(category_knowledge['keyword_map'])} keywords.")

def suggest_category(row, concepto_col, importe_col, cat_col, subcat_col, com_col): # Añadir com_col
    global category_knowledge, keywords_to_ignore
    # --- 0. Usar mapeo Comercio -> Categoría si existe (MÁXIMA PRIORIDAD) ---
    comercio = row[com_col]
    if isinstance(comercio, str) and comercio != '' and comercio in st.session_state.comercio_to_category_map:
        default_cat = st.session_state.comercio_to_category_map[comercio]
        # Intentar obtener subcategoría por defecto de la jerarquía para esa categoría
        default_sub = next(iter(st.session_state.category_hierarchy.get(default_cat, {''})), '') # Primera subcat o ''
        # st.write(f"Debug Suggest: Comercio '{comercio}' -> Cat '{default_cat}', Sub '{default_sub}'") # Debug
        return (default_cat, default_sub if default_sub else 'GENERAL') # Devolver subcat o 'GENERAL'

    # --- 1. Reglas Explícitas (si no hay mapeo de comercio) ---
    concepto = row[concepto_col]; importe = row[importe_col]; concepto_lower = str(concepto).lower(); current_subcat_lower = str(row[subcat_col]).lower()
    if "mercadona" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO'); # ... (resto de reglas) ...
    # ... etc ...

    # --- 2. Conocimiento Aprendido (si no hay reglas ni mapeo) ---
    cleaned = clean_text(concepto); words = set(cleaned).split() - keywords_to_ignore
    amt_bin = int(round(importe / 10) * 10) if pd.notna(importe) and isinstance(importe, (int, float)) else 0
    best_sugg = None
    for w in words:
        if len(w) < 4: continue
        k_amt = (w, amt_bin);
        if k_amt in category_knowledge["amount_map"]: best_sugg = category_knowledge["amount_map"][k_amt]; break
    if best_sugg is None:
        for w in words:
             if len(w) < 4: continue
             if w in category_knowledge["keyword_map"]: best_sugg = category_knowledge["keyword_map"][w]; break
    return best_sugg if best_sugg else None

def derive_category_hierarchy(df, cat_col, subcat_col, ph_cat, ph_sub):
    """Deriva la estructura Cat -> {Subcats} del DataFrame."""
    hierarchy = defaultdict(set)
    # Excluir filas sin categoría o subcategoría válida
    df_valid = df[(df[cat_col] != ph_cat) & (df[subcat_col] != ph_sub)].copy()
    # Agrupar y añadir a la jerarquía
    for cat, group in df_valid.groupby(cat_col):
        hierarchy[cat].update(group[subcat_col].unique())
    return hierarchy

def derive_comercio_map(df, com_col, cat_col, ph_cat):
    """Deriva el mapeo Comercio -> Categoría más frecuente."""
    comercio_map = {}
    # Considerar solo comercios no vacíos y con categoría válida
    df_valid = df[(df[com_col] != '') & (df[cat_col] != ph_cat)].copy()
    if not df_valid.empty:
        # Encontrar la categoría más frecuente para cada comercio
        comercio_map = df_valid.groupby(com_col)[cat_col].agg(lambda x: x.mode()[0] if not x.mode().empty else None).dropna().to_dict()
    return comercio_map

# --- Función Principal Main ---
def main():
    st.set_page_config(layout="wide")
    st.title('Análisis Financiero y Configuración')

    if 'edited_df' not in st.session_state: st.session_state.edited_df = None
    if 'data_processed' not in st.session_state: st.session_state.data_processed = False
    if 'last_uploaded_filename' not in st.session_state: st.session_state.last_uploaded_filename = None
    # Inicializar mapeos en session state si no existen
    if 'category_hierarchy' not in st.session_state: st.session_state.category_hierarchy = defaultdict(set)
    if 'comercio_to_category_map' not in st.session_state: st.session_state.comercio_to_category_map = {}

    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"], key="file_uploader")

    if uploaded_file is not None:
        if 'last_uploaded_filename' not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
             st.session_state.edited_df = None; st.session_state.data_processed = False; st.session_state.last_uploaded_filename = uploaded_file.name; convert_df_to_csv.clear()
             # Resetear mapeos si se carga archivo nuevo
             st.session_state.category_hierarchy = defaultdict(set)
             st.session_state.comercio_to_category_map = {}
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
            missing = [c for c in req_cols if c not in df_processing.columns]; assert not missing, f"Faltan: {', '.join(missing)}"
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
                       if ph == '': df_processing[c] = df_processing[c].replace('', ph)
            # Aplicar categorías fijas
            mask_traspaso = df_processing[tipo] == 'TRASPASO'; df_processing.loc[mask_traspaso, cat] = 'TRASPASO'; df_processing.loc[mask_traspaso, subcat] = 'TRASPASO INTERNO'
            mask_recibo = df_processing[tipo] == 'RECIBO'; df_processing.loc[mask_recibo, cat] = 'RECIBO'; df_processing.loc[mask_recibo, subcat] = 'PAGO RECIBO'

            # --- Derivar y guardar mapeos en Session State ---
            st.session_state.category_hierarchy = derive_category_hierarchy(df_processing, cat, subcat, ph_cat, ph_sub)
            st.session_state.comercio_to_category_map = derive_comercio_map(df_processing, com, cat, ph_cat)
            st.sidebar.info(f"{len(st.session_state.category_hierarchy)} categorías con subcategorías encontradas.")
            st.sidebar.info(f"{len(st.session_state.comercio_to_category_map)} comercios mapeados a categoría.")

            learn_categories(df_processing, desc, cat, subcat, imp_calc, ph_cat, ph_sub)
            st.session_state.edited_df = df_processing.copy()
            st.session_state.data_processed = True
            st.sidebar.success("Datos procesados.")
            st.experimental_rerun()
        except Exception as e_proc: st.error(f"Error procesando: {e_proc}"); st.code(traceback.format_exc()); st.session_state.edited_df = None; st.session_state.data_processed = False; return

    if st.session_state.get('data_processed', False) and st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy()
        tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'Año'; mes = 'Mes'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'; imp_calc = 'importe'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

        uncategorized_mask = (df[cat] == ph_cat); num_uncategorized = df[uncategorized_mask].shape[0]
        if num_uncategorized > 0: st.sidebar.warning(f"⚠️ {num_uncategorized} trans. sin CATEGORÍA.")

        # === Pestañas ===
        tab_gastos, tab_pl, tab_categorizar, tab_config = st.tabs([
            "📊 Gastos", "📈 P&L EVO", "🏷️ Categorizar", "⚙️ Configuración"
        ])

        with tab_gastos:
            # ... (Código Pestaña Gastos) ...
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
            # ... (Código Pestaña P&L) ...
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
            # ... (Código Pestaña Categorizar: Sugerir, Filtros, Editor, Aplicar, Descargar) ...
            # Asegurarse de usar las variables de columna definidas al inicio de este bloque
            if num_uncategorized > 0:
                st.info(f"Hay {num_uncategorized} transacciones sin CATEGORÍA principal.")
                if st.button("🤖 Sugerir CATEGORÍAS Faltantes", key="suggest_cats"):
                    # Redefinir locales si es necesario por scope de botón, o asegurar que las de fuera son accesibles
                    cat_btn = cat; subcat_btn = subcat; desc_btn = desc; imp_calc_btn = imp_calc; ph_cat_btn = ph_cat; ph_sub_btn = ph_sub; com_btn = com # Renombrar para claridad
                    suggestions_applied = 0; df_suggest = st.session_state.edited_df.copy()
                    suggest_mask = (df_suggest[cat_btn] == ph_cat_btn); indices_to_update = df_suggest[suggest_mask].index
                    for index in indices_to_update:
                        row = df_suggest.loc[index]; sugg_result = suggest_category(row, desc_btn, imp_calc_btn, cat_btn, subcat_btn, com_btn) # Pasar com_btn
                        applied_c = False
                        if sugg_result is not None:
                           sugg_cat, sugg_sub = sugg_result
                           if sugg_cat and df_suggest.loc[index, cat_btn] == ph_cat_btn: df_suggest.loc[index, cat_btn] = sugg_cat; applied_c = True
                           # Aplicar subcat solo si actual es placeholder Y (categoría se aplicó O ya estaba bien)
                           if sugg_sub and df_suggest.loc[index, subcat_btn] == ph_sub_btn:
                               if applied_c or (sugg_cat is None and df_suggest.loc[index, cat_btn] != ph_cat_btn): df_suggest.loc[index, subcat_btn] = sugg_sub; applied_c = True # Marcar cambio si solo aplica subcat
                        if applied_c: suggestions_applied += 1
                    if suggestions_applied > 0: st.session_state.edited_df = df_suggest.copy(); st.success(f"Se aplicaron {suggestions_applied} sugerencias."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se encontraron sugerencias.")
            else: st.success("¡Todo categorizado!")

            st.subheader("Editar Transacciones")
            col_f1, col_f2, col_f3 = st.columns([1,1,2]);
            with col_f1: show_uncat_edit = st.checkbox("Solo sin CATEGORÍA", value=(num_uncategorized > 0), key='chk_uncat_edit', disabled=(num_uncategorized == 0))
            with col_f2: year_opts = ["Todos"] + sorted([int(a) for a in df[ano].dropna().unique()]); year_sel = st.selectbox("Año:", year_opts, key='sel_a_edit')
            with col_f3: txt_filter = st.text_input("Buscar Desc:", key='txt_edit_filter')
            df_display_edit = st.session_state.edited_df.copy(); display_mask = (df_display_edit[cat] == ph_cat)
            if show_uncat_edit: df_display_edit = df_display_edit[display_mask]
            if year_sel != "Todos":
                 if ano in df_display_edit.columns: df_display_edit = df_display_edit[df_display_edit[ano] == year_sel]
                 else: st.error(f"Columna '{ano}' no encontrada.")
            if txt_filter: df_display_edit = df_display_edit[df_display_edit[desc].str.contains(txt_filter, case=False, na=False)]
            df_display_edit['original_index'] = df_display_edit.index
            cats_opts = sorted([str(c) for c in st.session_state.edited_df[cat].unique() if pd.notna(c) and c != ph_cat])
            subcats_opts = sorted([str(s) for s in st.session_state.edited_df[subcat].unique() if pd.notna(s) and s != ph_sub])
            col_cfg = { cat: st.column_config.SelectboxColumn(cat, options=cats_opts, required=False), subcat: st.column_config.SelectboxColumn(subcat, options=subcats_opts, required=False), imp_calc: st.column_config.NumberColumn("Importe", format="%.2f €"), 'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"), 'original_index': None, ano: None, mes: None, }
            edited_data = st.data_editor( df_display_edit, column_config=col_cfg, use_container_width=True, num_rows="dynamic", key='data_editor_main', hide_index=True, height=400 )

            # Botón Aplicar Cambios Manuales con Validación
            if st.button("💾 Aplicar Cambios Editados", key="apply_manual_changes"):
                cat_btn = cat; subcat_btn = subcat # Usar vars definidas
                changes_manual = 0; df_session = st.session_state.edited_df; edit_cols = [cat_btn, subcat_btn]
                invalid_combinations = [] # Lista para guardar filas con errores
                valid_hierarchy = st.session_state.category_hierarchy # Obtener jerarquía

                # Iterar sobre los datos editados para aplicar y validar
                indices_edited = edited_data['original_index']
                if indices_edited.is_unique:
                    # Aplicar cambios temporalmente para validación
                    temp_df_session = df_session.copy()
                    temp_df_session.loc[indices_edited, edit_cols] = edited_data[edit_cols].values

                    # Validar combinaciones en las filas afectadas
                    for idx in indices_edited:
                        edited_cat = temp_df_session.loc[idx, cat_btn]
                        edited_subcat = temp_df_session.loc[idx, subcat_btn]
                        # Es inválido si la categoría existe en la jerarquía pero la subcategoría no está en su set,
                        # Y la subcategoría no es un placeholder o vacía (permitimos dejar subcat vacía)
                        if edited_cat in valid_hierarchy and \
                           edited_subcat not in valid_hierarchy[edited_cat] and \
                           edited_subcat != ph_sub and edited_subcat != '':
                            invalid_combinations.append({
                                "Índice": idx,
                                "Concepto": temp_df_session.loc[idx, desc],
                                "Categoría": edited_cat,
                                "Subcategoría Inválida": edited_subcat,
                                "Subcategorías Válidas": ", ".join(sorted(list(valid_hierarchy[edited_cat]))) if valid_hierarchy[edited_cat] else "Ninguna definida"
                            })

                    # Si NO hay combinaciones inválidas, aplicar los cambios a la sesión real
                    if not invalid_combinations:
                        df_session.loc[indices_edited, edit_cols] = edited_data[edit_cols].values # Aplicar de verdad
                        changes_manual = len(indices_edited) # Asumir cambios
                        st.session_state.edited_df = df_session.copy()
                        st.success(f"{changes_manual} filas actualizadas en sesión."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else:
                        # Si hay errores, NO aplicar cambios y mostrar advertencia
                        st.error("Se encontraron combinaciones de Categoría/Subcategoría inválidas. No se aplicaron los cambios.")
                        st.write("Por favor, corrige las siguientes filas:")
                        st.dataframe(pd.DataFrame(invalid_combinations), use_container_width=True)

                else: st.error("Error: Índices duplicados al aplicar.")

            # Descargar Datos
            st.subheader("Descargar Datos"); st.caption("Descarga el CSV con las últimas categorías.")
            csv_dl = convert_df_to_csv(st.session_state.edited_df)
            st.download_button( label="📥 Descargar CSV Actualizado", data=csv_dl, file_name=f"Gastos_Cat_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='dl_cat')


        # --- *** NUEVA PESTAÑA: Configuración *** ---
        with tab_config:
            st.header("⚙️ Configuración de Categorías y Comercios")
            st.write("Gestiona las relaciones entre categorías, subcategorías y comercios.")
            st.caption("Los cambios realizados aquí se guardan temporalmente en la sesión.")

            # 1. Mostrar Jerarquía Categoría -> Subcategoría
            st.subheader("Jerarquía Categoría -> Subcategorías")
            st.write("Subcategorías encontradas para cada categoría en los datos cargados:")
            hierarchy = st.session_state.category_hierarchy
            if hierarchy:
                for category, subcategories in sorted(hierarchy.items()):
                    with st.expander(f"**{category}** ({len(subcategories)} subcategorías)"):
                        if subcategories:
                            st.write(", ".join(sorted(list(subcategories))))
                        else:
                            st.write("_(Ninguna subcategoría encontrada para esta categoría)_")
            else:
                st.info("No se pudo derivar la jerarquía de categorías (quizás no hay datos categorizados).")

            # 2. Editar Mapeo Comercio -> Categoría
            st.subheader("Asignar Categoría por Defecto a Comercios")
            st.write("Puedes asignar una categoría predeterminada a comercios específicos. Esto se usará como sugerencia de máxima prioridad al categorizar.")

            # Preparar datos para el editor de comercios
            comercio_map = st.session_state.comercio_to_category_map
            # Obtener todos los comercios únicos (no vacíos) del DF actual
            all_comercios = sorted([c for c in df[com].unique() if c != ''])
            # Obtener todas las categorías únicas para el dropdown
            all_categories = sorted([c for c in df[cat].unique() if c != ph_cat])

            # Crear DataFrame para el editor
            comercio_config_list = []
            for comercio_name in all_comercios:
                comercio_config_list.append({
                    "COMERCIO": comercio_name,
                    "CATEGORÍA Asignada": comercio_map.get(comercio_name, None) # Usar None si no hay mapeo
                })
            df_comercio_config = pd.DataFrame(comercio_config_list)

            # Configurar el editor
            comercio_editor_config = {
                "COMERCIO": st.column_config.TextColumn("Comercio", disabled=True), # No editar el nombre del comercio
                "CATEGORÍA Asignada": st.column_config.SelectboxColumn(
                    "Categoría por Defecto",
                    options=[None] + all_categories, # Permitir no asignar (None)
                    required=False,
                    help="Selecciona la categoría que quieres asignar por defecto a este comercio."
                )
            }

            st.info("💡 Edita la columna 'Categoría por Defecto' para establecer o cambiar la asignación.")
            edited_comercio_data = st.data_editor(
                df_comercio_config,
                column_config=comercio_editor_config,
                key="comercio_config_editor",
                hide_index=True,
                use_container_width=True,
                num_rows="fixed" # No permitir añadir/borrar filas aquí
            )

            # Botón para guardar cambios del mapeo de comercios
            if st.button("💾 Guardar Mapeo de Comercios", key="save_comercio_map"):
                new_map = {}
                changes_detected = False
                # Reconstruir el mapa desde los datos editados
                for _, row in edited_comercio_data.iterrows():
                    comercio_name = row["COMERCIO"]
                    assigned_cat = row["CATEGORÍA Asignada"]
                    # Guardar solo si se asignó una categoría (no None)
                    if assigned_cat is not None and assigned_cat != '':
                        new_map[comercio_name] = assigned_cat
                        # Detectar si hubo un cambio real
                        if st.session_state.comercio_to_category_map.get(comercio_name) != assigned_cat:
                             changes_detected = True
                    # Detectar si se eliminó una asignación
                    elif comercio_name in st.session_state.comercio_to_category_map:
                         changes_detected = True # Se borró una existente

                if changes_detected or len(new_map) != len(st.session_state.comercio_to_category_map):
                    st.session_state.comercio_to_category_map = new_map
                    st.success("Mapeo Comercio -> Categoría actualizado en la sesión.")
                    # No es necesario rerun aquí, la sugerencia lo leerá la próxima vez
                else:
                    st.info("No se detectaron cambios en el mapeo de comercios.")

    # --- Manejo de Errores Final ---
    # Comentado para depuración
    # except Exception as e:
    #     st.error(f"Ocurrió un error inesperado: {e}"); st.code(traceback.format_exc())
    #     st.session_state.edited_df = None; st.session_state.data_processed = False

if __name__ == "__main__":
    main()
