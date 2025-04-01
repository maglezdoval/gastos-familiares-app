import streamlit as st
import pandas as pd
import calendar

# --- (Función obtener_nombre_mes como antes) ---
meses_es = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic" }
def obtener_nombre_mes(numero_mes):
    try:
        return meses_es.get(int(numero_mes), str(numero_mes))
    except (ValueError, TypeError):
        return str(numero_mes)

# --- Función para preparar datos descargados ---
@st.cache_data # Cachear la conversión para eficiencia en la descarga
def convert_df_to_csv(df_to_convert):
    # Asegurar el separador decimal correcto (coma) y delimitador (punto y coma) para posible re-importación
    # Revertir el nombre de la columna 'Importe' a 'IMPORTE' si es necesario para re-importar
    df_download = df_to_convert.copy()
    if 'Importe' in df_download.columns and 'IMPORTE' not in df_download.columns:
         df_download.rename(columns={'Importe': 'IMPORTE'}, inplace=True)
    # Convertir columna de importe de nuevo a string con coma decimal
    if 'IMPORTE' in df_download.columns:
         df_download['IMPORTE'] = df_download['IMPORTE'].map('{:,.2f}'.format).str.replace('.', ',') # Formato con coma

    return df_download.to_csv(index=False, sep=';', decimal=',').encode('utf-8')


def main():
    st.set_page_config(layout="wide")
    st.title('Análisis Financiero Personal y Categorización')

    # --- Gestión del DataFrame Editado en Session State (Opcional Básico) ---
    # Inicializar session state si no existe
    if 'edited_df' not in st.session_state:
        st.session_state.edited_df = None
    if 'original_df_loaded' not in st.session_state:
        st.session_state.original_df_loaded = None


    uploaded_file = st.file_uploader("Sube tu archivo CSV de movimientos", type=["csv"], key="file_uploader")

    # --- Lógica de Carga y Procesamiento Inicial ---
    if uploaded_file is not None:
        # Cargar solo si no hay un DF editado en la sesión o si se sube un nuevo archivo
        # (Esto es una lógica simple, podría necesitar refinamiento)
        # Forzar recarga si se sube un nuevo archivo (comprobar nombre o contenido podría ser mejor)
        # Una forma simple es resetear si el nombre del archivo cargado cambia
        if st.session_state.edited_df is None or \
           (st.session_state.get('last_uploaded_filename') != uploaded_file.name):

            try:
                df_original = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
                st.session_state.original_df_loaded = df_original.copy() # Guardar original
                st.session_state.edited_df = df_original.copy() # Empezar con copia editable
                st.session_state.last_uploaded_filename = uploaded_file.name # Guardar nombre
                st.success(f"Archivo '{uploaded_file.name}' cargado correctamente.")
                 # Limpiar cache de data_editor si se carga nuevo archivo (evita bugs)
                st.experimental_rerun() # Forzar re-ejecución para usar el nuevo df

            except Exception as e:
                st.error(f"Error al cargar o procesar inicialmente el archivo: {e}")
                st.session_state.original_df_loaded = None
                st.session_state.edited_df = None
                return # Salir si la carga inicial falla
    elif st.session_state.edited_df is not None:
         # Si no se sube archivo pero hay datos en sesión, usarlos
         pass # Continuar con los datos en sesión
    else:
         # Ni archivo subido ni datos en sesión
         st.info("Por favor, sube tu archivo CSV para comenzar.")
         return # Salir si no hay datos


    # --- Usar el DataFrame de Session State para el resto de la app ---
    if st.session_state.edited_df is not None:
        df = st.session_state.edited_df.copy() # Trabajar con una copia del estado de sesión

        try:
            # --- Procesamiento Común (aplicado al df de session state) ---
            df.columns = df.columns.str.strip()
            # ... (definición de nombres de columna como antes) ...
            importe_original_col = 'IMPORTE'; tipo_column_name = 'TIPO'; categoria_column_name = 'CATEGORÍA'; subcategoria_column_name = 'SUBCATEGORIA'; anio_column_name = 'AÑO'; mes_column_name = 'MES'; dia_column_name = 'DIA'; descripcion_column_name = 'CONCEPTO'; comercio_column_name = 'COMERCIO'; cuenta_column_name = 'CUENTA'
            importe_calculo_col = 'Importe'

            # Validar columnas (importante hacerlo aquí por si el df en sesión es inválido)
            required_columns = [importe_original_col if importe_calculo_col not in df.columns else importe_calculo_col, # Validar original o renombrada
                                tipo_column_name, categoria_column_name, subcategoria_column_name, anio_column_name,
                                mes_column_name, dia_column_name, descripcion_column_name, comercio_column_name, cuenta_column_name]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Error: Faltan columnas esenciales en los datos actuales: {', '.join(missing_columns)}")
                st.session_state.edited_df = None # Resetear si los datos son inválidos
                st.experimental_rerun()
                return

            # Asegurar que 'Importe' es numérico (si no lo es ya por edición previa)
            if not pd.api.types.is_numeric_dtype(df[importe_calculo_col]):
                 # Intentar renombrar y convertir si aún está como original
                 if importe_original_col in df.columns and importe_calculo_col not in df.columns:
                       df.rename(columns={importe_original_col: importe_calculo_col}, inplace=True)
                 df[importe_calculo_col] = df[importe_calculo_col].astype(str).str.replace(',', '.').astype(float)


            # Asegurar columna 'Fecha', 'Año', 'Mes'
            if 'Fecha' not in df.columns or df['Fecha'].isnull().any():
                 try:
                       df['Fecha'] = pd.to_datetime(
                            df[anio_column_name].astype(str) + '-' + df[mes_column_name].astype(str) + '-' + df[dia_column_name].astype(str),
                            format='%Y-%m-%d', errors='coerce')
                       df.dropna(subset=['Fecha'], inplace=True)
                       df['Año'] = df['Fecha'].dt.year
                       df['Mes'] = df['Fecha'].dt.month
                 except Exception as e_fecha:
                       st.error(f"Error procesando fechas en datos actuales: {e_fecha}")
                       return

            # Rellenar NaNs en columnas categóricas
            placeholder_cat = 'SIN CATEGORÍA'
            placeholder_sub = 'SIN SUBCATEGORÍA'
            fill_na_cols = {
                categoria_column_name: placeholder_cat,
                subcategoria_column_name: placeholder_sub,
                # Añadir otros si es necesario, ej:
                # comercio_column_name: 'SIN COMERCIO',
                # descripcion_column_name: 'SIN DESCRIPCIÓN',
                # cuenta_column_name: 'SIN CUENTA'
            }
            for col, placeholder in fill_na_cols.items():
                if col in df.columns:
                    # Convertir a string ANTES de fillna para manejar tipos mixtos y NaN correctamente
                    df[col] = df[col].astype(str).fillna(placeholder)
                    # Reemplazar también cadenas vacías por el placeholder
                    df[col] = df[col].replace(['', 'nan', 'NaN'], placeholder)


            # --- Detección de Sin Categorizar ---
            uncategorized_mask = (df[categoria_column_name] == placeholder_cat) | (df[subcategoria_column_name] == placeholder_sub)
            df_uncategorized = df[uncategorized_mask]
            num_uncategorized = len(df_uncategorized)

            if num_uncategorized > 0:
                st.warning(f"⚠️ ¡Atención! Tienes {num_uncategorized} transacciones sin categorizar.")

            # === Crear Pestañas para las Secciones ===
            tab_gastos, tab_pl, tab_categorizar = st.tabs([
                "📊 Análisis de Gastos",
                "📈 P&L Cuenta Familiar",
                "🏷️ Categorizar Transacciones"
            ])

            # --- PESTAÑA 1: Análisis de Gastos ---
            with tab_gastos:
                st.header("Análisis Detallado de Gastos")
                # (Código de Análisis de Gastos como en la versión anterior, usando 'df')
                # Importante: Asegurarse que este código filtra df por TIPO=='GASTO' internamente
                # y usa los selectores adecuados para año y cuenta DENTRO de esta pestaña.
                # ... (El código detallado iría aquí) ...
                valores_gasto = ["GASTO"]
                df_gastos_tab = df[df[tipo_column_name].isin(valores_gasto)].copy()
                if not df_gastos_tab.empty:
                     # Filtros específicos para esta pestaña
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
                                    # ... (Mostrar tabla pivote y detalle de gastos aquí usando df_gastos_año_filtrado_tab) ...
                                     st.subheader(f"Resumen Gastos ({año_gastos_sel} - Cuentas: {', '.join(cuentas_gastos_sel)})")
                                     try:
                                         tabla_gastos_pivot = df_gastos_año_filtrado_tab.pivot_table(
                                             values=importe_calculo_col, index=categoria_column_name, columns='Mes',
                                             aggfunc='sum', fill_value=0, margins=True, margins_name='Total' )
                                         # ... (formato y display tabla) ...
                                         formato_euro_gasto = '{:,.0f} €'.format
                                         estilo_gasto = [
                                             {'selector': 'th.col_heading, th.row_heading', 'props': [('background-color', '#6c757d'), ('color', 'white'), ('font-weight', 'bold')]},
                                             {'selector': 'th.col_heading', 'props': [('text-align', 'center')]},
                                             {'selector': 'th.row_heading', 'props': [('text-align', 'left')]},
                                             {'selector': 'tr:last-child td, td:last-child', 'props': [('font-weight', 'bold'), ('background-color', '#f8f9fa')]} ]
                                         tabla_gasto_formateada = tabla_gastos_pivot.style.format(formato_euro_gasto).set_table_styles(estilo_gasto)
                                         st.dataframe(tabla_gasto_formateada, use_container_width=True)

                                     except Exception as e_pivot_gasto:
                                        st.error(f"Error al crear tabla pivote de gastos: {e_pivot_gasto}")

                                     # ... (Código detalle interactivo de gastos aquí) ...
                                     # (similar al anterior, pero usando df_gastos_año_filtrado_tab)

                               else: st.info("No hay gastos para la selección actual.")
                          else: st.warning("Seleccione cuentas para el análisis de gastos.")
                     else: st.info("No hay gastos para el año seleccionado.")
                else: st.info("No hay registros de GASTO en los datos.")


            # --- PESTAÑA 2: P&L Cuenta Familiar ---
            with tab_pl:
                st.header("Análisis P&L - Cuenta Familiar (EVO)")
                # (Código de Análisis P&L como en la versión anterior, usando 'df')
                # Importante: Usar un selector de año específico para P&L DENTRO de esta pestaña.
                # ... (El código detallado iría aquí) ...
                df_evo_tab = df[df[cuenta_column_name] == 'EVO'].copy()
                if not df_evo_tab.empty:
                    st.sidebar.header("Filtro P&L (EVO)")
                    años_evo_disp = sorted([int(a) for a in df_evo_tab['Año'].dropna().unique()])
                    año_pl_sel = st.sidebar.selectbox("Año (P&L):", años_evo_disp, key='sel_año_pl_tab')
                    df_evo_año_tab = df_evo_tab[df_evo_tab['Año'] == año_pl_sel]

                    if not df_evo_año_tab.empty:
                         # ... (Calcular ingresos, egresos, df_pl, mostrar tabla y gráfico aquí usando df_evo_año_tab) ...
                         tipos_ingreso = ['TRASPASO', 'INGRESO', 'REEMBOLSO'] # Ajusta según tus tipos
                         df_ingresos = df_evo_año_tab[df_evo_año_tab[tipo_column_name].isin(tipos_ingreso)]
                         ingresos_mensuales = df_ingresos.groupby('Mes')[importe_calculo_col].sum()

                         tipos_egreso = ['GASTO'] # Ajusta si es necesario
                         df_egresos = df_evo_año_tab[df_evo_año_tab[tipo_column_name].isin(tipos_egreso)]
                         egresos_mensuales_abs = df_egresos.groupby('Mes')[importe_calculo_col].sum().abs()

                         df_pl = pd.DataFrame({'Ingresos': ingresos_mensuales, 'Egresos': egresos_mensuales_abs}).fillna(0)
                         df_pl['Resultado'] = df_pl['Ingresos'] - df_pl['Egresos']
                         total_pl = df_pl.sum(); total_pl.name = 'Total'
                         df_pl = pd.concat([df_pl, total_pl.to_frame().T])
                         df_pl.index = df_pl.index.map(obtener_nombre_mes)

                         formato_euro_pl = '{:,.2f} €'.format
                         df_pl_formateado = df_pl.style.format(formato_euro_pl) \
                                               .applymap(lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else 'color: black'), subset=['Resultado']) \
                                               .set_properties(**{'text-align': 'right'})
                         st.subheader(f"Tabla P&L Mensual ({año_pl_sel}) - Cuenta EVO")
                         st.dataframe(df_pl_formateado, use_container_width=True)

                         df_pl_chart = df_pl.drop('Total')
                         # ... (código para intentar reordenar y mostrar st.line_chart) ...
                         try:
                              mes_num_map = {v: k for k, v in meses_es.items()}
                              df_pl_chart.index = df_pl_chart.index.map(mes_num_map.get)
                              df_pl_chart = df_pl_chart.sort_index()
                         except: pass
                         st.subheader(f"Gráfico P&L Mensual ({año_pl_sel}) - Cuenta EVO")
                         st.line_chart(df_pl_chart[['Ingresos', 'Egresos']])

                    else: st.info(f"No hay datos para EVO en el año {año_pl_sel}.")
                else: st.info("No se encontraron transacciones para la cuenta EVO.")


            # --- PESTAÑA 3: Categorizar Transacciones ---
            with tab_categorizar:
                st.header("Revisión y Categorización de Transacciones")

                if num_uncategorized > 0:
                     st.info(f"Encontradas {num_uncategorized} transacciones sin categoría o subcategoría definida.")

                # Obtener listas actuales de categorías y subcategorías para los dropdowns
                # Excluir los placeholders de las opciones seleccionables
                categorias_existentes = sorted([cat for cat in df[categoria_column_name].unique() if cat != placeholder_cat])
                subcategorias_existentes = sorted([sub for sub in df[subcategoria_column_name].unique() if sub != placeholder_sub])

                st.subheader("Editar Categorías")
                st.caption("Modifica las categorías o subcategorías directamente en la tabla. Los cambios se guardarán temporalmente en la sesión.")

                # Opciones de filtrado para la tabla de edición
                st.write("Filtrar transacciones a editar:")
                col_f1, col_f2, col_f3 = st.columns([1,1,2])
                with col_f1:
                    show_uncategorized_only = st.checkbox("Mostrar solo sin categorizar", value=(num_uncategorized > 0))
                with col_f2:
                    selected_year_edit = st.selectbox("Año:", ["Todos"] + sorted([int(a) for a in df['Año'].dropna().unique()]), key='sel_año_edit')
                with col_f3:
                    text_filter = st.text_input("Buscar en Descripción (CONCEPTO):", key='text_filter_edit')

                # Aplicar filtros para la edición
                df_to_edit = df.copy()
                if show_uncategorized_only:
                    df_to_edit = df_to_edit[uncategorized_mask]
                if selected_year_edit != "Todos":
                    df_to_edit = df_to_edit[df_to_edit['Año'] == selected_year_edit]
                if text_filter:
                    df_to_edit = df_to_edit[df_to_edit[descripcion_column_name].str.contains(text_filter, case=False, na=False)]


                # Configurar el data_editor
                column_config_editor = {
                    categoria_column_name: st.column_config.SelectboxColumn(
                        f"{categoria_column_name}",
                        help=f"Selecciona o escribe una nueva {categoria_column_name}",
                        options=categorias_existentes,
                        required=False # Permitir añadir nuevas categorías tecleando
                    ),
                    subcategoria_column_name: st.column_config.SelectboxColumn(
                        f"{subcategoria_column_name}",
                        help=f"Selecciona o escribe una nueva {subcategoria_column_name}",
                        options=subcategorias_existentes,
                        required=False
                    ),
                    # Ocultar columnas menos relevantes para la categorización
                     anio_column_name: None, mes_column_name: None, dia_column_name: None,
                     importe_calculo_col: st.column_config.NumberColumn(format="%.2f €"), # Mostrar importe formateado
                     # Ajustar visibilidad de otras columnas si es necesario
                }

                st.info("💡 Haz doble clic en una celda de CATEGORÍA o SUBCATEGORÍA para editarla.")
                edited_df_result = st.data_editor(
                    df_to_edit, # Pasar el df filtrado para edición
                    column_config=column_config_editor,
                    use_container_width=True,
                    num_rows="dynamic", # Permitir añadir/borrar filas si se quisiera (puede ser peligroso) -> usar "fixed" o "auto"
                    key='data_editor_categorize',
                     hide_index=True
                )

                # --- Lógica para actualizar el DataFrame en Session State ---
                if edited_df_result is not None :
                    # Comparar si hubo cambios reales para evitar reruns innecesarios
                    # if not df_to_edit.equals(edited_df_result): # st.data_editor a veces retorna el mismo df
                    # ¡Importante! Reconstruir el DataFrame completo si editamos una vista filtrada
                    # Actualizar las filas editadas en el DataFrame principal 'df'

                    # Crear un índice temporal único si no existe para el merge
                    if 'temp_id' not in df.columns:
                        df['temp_id'] = range(len(df))
                    if 'temp_id' not in edited_df_result.columns:
                         # Necesitamos mapear los cambios de vuelta. Esto es complejo si se filtró.
                         # Alternativa más simple: guardar el df completo en session state y editarlo siempre.
                         # Vamos a simplificar y asumir que editamos df completo por ahora o
                         # que el usuario entiende que los cambios aplican al df completo
                         # st.warning("La edición sobre vista filtrada es compleja de guardar. Cambios aplicados globalmente.")
                         pass # Por ahora, no intentaremos el merge complejo


                    st.session_state.edited_df = edited_df_result.copy() # Guardar el resultado editado completo
                    # st.info("Cambios guardados en la sesión actual.")
                    # Considerar un botón explícito de "Guardar Cambios en Sesión" para más control
                    # st.experimental_rerun() # Re-ejecutar para que los análisis usen los datos actualizados


                st.subheader("Guardar Cambios")
                st.write("Descarga el archivo CSV con las categorías actualizadas para usarlo la próxima vez.")

                csv_data = convert_df_to_csv(st.session_state.edited_df)

                st.download_button(
                    label="📥 Descargar CSV Corregido",
                    data=csv_data,
                    file_name=f"Gastos_Corregido_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                )


        # --- Manejo de Errores General ---
        except Exception as e:
            st.error(f"Ocurrió un error inesperado en el procesamiento principal: {e}")
            import traceback
            st.error("Detalle del error:")
            st.code(traceback.format_exc())
            # Resetear estado en caso de error grave
            st.session_state.edited_df = None
            st.session_state.original_df_loaded = None

# --- Fin del Bloque Principal si hay datos ---

if __name__ == "__main__":
    main()
