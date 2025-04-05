import streamlit as st
import pandas as pd
import calendar
import traceback
import re
from collections import Counter

# --- (Funciones auxiliares: obtener_nombre_mes, convert_df_to_csv, clean_text, learn_categories, suggest_category - sin cambios) ---
# ... (Incluye aquí las definiciones completas de estas funciones de la respuesta anterior) ...
meses_es = { 1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic" }
def obtener_nombre_mes(n): try: return meses_es.get(int(n), str(n)); except: return str(n)
@st.cache_data
def convert_df_to_csv(df): # Renombrado argumento para claridad
    df_download = df.copy(); # ... (resto de la función como antes) ...
    if 'importe' in df_download.columns: df_download.rename(columns={'importe': 'IMPORTE'}, inplace=True)
    if 'IMPORTE' in df_download.columns:
        df_download['IMPORTE'] = pd.to_numeric(df_download['IMPORTE'], errors='coerce')
        df_download['IMPORTE'] = df_download['IMPORTE'].map('{:.2f}'.format).str.replace('.', ',', regex=False); df_download['IMPORTE'].fillna('0,00', inplace=True)
    df_download = df_download.drop(columns=['original_index', 'temp_id'], errors='ignore')
    return df_download.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
def clean_text(t): # Abreviado nombre argumento
    if not isinstance(t, str): return ""; t = t.lower(); t = re.sub(r'\b\d{4,}\b', '', t); t = re.sub(r'\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?', '', t); t = re.sub(r'[^\w\s]', ' ', t); t = re.sub(r'\s+', ' ', t).strip(); return t
category_knowledge = {"keyword_map": {},"amount_map": {}}
keywords_to_ignore = { 'pago', 'movil', 'en', 'compra', 'tarjeta', 'tarj', 'internet', 'comision', 'recibo', 'favor', 'de', 'la', 'el', 'los', 'las', 'a', 'con', 'sl', 'sa', 'sau', 's l', 'concepto', 'nº', 'ref', 'mandato', 'cuenta', 'gastos', 'varios', 'madrid', 'huelva', 'rozas', 'espanola', 'europe', 'fecha', 'num', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre', 'transferencia', 'trf', 'bizum', 'liquidacin', 'contrato', 'impuesto', 'cotizacion', 'tgss', 'iban', 'swift', 'com', 'www', 'http', 'https', 'cliente', 'importe', 'saldo', 'valor', 'atm', 'reintegro', 'oficina', 'suc', 'sr', 'sra', 'dna', 'bill', 'pending', 'uber', 'comercial', 'petroleo', 'obo', 'inv', 'for', 'sueldo', 'salar', 'nombre', 'miguel', 'angel', 'gonzalez', 'doval', 'alicia', 'jimenez', 'corpa', 'ordenante', 'beneficiario' }
def learn_categories(df, concepto_col, cat_col, subcat_col, importe_col, ph_cat, ph_sub): # abreviado placeholders
    global category_knowledge; kw_counter = {}; amt_counter = {}
    df_cat = df[(df[cat_col] != ph_cat) & (df[subcat_col] != ph_sub)].copy()
    if df_cat.empty: return
    df_cat['clean'] = df_cat[concepto_col].apply(clean_text)
    for _, r in df_cat.iterrows():
        cat, subcat, imp = r[cat_col], r[subcat_col], r[importe_col]
        amt_bin = int(round(imp / 10) * 10) if pd.notna(imp) and isinstance(imp, (int, float)) else 0
        words = set(r['clean'].split()) - keywords_to_ignore
        for w in words:
            if len(w) < 4: continue
            kw_counter.setdefault(w, Counter())[(cat, subcat)] += 1
            amt_counter.setdefault((w, amt_bin), Counter())[(cat, subcat)] += 1
    category_knowledge["keyword_map"] = {w: c.most_common(1)[0][0] for w, c in kw_counter.items() if c}
    category_knowledge["amount_map"] = {k: c.most_common(1)[0][0] for k, c in amt_counter.items() if c}
    st.sidebar.info(f"Aprendizaje: {len(category_knowledge['keyword_map'])} keywords.")
def suggest_category(row, concepto_col, importe_col, cat_col, subcat_col):
    global category_knowledge; concepto = row[concepto_col]; importe = row[importe_col]; concepto_lower = str(concepto).lower(); current_subcat_lower = str(row[subcat_col]).lower()
    # --- 1. Reglas Explícitas ---
    # ... (tus reglas explícitas aquí) ...
    if "mercadona" in concepto_lower: return ('ALIMENTACIÓN', 'SUPERMERCADO') # Ejemplo
    # --- 2. Conocimiento Aprendido ---
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
    return best_sugg if best_sugg else (None, None)

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
            req_cols = [imp_orig, tipo, cat, subcat, ano, mes, dia, desc, com, cta]; missing = [c for c in req_cols if c not in df_processing.columns]; assert not missing, f"Faltan: {', '.join(missing)}"
            df_processing.rename(columns={imp_orig: imp_calc}, inplace=True)
            df_processing[imp_calc] = pd.to_numeric(df_processing[imp_calc].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
            df_processing[ano]=df_processing[ano].astype(str); df_processing[mes]=df_processing[mes].astype(str).str.zfill(2); df_processing[dia]=df_processing[dia].astype(str).str.zfill(2)
            df_processing['Fecha'] = pd.to_datetime(df_processing[ano] + '-' + df_processing[mes] + '-' + df_processing[dia], format='%Y-%m-%d', errors='coerce')
            n_inv = df_processing['Fecha'].isnull().sum();
            if n_inv > 0: st.warning(f"{n_inv} filas con fechas inválidas eliminadas.")
            df_processing.dropna(subset=['Fecha'], inplace=True)
            df_processing['Año'] = df_processing['Fecha'].dt.year.astype(int); df_processing['Mes'] = df_processing['Fecha'].dt.month.astype(int)
            ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'
            fill_cols = {cat: ph_cat, subcat: ph_sub, com: '', cta: 'SIN CUENTA', tipo: 'SIN TIPO'}
            for c, ph in fill_cols.items():
                 if c in df_processing.columns: df_processing[c] = df_processing[c].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], pd.NA).fillna(ph); df_processing[c].replace('', ph, inplace=True) # Asegurar '' se reemplaza si placeholder no es ''
            learn_categories(df_processing, desc, cat, subcat, imp_calc, ph_cat, ph_sub)
            st.session_state.edited_df = df_processing.copy()
            st.session_state.data_processed = True
            st.experimental_rerun()
        except Exception as e_proc: st.error(f"Error procesando: {e_proc}"); st.code(traceback.format_exc()); st.session_state.edited_df = None; st.session_state.data_processed = False; return

    if st.session_state.get('data_processed', False) and st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy()
        tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'Año'; mes = 'Mes'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'; imp_calc = 'importe'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

        uncategorized_mask = (df[cat] == ph_cat) # Basado solo en categoría principal
        num_uncategorized = df[uncategorized_mask].shape[0]
        if num_uncategorized > 0: st.sidebar.warning(f"⚠️ {num_uncategorized} transacciones sin CATEGORÍA.")

        tab_gastos, tab_pl, tab_categorizar = st.tabs(["📊 Gastos", "📈 P&L EVO", "🏷️ Categorizar"])

        with tab_gastos:
            # ... (Código Gastos, usando nombres de variable cortos: tipo, cat, subcat, ano, mes, cta, imp_calc) ...
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
                                     fmt = '{:,.0f} €'; sty = [ {'selector': 'th...', 'props': [('...', '...')]},{'...'} ] # Estilos completos aquí
                                     st.dataframe(piv_g.style.format(fmt).set_table_styles(sty), use_container_width=True) # Usar estilos
                                except Exception as e: st.error(f"Error pivote G: {e}")
                                # Detalle Gastos
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
            # ... (Código P&L, usando nombres cortos) ...
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
            if num_uncategorized > 0:
                st.info(f"Hay {num_uncategorized} transacciones sin CATEGORÍA principal.")
                # --- Botón Sugerir ---
                if st.button("🤖 Sugerir CATEGORÍAS Faltantes", key="suggest_cats"):
                    suggestions_applied = 0
                    df_suggest = st.session_state.edited_df.copy() # Trabajar sobre copia de sesión
                    # Asegurar que 'importe' existe y es numérico en la copia
                    if imp_orig in df_suggest.columns: df_suggest.rename(columns={imp_orig: imp_calc}, inplace=True)
                    if imp_calc not in df_suggest.columns: raise KeyError("Falta columna de importe en df_suggest")
                    if not pd.api.types.is_numeric_dtype(df_suggest[imp_calc]):
                        df_suggest[imp_calc] = pd.to_numeric(df_suggest[imp_calc].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                    # Identificar índices a actualizar en la copia
                    current_mask = (df_suggest[cat] == ph_cat)
                    indices_to_update = df_suggest[current_mask].index

                    # Iterar y aplicar sugerencias a la copia
                    for index in indices_to_update:
                        row = df_suggest.loc[index]
                        sugg_cat, sugg_sub = suggest_category(row, desc, imp_calc, cat, subcat)
                        applied_c = False
                        if sugg_cat and df_suggest.loc[index, cat] == ph_cat:
                            df_suggest.loc[index, cat] = sugg_cat
                            applied_c = True
                        if sugg_sub and df_suggest.loc[index, subcat] == ph_sub:
                            if applied_c or (sugg_cat is None and df_suggest.loc[index, cat] != ph_cat):
                                df_suggest.loc[index, subcat] = sugg_sub
                                applied_c = True # Asegurar conteo si solo se aplica subcat
                        if applied_c: suggestions_applied += 1

                    # Actualizar sesión si hubo cambios
                    if suggestions_applied > 0:
                        st.session_state.edited_df = df_suggest.copy() # Guardar la copia modificada
                        st.success(f"Se aplicaron {suggestions_applied} sugerencias.")
                        convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se encontraron sugerencias.")
            else: st.success("¡Todo categorizado!")

            # --- Filtros y Editor ---
            st.subheader("Editar Transacciones")
            col_f1, col_f2, col_f3 = st.columns([1,1,2]);
            with col_f1:
                # *** Usar num_uncategorized calculado al principio de la sección ***
                show_uncat_edit = st.checkbox("Solo sin CATEGORÍA", value=(num_uncategorized > 0), key='chk_uncat_edit', disabled=(num_uncategorized == 0))
            with col_f2: year_opts = ["Todos"] + sorted([int(a) for a in df[ano].dropna().unique()]); year_sel = st.selectbox("Año:", year_opts, key='sel_a_edit')
            with col_f3: txt_filter = st.text_input("Buscar Desc:", key='txt_edit_filter')

            # Aplicar filtros para mostrar en editor
            df_display = st.session_state.edited_df.copy()
            # *** Recalcular máscara sobre df_display ***
            display_mask = (df_display[cat] == ph_cat)
            if show_uncat_edit: df_display = df_display[display_mask]
            if year_sel != "Todos":
                 if ano in df_display.columns: df_display = df_display[df_display[ano] == year_sel]
                 else: st.error(f"Columna '{ano}' no encontrada.")
            if txt_filter: df_display = df_display[df_display[desc].str.contains(txt_filter, case=False, na=False)]
            df_display['original_index'] = df_display.index

            # Opciones para Selectbox (basadas en el df completo de sesión)
            cats_opts = sorted([str(c) for c in st.session_state.edited_df[cat].unique() if pd.notna(c) and c != ph_cat])
            subcats_opts = sorted([str(s) for s in st.session_state.edited_df[subcat].unique() if pd.notna(s) and s != ph_sub])

            col_cfg = { cat: st.column_config.SelectboxColumn(cat, options=cats_opts, required=False), subcat: st.column_config.SelectboxColumn(subcat, options=subcats_opts, required=False), imp_calc: st.column_config.NumberColumn("Importe", format="%.2f €"), 'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"), 'original_index': None, ano: None, mes: None, }
            edited_data = st.data_editor( df_display, column_config=col_cfg, use_container_width=True, num_rows="dynamic", key='data_editor_main', hide_index=True, height=400 )

            # Botón Aplicar Cambios Manuales
            if st.button("💾 Aplicar Cambios Editados", key="apply_manual_changes"):
                changes_manual = 0; df_session = st.session_state.edited_df; edit_cols = [cat, subcat]
                # Iterar sobre los datos mostrados/editados
                indices_edited_rows = edited_data['original_index']
                df_original_rows = df_session.loc[indices_edited_rows] # Filas originales correspondientes

                # Comparar edited_data con las filas originales
                # Nota: Esto requiere que los índices coincidan bien
                # Simplificación: Iterar sobre edited_data y actualizar df_session por índice original
                for _, edited_row in edited_data.iterrows():
                    orig_idx = edited_row['original_index']
                    if orig_idx in df_session.index:
                        for c in edit_cols:
                             if c in edited_row and edited_row[c] != df_session.loc[orig_idx, c]:
                                  df_session.loc[orig_idx, c] = edited_row[c]
                                  changes_manual += 1
                    # else: st.warning(f"Índice {orig_idx} no encontrado al aplicar") # Debug

                if changes_manual > 0:
                     st.session_state.edited_df = df_session.copy() # Guardar df actualizado
                     st.success(f"{changes_manual} cambios manuales aplicados."); convert_df_to_csv.clear(); st.experimental_rerun()
                else: st.info("No se detectaron cambios manuales.")

            # Descargar Datos
            st.subheader("Descargar Datos"); st.caption("Descarga el CSV con las últimas categorías.")
            csv_dl = convert_df_to_csv(st.session_state.edited_df)
            st.download_button( label="📥 Descargar CSV Actualizado", data=csv_dl, file_name=f"Gastos_Cat_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='dl_cat')


# --- Manejo de Errores Final ---
# (Este except captura errores de procesamiento y de las pestañas)
# Comentado temporalmente para ver errores específicos si los hay
#    except Exception as e:
#        st.error(f"Ocurrió un error inesperado en la aplicación: {e}")
#        st.error("Detalle del error:")
#        st.code(traceback.format_exc())
#        st.session_state.edited_df = None
#        st.session_state.data_processed = False


if __name__ == "__main__":
    main()
