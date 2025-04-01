import streamlit as st
import pandas as pd

def main():
    st.title('Análisis de Gastos por Año y Mes')

    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            # 1. Leer el CSV
            df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')

            # 2. Limpiar nombres de columnas (eliminar espacios)
            df.columns = df.columns.str.strip()

            # (Opcional para depuración) Imprimir columnas para confirmar
            # st.write("Columnas detectadas:", df.columns.tolist())

            # 3. Definir los nombres exactos de las columnas según tu CSV
            importe_column_name = 'IMPORTE'
            tipo_column_name = 'TIPO'
            categoria_column_name = 'CATEGORÍA'
            subcategoria_column_name = 'SUBCATEGORIA'
            anio_column_name = 'AÑO'
            mes_column_name = 'MES'
            dia_column_name = 'DIA'
            descripcion_column_name = 'CONCEPTO' # Columna que contiene la descripción larga
            comercio_column_name = 'COMERCIO'   # Columna adicional para el nombre del comercio

            # 4. Validar que las columnas necesarias existen
            required_columns = [
                importe_column_name, tipo_column_name, categoria_column_name,
                subcategoria_column_name, anio_column_name, mes_column_name,
                dia_column_name, descripcion_column_name, comercio_column_name
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                st.error(f"Error: Faltan las siguientes columnas esenciales en el archivo CSV: {', '.join(missing_columns)}")
                st.info(f"Las columnas detectadas son: {df.columns.tolist()}")
                return # Detener ejecución si faltan columnas

            # 5. Convertir la columna 'IMPORTE' a numérico
            # Asegurarse de que es string antes de reemplazar (maneja posibles errores)
            df[importe_column_name] = df[importe_column_name].astype(str).str.replace(',', '.').astype(float)

            # 6. Crear columna 'Fecha' combinando AÑO, MES, DIA
            try:
                # Convertir AÑO, MES, DIA a string para concatenación segura
                df['Fecha'] = pd.to_datetime(
                    df[anio_column_name].astype(str) + '-' +
                    df[mes_column_name].astype(str) + '-' +
                    df[dia_column_name].astype(str),
                    format='%Y-%m-%d',
                    errors='coerce' # Si alguna fecha es inválida, la pone como NaT (Not a Time)
                )
                # Verificar si hubo errores en la conversión de fechas
                if df['Fecha'].isnull().any():
                    st.warning("Advertencia: Algunas fechas no pudieron ser convertidas correctamente. Se ignorarán esas filas en los análisis basados en fecha.")
                    # Opcional: eliminar filas con fechas inválidas
                    # df.dropna(subset=['Fecha'], inplace=True)

            except ValueError as e:
                st.error(f"Error crítico al convertir las columnas de fecha: {e}. Asegúrate de que AÑO, MES y DIA sean correctos.")
                return
            except KeyError as e:
                 st.error(f"Error: Falta una de las columnas de fecha ({e}) requeridas ('AÑO', 'MES', 'DIA').")
                 return

            # 7. Mostrar información básica de los datos cargados
            st.subheader("Información General del Archivo")
            st.write(f"Valores únicos en la columna '{tipo_column_name}':", df[tipo_column_name].unique())
            st.write(f"Valores únicos en la columna '{categoria_column_name}':", df[categoria_column_name].astype(str).unique()) # Convertir a str por si hay NaN

            # 8. Filtrar solo los gastos (Excluir INGRESOS, TRASPASOS, RECIBOS, etc.)
            # Ser más específico si es necesario, basado en los valores únicos vistos
            valores_gasto = ["GASTO"] # Puedes añadir más si aplican como gasto
            df_gastos = df[df[tipo_column_name].isin(valores_gasto)].copy() # Usar .copy() para evitar SettingWithCopyWarning

            if df_gastos.empty:
                st.warning("No se encontraron registros de tipo 'GASTO' en el archivo.")
                return

            # 9. Extraer año y mes de la columna 'Fecha' para los gastos
            df_gastos['Año'] = df_gastos['Fecha'].dt.year
            df_gastos['Mes'] = df_gastos['Fecha'].dt.month

             # Rellenar valores NaN en columnas categóricas antes de usarlas en selectbox o groupby
            df_gastos[categoria_column_name].fillna('SIN CATEGORÍA', inplace=True)
            df_gastos[subcategoria_column_name].fillna('SIN SUBCATEGORÍA', inplace=True)
            df_gastos[comercio_column_name].fillna('SIN COMERCIO', inplace=True)
            df_gastos[descripcion_column_name].fillna('SIN DESCRIPCIÓN', inplace=True)


            # 10. Selección de Año por el Usuario
            # Obtener años únicos DESPUÉS de filtrar gastos y ANTES de filtrar por año seleccionado
            años_disponibles = sorted(df_gastos['Año'].unique())
            if not años_disponibles:
                 st.warning("No hay años con gastos para analizar.")
                 return
            año_seleccionado = st.selectbox("Selecciona un año para analizar:", años_disponibles)

            # 11. Filtrar DataFrame por el año seleccionado
            df_año = df_gastos[df_gastos['Año'] == año_seleccionado]

            if df_año.empty:
                st.warning(f"No hay gastos registrados para el año {año_seleccionado}.")
                return

            # 12. Crear y mostrar la tabla pivote de gastos
            st.subheader(f"Resumen de Gastos por Categoría y Mes ({año_seleccionado})")
            try:
                tabla_gastos = df_año.pivot_table(
                    values='Importe',
                    index=categoria_column_name,
                    columns='Mes',
                    aggfunc='sum',
                    fill_value=0,
                    margins=True,          # Añadir totales
                    margins_name='Total'   # Nombre para la fila/columna de totales
                )

                # Formatear la tabla pivote
                formato_euro = '{:,.0f} €'.format # Separador de miles, 0 decimales, símbolo €
                estilo = [
                    {'selector': 'th.col_heading, th.row_heading', 'props': [('background-color', '#6c757d'), ('color', 'white'), ('font-weight', 'bold')]},
                    {'selector': 'th.col_heading', 'props': [('text-align', 'center')]},
                    {'selector': 'th.row_heading', 'props': [('text-align', 'left')]},
                    {'selector': 'tr:last-child td, td:last-child', 'props': [('font-weight', 'bold'), ('background-color', '#f8f9fa')]} # Resaltar totales
                ]
                # Aplicar formato y estilo, ocultando índice si es redundante
                tabla_formateada = tabla_gastos.style.format(formato_euro).set_table_styles(estilo) # .hide(axis="index") si el índice es la categoría

                st.dataframe(tabla_formateada, use_container_width=True) # Usar todo el ancho disponible

            except Exception as e_pivot:
                st.error(f"Error al crear la tabla pivote: {e_pivot}")

            # 13. Sección Interactiva para Detalle de Gastos
            st.subheader("Detalle de Gastos por Categoría y Mes")

            # Obtener listas únicas DESPUÉS de filtrar por año
            categorias_año = sorted(df_año[categoria_column_name].unique())
            meses_año = sorted(df_año['Mes'].unique())

            if not categorias_año or not meses_año:
                st.info("No hay suficientes datos para mostrar el detalle interactivo.")
                return

            col1, col2 = st.columns(2) # Crear dos columnas para los selectores
            with col1:
                categoria_seleccionada = st.selectbox(f"Selecciona una Categoría ({categoria_column_name})", categorias_año)
            with col2:
                mes_seleccionado = st.selectbox("Selecciona un Mes", meses_año)

            # Filtrar para el detalle
            filtro_detalle = (df_año[categoria_column_name] == categoria_seleccionada) & (df_año['Mes'] == mes_seleccionado)
            df_detalle = df_año[filtro_detalle]

            if not df_detalle.empty:
                st.write(f"**Detalle para {categoria_seleccionada} en el mes {mes_seleccionado} del año {año_seleccionado}:**")

                # Agrupar y sumar para la tabla de desglose
                tabla_desglose = df_detalle.groupby([
                    subcategoria_column_name,
                    descripcion_column_name,
                    comercio_column_name,
                    'Fecha' # Mantener fecha para detalle completo
                ])['Importe'].sum().reset_index() # Usar la variable de importe original aquí

                # Ordenar por Importe descendente
                tabla_desglose = tabla_desglose.sort_values(by='Importe', ascending=True) # True para ver gastos más pequeños primero, False para los más grandes

                # Formatear columna de Importe en la tabla de desglose
                tabla_desglose['Importe'] = tabla_desglose['Importe'].map('{:,.2f} €'.format) # 2 decimales para detalle
                tabla_desglose['Fecha'] = tabla_desglose['Fecha'].dt.strftime('%Y-%m-%d') # Formatear fecha a string

                # Mostrar tabla de desglose
                st.dataframe(tabla_desglose, use_container_width=True)
            else:
                st.info(f"No se encontraron gastos detallados para {categoria_seleccionada} en el mes {mes_seleccionado} del año {año_seleccionado}.")

        except FileNotFoundError:
             st.error("Error: No se pudo encontrar el archivo subido.")
        except pd.errors.EmptyDataError:
             st.error("Error: El archivo CSV está vacío.")
        except pd.errors.ParserError:
             st.error("Error: No se pudo parsear el archivo CSV. Verifica el formato y el separador (';').")
        except KeyError as e:
             st.error(f"Error de columna: No se encontró la columna '{e}'. Verifica los nombres en tu archivo CSV.")
        except Exception as e:
            # Captura cualquier otro error inesperado
            st.error(f"Ocurrió un error inesperado al procesar el archivo: {e}")
            import traceback
            st.error("Detalle del error:")
            st.code(traceback.format_exc()) # Muestra el stack trace para depuración

    else:
        st.info("Por favor, sube tu archivo CSV de gastos para comenzar el análisis.")

if __name__ == "__main__":
    main()
