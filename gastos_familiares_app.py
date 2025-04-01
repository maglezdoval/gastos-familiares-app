import streamlit as st
import pandas as pd
import calendar
import traceback # Asegurarse que traceback está importado

# --- (Función obtener_nombre_mes y meses_es como antes) ---
meses_es = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic" }
def obtener_nombre_mes(numero_mes):
    try: return meses_es.get(int(numero_mes), str(numero_mes))
    except (ValueError, TypeError): return str(numero_mes)

# --- (Función convert_df_to_csv como antes) ---
@st.cache_data
def convert_df_to_csv(df_to_convert):
    df_download = df_to_convert.copy()
    # Asegurar nombre original 'IMPORTE' y coma decimal para descarga/re-importación
    if 'importe' in df_download.columns: # Si existe la de cálculo (minúscula)
         df_download.rename(columns={'importe': 'IMPORTE'}, inplace=True)
    if 'IMPORTE' in df_download.columns:
        # Convertir a numérico primero para aplicar formato correctamente, luego a string con coma
        df_download['IMPORTE'] = pd.to_numeric(df_download['IMPORTE'], errors='coerce')
        df_download['IMPORTE'] = df_download['IMPORTE'].map('{:.2f}'.format).str.replace('.', ',') # Formato español
        # Rellenar NaNs que puedan surgir del to_numeric si había errores
        df_download['IMPORTE'].fillna('0,00', inplace=True)

    return df_download.to_csv(index=False, sep=';', decimal=',').encode('utf-8')


def main():
    st.set_page_config(layout="wide")
    st.title('Análisis Financiero Personal y Categorización')

    if 'edited_df' not in st.session_state: st.session_state.edited_df = None
    if 'original_df_loaded' not in st.session_state: st.session_state.original_df_loaded = None
    if 'last_uploaded_filename' not in st.session_state: st.session_state.last_uploaded_filename = None


    uploaded_file = st.file_uploader("Sube tu archivo CSV de movimientos", type=["csv"], key="file_uploader")

    if uploaded_file is not None:
        # Recargar datos si el archivo es nuevo o no hay datos en sesión
        if st.session_state.edited_df is None or st.session_state.last_uploaded_filename != uploaded_file.name:
            try:
                df_original = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                st.session_state.original_df_loaded = df_original.copy()
                st.session_state.edited_df = df_original.copy() # Empezar con copia editable
                st.session_state.last_uploaded_filename = uploaded_file.name
                st.success(f"Archivo '{uploaded_file.name}' cargado.")
                st.experimental_rerun() # Forzar re-ejecución para procesar el nuevo df
            except Exception as e:
                st.error(f"Error al cargar archivo: {e}")
                st.session_state.edited_df = None; st.session_state.original_df_loaded = None
                return
    elif st.session_state.edited_df is None:
         st.info("Por favor, sube tu archivo CSV.")
         return

    # --- Usar el DataFrame de Session State ---
    if st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy()

        try:
            # --- Procesamiento Común ---
            df.columns = df.columns.str.strip()

            # Nombres de columnas originales
            importe_original_col = 'IMPORTE'; tipo_column_name = 'TIPO'; categoria_column_name = 'CATEGORÍA'; subcategoria_column_name = 'SUBCATEGORIA'; anio_column_name = 'AÑO'; mes_column_name = 'MES'; dia_column_name = 'DIA'; descripcion_column_name = 'CONCEPTO'; comercio_column_name = 'COMERCIO'; cuenta_column_name = 'CUENTA'

            # **** CORRECCIÓN: Nombre estandarizado para cálculos ****
            importe_calculo_col = 'importe' # Usar minúscula consistentemente

            # Validar columnas originales (incluida IMPORTE original)
            required_columns_original = [importe_original_col, tipo_column_name, categoria_column_name, subcategoria_column_name, anio_column_name, mes_column_name, dia_column_name, descripcion_column_name, comercio_column_name, cuenta_column_name]
            missing_columns = [col for col in required_columns_original if col not in df.columns]
            if missing_columns:
                # Si falta la original 'IMPORTE', pero sí existe la de cálculo 'importe', no es error aquí
                if not (importe_original_col in missing_columns and importe_calculo_col in df.columns):
                    st.error(f"Error: Faltan columnas esenciales: {', '.join(missing_columns)}")
                    st.info(f"Columnas detectadas: {df.columns.tolist()}")
                    st.session_state.edited_df = None
                    st.experimental_rerun()
                    return

            # **** CORRECCIÓN: Renombrar y Convertir Importe ****
            # 1. Asegurar que la columna se llama 'importe' (minúscula)
            if importe_original_col in df.columns:
                df.rename(columns={importe_original_col: importe_calculo_col}, inplace=True)
            elif importe_calculo_col not in df.columns:
                # Si ni la original ni la renombrada existen, error
                st.error(f"Error: No se encuentra la columna de importe ('{importe_original_col}' o '{importe_calculo_col}')")
                st.session_state.edited_df = None; st.experimental_rerun(); return

            # 2. Ahora que sabemos que existe 'importe', convertir si no es numérica
            if not pd.api.types.is_numeric_dtype(df[importe_calculo_col]):
                 try:
                       df[importe_calculo_col] = df[importe_calculo_col].astype(str).str.replace(',', '.').astype(float)
                 except ValueError as e_conv:
                      st.error(f"Error al convertir '{importe_calculo_col}' a número: {e_conv}. Revise datos.")
                      # Considerar rellenar errores con 0 o NaN en lugar de parar
                      # df[importe_calculo_col] = pd.to_numeric(df[importe_calculo_col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                      return # Detener por ahora

            # --- Procesar Fecha, Año, Mes ---
            if 'Fecha' not in df.columns or not pd.api.types.is_datetime64_any_dtype(df['Fecha']) or df['Fecha'].isnull().any():
                 try:
                      df['Fecha'] = pd.to_datetime(
                           df[anio_column_name].astype(str) + '-' + df[mes_column_name].astype(str) + '-' + df[dia_column_name].astype(str),
                           format='%Y-%m-%d', errors='coerce')
                      df.dropna(subset=['Fecha'], inplace=True) # Eliminar filas que no se pudieron convertir
                      df['Año'] = df['Fecha'].dt.year.astype(int) # Asegurar que año es int
                      df['Mes'] = df['Fecha'].dt.month.astype(int) # Asegurar que mes es int
                 except Exception as e_fecha:
                      st.error(f"Error procesando fechas: {e_fecha}")
                      return

            # --- Rellenar NaNs y Vacíos en Categóricas ---
            placeholder_cat = 'SIN CATEGORÍA'; placeholder_sub = 'SIN SUBCATEGORÍA'
            fill_cols = {categoria_column_name: placeholder_cat, subcategoria_column_name: placeholder_sub, comercio_column_name: 'SIN COMERCIO', cuenta_column_name: 'SIN CUENTA', tipo_column_name: 'SIN TIPO'}
            for col, placeholder in fill_cols.items():
                 if col in df.columns:
                       # Convertir a string, reemplazar NaN y strings vacíos
                       df[col] = df[col].astype(str).replace(['', 'nan', 'NaN', None], pd.NA).fillna(placeholder)

            # --- Detección de Sin Categorizar ---
            uncategorized_mask = (df[categoria_column_name] == placeholder_cat) | (df[subcategoria_column_name] == placeholder_sub)
            num_uncategorized = df[uncategorized_mask].shape[0]
            if num_uncategorized > 0:
                 # Mostrar en la barra lateral para no saturar el main
                 st.sidebar.warning(f"⚠️ {num_uncategorized} transacciones sin categorizar.")

            # === Pestañas ===
            tab_gastos, tab_pl, tab_categorizar = st.tabs(["📊 Gastos", "📈 P&L EVO", "🏷️ Categorizar"])

            # --- PESTAÑA 1: Gastos ---
            with tab_gastos:
                # (El código de Gastos aquí, usando 'df' y aplicando filtros internos)
                # ... (Similar a la versión anterior)
                st.header("Análisis Detallado de Gastos")
                valores_gasto = ["GASTO"]
                df_gastos_tab = df[df[tipo_column_name].isin(valores_gasto)].copy()
                if not df_gastos_tab.empty:
                     st.sidebar.header("Filtros de Gastos")
                     años_gastos_disp = sorted([int(a) for a in df_gastos_tab['Año'].dropna().unique()])
                     año_gastos_sel = st.sidebar.selectbox("Año (Gastos):", años_gastos_disp, key='sel_año_gastos_tab')
                     df_gastos_año_tab = df_gastos_tab[df_gastos_tab['Año'] == año_gastos_sel]
                     if not df_gastos_año_tab.empty:
                          cuentas_gastos_disp = sorted(df_gastos_año_tab[cuenta_column_name].unique())
                          cuentas_gastos_sel = st.sidebar.multiselect(
                               "Cuentas (Gastos):", options=cuentas_gastos_disp, default=cuentas_gastos_disp, key='sel_cuenta_gastos_tab' )
                          if cuentas_gastos_sel:
                               df_gastos_año_filtrado_tab = df_gastos_año_tab[df_gastos_año_tab[cuenta_column_name].isin(cuentas_gastos_sel)].copy()
                               if not df_gastos_año_filtrado_tab.empty:
                                    st.subheader(f"Resumen Gastos ({año_gastos_sel} - Cuentas: {', '.join(cuentas_gastos_sel)})")
                                    try: # Tabla Pivote Gastos
                                         tabla_gastos_pivot = df_gastos_año_filtrado_tab.pivot_table(values=importe_calculo_col, index=categoria_column_name, columns='Mes', aggfunc='sum', fill_value=0, margins=True, margins_name='Total')
                                         formato_euro_gasto = '{:,.0f} €'.format
                                         estilo_gasto = [ {'selector': 'th.col_heading, th.row_heading', 'props': [('background-color', '#6c757d'), ('color', 'white'), ('font-weight', 'bold')]}, {'selector': 'th.col_heading', 'props': [('text-align', 'center')]}, {'selector': 'th.row_heading', 'props': [('text-align', 'left')]}, {'selector': 'tr:last-child td, td:last-child', 'props': [('font-weight', 'bold'), ('background-color', '#f8f9fa')]} ]
                                         st.dataframe(tabla_gastos_pivot.style.format(formato_euro_gasto).set_table_styles(estilo_gasto), use_container_width=True)
                                    except Exception as e_pivot_gasto: st.error(f"Error tabla pivote gastos: {e_pivot_gasto}")
                                    # Detalle Interactivo Gastos
                                    # ... (código similar al anterior, con selectboxes y dataframe filtrado) ...
                               else: st.info("No hay gastos para la selección actual.")
                          else: st.warning("Seleccione cuentas para el análisis de gastos.")
                     else: st.info(f"No hay gastos para el año {año_gastos_sel}.")
                else: st.info("No hay registros de GASTO en los datos.")


            # --- PESTAÑA 2: P&L ---
            with tab_pl:
                # (El código de P&L aquí, usando 'df' y filtros internos)
                # ... (Similar a la versión anterior)
                 st.header("Análisis P&L - Cuenta Familiar (EVO)")
                 df_evo_tab = df[df[cuenta_column_name] == 'EVO'].copy()
                 if not df_evo_tab.empty:
                      st.sidebar.header("Filtro P&L (EVO)")
                      años_evo_disp = sorted([int(a) for a in df_evo_tab['Año'].dropna().unique()])
                      año_pl_sel = st.sidebar.selectbox("Año (P&L):", años_evo_disp, key='sel_año_pl_tab')
                      df_evo_año_tab = df_evo_tab[df_evo_tab['Año'] == año_pl_sel]
                      if not df_evo_año_tab.empty:
                           tipos_ingreso = ['TRASPASO', 'INGRESO', 'REEMBOLSO'] # Revisar/ajustar
                           df_ingresos = df_evo_año_tab[df_evo_año_tab[tipo_column_name].isin(tipos_ingreso)]
                           ingresos_mensuales = df_ingresos.groupby('Mes')[importe_calculo_col].sum()
                           tipos_egreso = ['GASTO'] # Revisar/ajustar
                           df_egresos = df_evo_año_tab[df_evo_año_tab[tipo_column_name].isin(tipos_egreso)]
                           egresos_mensuales_abs = df_egresos.groupby('Mes')[importe_calculo_col].sum().abs()
                           df_pl = pd.DataFrame({'Ingresos': ingresos_mensuales, 'Egresos': egresos_mensuales_abs}).fillna(0)
                           df_pl['Resultado'] = df_pl['Ingresos'] - df_pl['Egresos']
                           total_pl = df_pl.sum(); total_pl.name = 'Total'
                           df_pl = pd.concat([df_pl, total_pl.to_frame().T])
                           df_pl.index = df_pl.index.map(obtener_nombre_mes)
                           formato_euro_pl = '{:,.2f} €'.format
                           df_pl_formateado = df_pl.style.format(formato_euro_pl).applymap(lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else 'color: black'), subset=['Resultado']).set_properties(**{'text-align': 'right'})
                           st.subheader(f"Tabla P&L Mensual ({año_pl_sel}) - Cuenta EVO")
                           st.dataframe(df_pl_formateado, use_container_width=True)
                           df_pl_chart = df_pl.drop('Total')
                           try: # Reordenar gráfico
                                mes_num_map = {v: k for k, v in meses_es.items()}
                                df_pl_chart.index = df_pl_chart.index.map(mes_num_map.get)
                                df_pl_chart = df_pl_chart.sort_index()
                           except: pass
                           st.subheader(f"Gráfico P&L Mensual ({año_pl_sel}) - Cuenta EVO")
                           st.line_chart(df_pl_chart[['Ingresos', 'Egresos']])
                      else: st.info(f"No hay datos para EVO en {año_pl_sel}.")
                 else: st.info("No se encontraron transacciones para la cuenta EVO.")


            # --- PESTAÑA 3: Categorizar ---
            with tab_categorizar:
                 st.header("Revisión y Categorización de Transacciones")
                 if num_uncategorized > 0:
                     st.info(f"Encontradas {num_uncategorized} transacciones con '{placeholder_cat}' o '{placeholder_sub}'.")

                 # Obtener listas actuales para dropdowns (excluyendo placeholders)
                 categorias_existentes = sorted([cat for cat in df[categoria_column_name].unique() if cat != placeholder_cat])
                 subcategorias_existentes = sorted([sub for sub in df[subcategoria_column_name].unique() if sub != placeholder_sub])

                 st.subheader("Editar Transacciones")
                 st.caption("Filtra las transacciones y edita las columnas 'CATEGORÍA' o 'SUBCATEGORIA' haciendo doble clic.")

                 # Filtros para la edición
                 col_f1, col_f2, col_f3 = st.columns([1,1,2])
                 with col_f1: show_uncat_edit = st.checkbox("Mostrar solo sin categorizar", value=(num_uncategorized > 0), key='chk_uncat_edit')
                 with col_f2: year_edit_opts = ["Todos"] + sorted([int(a) for a in df['Año'].dropna().unique()])
                              year_edit_sel = st.selectbox("Año:", year_edit_opts, key='sel_año_edit')
                 with col_f3: txt_edit_filter = st.text_input("Buscar en Descripción:", key='txt_edit_filter')

                 df_filtered_for_edit = df.copy()
                 if show_uncat_edit: df_filtered_for_edit = df_filtered_for_edit[uncategorized_mask]
                 if year_edit_sel != "Todos": df_filtered_for_edit = df_filtered_for_edit[df_filtered_for_edit['Año'] == year_edit_sel]
                 if txt_edit_filter: df_filtered_for_edit = df_filtered_for_edit[df_filtered_for_edit[descripcion_column_name].str.contains(txt_edit_filter, case=False, na=False)]

                 # Configurar data_editor
                 column_config = {
                      categoria_column_name: st.column_config.SelectboxColumn(f"{categoria_column_name}", options=categorias_existentes, required=False),
                      subcategoria_column_name: st.column_config.SelectboxColumn(f"{subcategoria_column_name}", options=subcategorias_existentes, required=False),
                      importe_calculo_col: st.column_config.NumberColumn("Importe", format="%.2f €"),
                      # Ocultar algunas columnas para simplificar la vista de edición
                      anio_column_name: None, mes_column_name: None, dia_column_name: None, 'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"),
                 }

                 # Usar el índice original del DataFrame para poder actualizar st.session_state.edited_df
                 df_filtered_for_edit['original_index'] = df_filtered_for_edit.index
                 edited_data = st.data_editor(
                      df_filtered_for_edit,
                      column_config=column_config,
                      use_container_width=True,
                      num_rows="dynamic", # O "fixed" si no quieres permitir añadir/borrar filas
                      key='data_editor_main',
                      hide_index=True,
                      # disabled=[col for col in df_filtered_for_edit.columns if col not in [categoria_column_name, subcategoria_column_name, 'original_index']] # Deshabilitar edición de otras columnas
                 )

                 # Botón para aplicar cambios a la sesión
                 if st.button("💾 Aplicar Cambios a la Sesión", key="apply_changes"):
                     # Actualizar el DataFrame principal ('df' que viene de session_state) con los cambios
                     # Usar 'original_index' para mapear las ediciones
                     changes_applied = 0
                     for idx, row in edited_data.iterrows():
                          original_idx = row['original_index']
                          # Compara fila editada con la original en df usando el índice
                          original_row = df.loc[original_idx]
                          # Columnas editables
                          editable_cols = [categoria_column_name, subcategoria_column_name]
                          for col in editable_cols:
                              if row[col] != original_row[col]:
                                  df.loc[original_idx, col] = row[col]
                                  changes_applied += 1

                     if changes_applied > 0:
                          st.session_state.edited_df = df.copy() # Guardar df actualizado en sesión
                          st.success(f"{changes_applied} cambios aplicados a la sesión.")
                          st.experimental_rerun() # Re-ejecutar para reflejar cambios en otras pestañas
                     else:
                          st.info("No se detectaron cambios para aplicar.")

                 st.subheader("Descargar Datos")
                 st.caption("Descarga el archivo CSV completo con las últimas categorías guardadas en la sesión.")
                 csv_data = convert_df_to_csv(st.session_state.edited_df)
                 st.download_button(
                     label="📥 Descargar CSV Actualizado", data=csv_data,
                     file_name=f"Gastos_Categorizado_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='download_csv')


        # --- Manejo de Errores General ---
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            st.error("Detalle del error:")
            st.code(traceback.format_exc())
            st.session_state.edited_df = None # Resetear en error

if __name__ == "__main__":
    main()
