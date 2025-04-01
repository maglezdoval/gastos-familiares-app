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
            importe_original_col = 'IMPORTE' # Nombre en el CSV
            # ... (otras definiciones de columnas originales) ...
            tipo_column_name = 'TIPO'
            categoria_column_name = 'CATEGORÍA'
            subcategoria_column_name = 'SUBCATEGORIA'
            anio_column_name = 'AÑO'
            mes_column_name = 'MES'
            dia_column_name = 'DIA'
            descripcion_column_name = 'CONCEPTO'
            comercio_column_name = 'COMERCIO'
            cuenta_column_name = 'CUENTA' # Añadir columna Cuenta si la necesitas más adelante

            # ---- Nombre estandarizado que usaremos internamente ----
            importe_calculo_col = 'Importe' # Usaremos 'Importe' (minúscula) para los cálculos

            # 4. Validar columnas originales
            required_columns_original = [
                importe_original_col, tipo_column_name, categoria_column_name,
                subcategoria_column_name, anio_column_name, mes_column_name,
                dia_column_name, descripcion_column_name, comercio_column_name,
                cuenta_column_name # Validar también Cuenta
            ]
            missing_columns = [col for col in required_columns_original if col not in df.columns]

            if missing_columns:
                st.error(f"Error: Faltan las siguientes columnas esenciales en el archivo CSV: {', '.join(missing_columns)}")
                st.info(f"Las columnas detectadas son: {df.columns.tolist()}")
                return

            # ---- PASO CLAVE: Renombrar la columna de importe original ----
            df.rename(columns={importe_original_col: importe_calculo_col}, inplace=True)
            # Ahora la columna se llama 'Importe' (minúscula) en el DataFrame

            # 5. Convertir la columna renombrada 'Importe' a numérico
            df[importe_calculo_col] = df[importe_calculo_col].astype(str).str.replace(',', '.').astype(float)
            # A partir de aquí, SIEMPRE usaremos importe_calculo_col ('Importe')

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

            # 7. Info general
            st.subheader("Información General del Archivo")
            st.write(f"Valores únicos en '{tipo_column_name}':", df[tipo_column_name].unique())
            st.write(f"Valores únicos en '{categoria_column_name}':", df[categoria_column_name].astype(str).unique())

            # 8. Filtrar gastos
            valores_gasto = ["GASTO"]
            df_gastos = df[df[tipo_column_name].isin(valores_gasto)].copy()

            if df_gastos.empty:
                st.warning("No se encontraron registros de tipo 'GASTO'.")
                return

            # 9. Extraer año y mes
            df_gastos['Año'] = df_gastos['Fecha'].dt.year
            df_gastos['Mes'] = df_gastos['Fecha'].dt.month

            # Rellenar NaNs en columnas categóricas
            for col in [categoria_column_name, subcategoria_column_name, comercio_column_name, descripcion_column_name]:
                 if col in df_gastos.columns:
                       df_gastos[col].fillna(f'SIN {col.upper()}', inplace=True)

            # 10. Selección de Año
            años_disponibles = sorted([int(a) for a in df_gastos['Año'].dropna().unique()]) # Asegurar que son ints y quitar NaNs si los hubiera
            if not años_disponibles:
                 st.warning("No hay años con gastos para analizar.")
                 return
            año_seleccionado = st.selectbox("Selecciona un año para analizar:", años_disponibles)

            # 11. Filtrar por año
            df_año = df_gastos[df_gastos['Año'] == año_seleccionado]

            if df_año.empty:
                st.warning(f"No hay gastos registrados para el año {año_seleccionado}.")
                return

            # 12. Tabla pivote
            st.subheader(f"Resumen de Gastos por Categoría y Mes ({año_seleccionado})")
            try:
                tabla_gastos = df_año.pivot_table(
                    values=importe_calculo_col,  # <-- USAR LA VARIABLE CORRECTA
                    index=categoria_column_name,
                    columns='Mes',
                    aggfunc='sum',
                    fill_value=0,
                    margins=True,
                    margins_name='Total'
                )

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
                # Ser más específico en el error
                st.error(f"Error al crear la tabla pivote: {e_pivot}")
                st.write("Columnas disponibles en df_año:", df_año.columns.tolist()) # Ayuda a depurar


            # 13. Detalle Interactivo
            st.subheader("Detalle de Gastos por Categoría y Mes")
            categorias_año = sorted(df_año[categoria_column_name].unique())
            meses_año = sorted(df_año['Mes'].unique())

            if not categorias_año or not meses_año:
                st.info("No hay suficientes datos para el detalle interactivo.")
                return

            col1, col2 = st.columns(2)
            with col1:
                categoria_seleccionada = st.selectbox(f"Categoría ({categoria_column_name})", categorias_año)
            with col2:
                mes_seleccionado = st.selectbox("Mes", meses_año)

            filtro_detalle = (df_año[categoria_column_name] == categoria_seleccionada) & (df_año['Mes'] == mes_seleccionado)
            df_detalle = df_año[filtro_detalle]

            if not df_detalle.empty:
                st.write(f"**Detalle para {categoria_seleccionada} en el mes {mes_seleccionado} del año {año_seleccionado}:**")
                tabla_desglose = df_detalle.groupby([
                    subcategoria_column_name,
                    descripcion_column_name,
                    comercio_column_name,
                    cuenta_column_name, # Incluir cuenta en el detalle
                    'Fecha'
                ])[importe_calculo_col].sum().reset_index() # <-- USAR LA VARIABLE CORRECTA

                tabla_desglose = tabla_desglose.sort_values(by=importe_calculo_col, ascending=True)

                # Asegurarse de que Fecha sea datetime antes de formatear
                tabla_desglose['Fecha'] = pd.to_datetime(tabla_desglose['Fecha']).dt.strftime('%Y-%m-%d')
                 # Formatear el importe después de ordenar
                tabla_desglose[importe_calculo_col] = tabla_desglose[importe_calculo_col].map('{:,.2f} €'.format)


                st.dataframe(tabla_desglose, use_container_width=True)
            else:
                st.info(f"No se encontraron gastos detallados para '{categoria_seleccionada}' en el mes {mes_seleccionado} del año {año_seleccionado}.")

        # (Manejo de errores más específicos como antes)
        except FileNotFoundError:
             st.error("Error: No se pudo encontrar el archivo subido.")
        except pd.errors.EmptyDataError:
             st.error("Error: El archivo CSV está vacío.")
        except pd.errors.ParserError:
             st.error("Error: No se pudo parsear el archivo CSV. Verifica el formato y el separador (';').")
        except KeyError as e:
             st.error(f"Error de columna: No se encontró la columna '{e}'. Verifica los nombres en tu archivo CSV.")
             st.info(f"Columnas detectadas al inicio: {df.columns.tolist()}") # Muestra columnas iniciales si falla aquí
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            import traceback
            st.error("Detalle del error:")
            st.code(traceback.format_exc())

    else:
        st.info("Por favor, sube tu archivo CSV de gastos para comenzar el análisis.")

if __name__ == "__main__":
    main()
