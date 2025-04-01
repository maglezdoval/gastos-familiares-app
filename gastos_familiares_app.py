import streamlit as st
import pandas as pd

def main():
    st.title('Análisis de Gastos por Año y Mes')

    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            # 1. Leer el CSV
            df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')

            # 2. Limpiar nombres de columnas
            df.columns = df.columns.str.strip()

            # 3. Definir los nombres originales
            importe_original_col = 'IMPORTE'
            tipo_column_name = 'TIPO'
            categoria_column_name = 'CATEGORÍA'
            subcategoria_column_name = 'SUBCATEGORIA'
            anio_column_name = 'AÑO'
            mes_column_name = 'MES'
            dia_column_name = 'DIA'
            descripcion_column_name = 'CONCEPTO'
            comercio_column_name = 'COMERCIO'
            cuenta_column_name = 'CUENTA' # Columna clave para el nuevo filtro

            # Nombre estandarizado para cálculos
            importe_calculo_col = 'Importe'

            # 4. Validar columnas originales
            required_columns_original = [
                importe_original_col, tipo_column_name, categoria_column_name,
                subcategoria_column_name, anio_column_name, mes_column_name,
                dia_column_name, descripcion_column_name, comercio_column_name,
                cuenta_column_name
            ]
            missing_columns = [col for col in required_columns_original if col not in df.columns]

            if missing_columns:
                st.error(f"Error: Faltan las siguientes columnas esenciales: {', '.join(missing_columns)}")
                st.info(f"Columnas detectadas: {df.columns.tolist()}")
                return

            # 5. Renombrar y convertir 'IMPORTE'
            df.rename(columns={importe_original_col: importe_calculo_col}, inplace=True)
            df[importe_calculo_col] = df[importe_calculo_col].astype(str).str.replace(',', '.').astype(float)

            # 6. Crear columna 'Fecha'
            try:
                df['Fecha'] = pd.to_datetime(
                    df[anio_column_name].astype(str) + '-' +
                    df[mes_column_name].astype(str) + '-' +
                    df[dia_column_name].astype(str),
                    format='%Y-%m-%d', errors='coerce'
                )
                if df['Fecha'].isnull().any():
                    st.warning("Advertencia: Algunas fechas no pudieron ser convertidas.")
            except ValueError as e:
                st.error(f"Error crítico al convertir las columnas de fecha: {e}.")
                return
            except KeyError as e:
                 st.error(f"Error: Falta una de las columnas de fecha ({e}).")
                 return

            # 7. Info general (opcional mostrar aquí)
            # st.subheader("Información General del Archivo")
            # st.write(f"Valores únicos en '{tipo_column_name}':", df[tipo_column_name].unique())
            # st.write(f"Valores únicos en '{categoria_column_name}':", df[categoria_column_name].astype(str).unique())
            # st.write(f"Valores únicos en '{cuenta_column_name}':", df[cuenta_column_name].astype(str).unique())

            # 8. Filtrar gastos
            valores_gasto = ["GASTO"]
            df_gastos = df[df[tipo_column_name].isin(valores_gasto)].copy()

            if df_gastos.empty:
                st.warning("No se encontraron registros de tipo 'GASTO'.")
                return

            # 9. Extraer año y mes
            df_gastos['Año'] = df_gastos['Fecha'].dt.year
            df_gastos['Mes'] = df_gastos['Fecha'].dt.month

            # Rellenar NaNs en columnas categóricas ANTES de usarlas en filtros/agrupaciones
            fill_na_cols = [categoria_column_name, subcategoria_column_name, comercio_column_name, descripcion_column_name, cuenta_column_name]
            for col in fill_na_cols:
                 if col in df_gastos.columns:
                       # Usar astype(str) para asegurar que no haya error con tipos mixtos antes de fillna
                       df_gastos[col] = df_gastos[col].astype(str).fillna(f'SIN {col.upper()}')


            # --- SECCIÓN DE FILTROS PRINCIPALES ---
            st.sidebar.header("Filtros Principales") # Mover filtros a la barra lateral

            # 10. Selección de Año
            años_disponibles = sorted([int(a) for a in df_gastos['Año'].dropna().unique()])
            if not años_disponibles:
                 st.warning("No hay años con gastos para analizar.")
                 return
            año_seleccionado = st.sidebar.selectbox("Año:", años_disponibles)

            # 11. Filtrar DataFrame por el año seleccionado
            df_año = df_gastos[df_gastos['Año'] == año_seleccionado]

            if df_año.empty:
                st.warning(f"No hay gastos registrados para el año {año_seleccionado}.")
                return # Salir si no hay datos para el año

            # 12. **NUEVO: Filtro Multiselección por CUENTA**
            cuentas_disponibles = sorted(df_año[cuenta_column_name].unique())
            if not cuentas_disponibles:
                 st.warning(f"No hay cuentas con gastos registrados para el año {año_seleccionado}.")
                 return # Salir si no hay cuentas para filtrar

            # st.multiselect va aquí, después de filtrar por año para que las opciones sean relevantes
            cuentas_seleccionadas = st.sidebar.multiselect(
                "Cuentas (Tags):",
                options=cuentas_disponibles,
                default=cuentas_disponibles # Todas seleccionadas por defecto
            )

            # 13. Filtrar df_año por las cuentas seleccionadas
            if not cuentas_seleccionadas: # Si el usuario deselecciona todo
                 st.warning("Selecciona al menos una cuenta para ver los datos.")
                 # Opcionalmente, mostrar un dataframe vacío o no mostrar nada más
                 return # Detener la ejecución aquí si no hay cuentas seleccionadas

            # Aplicar el filtro de cuentas al DataFrame del año
            df_año_filtrado = df_año[df_año[cuenta_column_name].isin(cuentas_seleccionadas)].copy()

            # Verificar si quedaron datos después de filtrar por cuenta
            if df_año_filtrado.empty:
                 st.info(f"No se encontraron gastos para las cuentas seleccionadas en el año {año_seleccionado}.")
                 return # Salir si el filtro de cuentas deja el dataframe vacío

            # --- FIN SECCIÓN DE FILTROS PRINCIPALES ---


            # --- MOSTRAR RESULTADOS (usar df_año_filtrado a partir de aquí) ---
            st.subheader(f"Resumen de Gastos por Categoría y Mes ({año_seleccionado})")
            st.caption(f"Mostrando datos para las cuentas: {', '.join(cuentas_seleccionadas)}")

            # 14. Tabla pivote (ahora usa df_año_filtrado)
            try:
                tabla_gastos = df_año_filtrado.pivot_table(
                    values=importe_calculo_col,
                    index=categoria_column_name,
                    columns='Mes',
                    aggfunc='sum',
                    fill_value=0,
                    margins=True,
                    margins_name='Total'
                )

                # (Formato y estilo de la tabla como antes)
                formato_euro = '{:,.0f} €'.format
                estilo = [
                     {'selector': 'th.col_heading, th.row_heading', 'props': [('background-color', '#6c757d'), ('color', 'white'), ('font-weight', 'bold')]},
                     {'selector': 'th.col_heading', 'props': [('text-align', 'center')]},
                     {'selector': 'th.row_heading', 'props': [('text-align', 'left')]},
                     {'selector': 'tr:last-child td, td:last-child', 'props': [('font-weight', 'bold'), ('background-color', '#f8f9fa')]}
                ]
                tabla_formateada = tabla_gastos.style.format(formato_euro).set_table_styles(estilo)
                st.dataframe(tabla_formateada, use_container_width=True)

            except Exception as e_pivot:
                st.error(f"Error al crear la tabla pivote: {e_pivot}")
                # st.write("Columnas disponibles en df_año_filtrado:", df_año_filtrado.columns.tolist()) # Ayuda a depurar

            # 15. Detalle Interactivo (ahora usa df_año_filtrado)
            st.subheader("Detalle de Gastos por Categoría y Mes")

            # Obtener listas únicas DESPUÉS de filtrar por año y CUENTA
            categorias_filtradas = sorted(df_año_filtrado[categoria_column_name].unique())
            meses_filtrados = sorted(df_año_filtrado['Mes'].unique())

            if not categorias_filtradas or not meses_filtrados:
                st.info("No hay suficientes datos (categorías o meses) para mostrar el detalle interactivo con los filtros actuales.")
                # return # Podrías salir aquí si prefieres no mostrar los selectores vacíos

            # Usar columnas para los selectores de detalle
            col1_det, col2_det = st.columns(2)
            with col1_det:
                 # Asegurar que hay opciones antes de crear el selectbox
                 categoria_seleccionada = st.selectbox(
                     f"Categoría ({categoria_column_name})",
                     categorias_filtradas,
                     key='cat_detalle_sel', # Añadir key por si acaso hay conflicto
                     disabled=(not categorias_filtradas) # Deshabilitar si no hay opciones
                 )
            with col2_det:
                 mes_seleccionado = st.selectbox(
                     "Mes",
                     meses_filtrados,
                     key='mes_detalle_sel',
                     disabled=(not meses_filtrados) # Deshabilitar si no hay opciones
                 )


            # Filtrar para el detalle usando df_año_filtrado
            if categorias_filtradas and meses_filtrados: # Solo proceder si hay opciones válidas
                 filtro_detalle = (df_año_filtrado[categoria_column_name] == categoria_seleccionada) & (df_año_filtrado['Mes'] == mes_seleccionado)
                 df_detalle = df_año_filtrado[filtro_detalle]

                 if not df_detalle.empty:
                     st.write(f"**Detalle para {categoria_seleccionada} en el mes {mes_seleccionado} del año {año_seleccionado} (Cuentas: {', '.join(cuentas_seleccionadas)})**")
                     tabla_desglose = df_detalle.groupby([
                         subcategoria_column_name,
                         descripcion_column_name,
                         comercio_column_name,
                         cuenta_column_name,
                         'Fecha'
                     ])[importe_calculo_col].sum().reset_index()

                     tabla_desglose = tabla_desglose.sort_values(by=importe_calculo_col, ascending=True)

                     tabla_desglose['Fecha'] = pd.to_datetime(tabla_desglose['Fecha']).dt.strftime('%Y-%m-%d')
                     tabla_desglose[importe_calculo_col] = tabla_desglose[importe_calculo_col].map('{:,.2f} €'.format)

                     st.dataframe(tabla_desglose, use_container_width=True)
                 else:
                     st.info(f"No se encontraron gastos detallados para '{categoria_seleccionada}' en el mes {mes_seleccionado} del año {año_seleccionado} con las cuentas seleccionadas.")
            elif not df_año_filtrado.empty:
                 st.info("No hay datos de categorías o meses para la selección actual de año y cuenta.")


        # (Manejo de errores como antes)
        except FileNotFoundError:
             st.error("Error: No se pudo encontrar el archivo subido.")
        except pd.errors.EmptyDataError:
             st.error("Error: El archivo CSV está vacío.")
        except pd.errors.ParserError:
             st.error("Error: No se pudo parsear el archivo CSV. Verifica el formato y el separador (';').")
        except KeyError as e:
             st.error(f"Error de columna: No se encontró la columna '{e}'. Verifica los nombres en tu archivo CSV.")
             # Intenta mostrar las columnas detectadas si es posible
             try:
                 st.info(f"Columnas detectadas al inicio: {df.columns.tolist()}")
             except NameError: # df puede no estar definido si falla la lectura inicial
                 pass
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            import traceback
            st.error("Detalle del error:")
            st.code(traceback.format_exc())

    else:
        st.info("Por favor, sube tu archivo CSV de gastos para comenzar el análisis.")

if __name__ == "__main__":
    main()
