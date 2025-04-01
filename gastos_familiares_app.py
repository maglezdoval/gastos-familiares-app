import streamlit as st
import pandas as pd
import calendar # Para obtener nombres de meses

# Función auxiliar para mapear número de mes a nombre
def obtener_nombre_mes(numero_mes):
    try:
        # Asegurarse de que es un entero
        numero_mes_int = int(numero_mes)
        # Usar calendar para obtener el nombre abreviado en español
        # Nota: Esto depende de la configuración regional (locale) del sistema donde corre Streamlit.
        # Si no funciona, podríamos necesitar instalar y configurar el locale explícitamente
        # o usar un diccionario de mapeo manual.
        # Intentaremos con calendar primero. Asegúrate de que tu sistema tenga locale español.
        # import locale
        # try:
        #     locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8') # o 'Spanish_Spain.1252' en Windows
        # except locale.Error:
        #     st.warning("Locale español no encontrado, usando nombres de mes en inglés.")
        #     locale.setlocale(locale.LC_TIME, '') # Volver al default si falla

        # return calendar.month_abbr[numero_mes_int]

        # --- Alternativa Manual (más segura si locale falla) ---
        meses_es = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }
        return meses_es.get(numero_mes_int, str(numero_mes_int)) # Devuelve número si no está en el dict
    except (ValueError, TypeError):
        return str(numero_mes) # Devolver como string si no es un número válido

def main():
    st.set_page_config(layout="wide") # Usar layout ancho para más espacio
    st.title('Análisis Financiero Personal')

    uploaded_file = st.file_uploader("Sube tu archivo CSV de movimientos", type=["csv"])

    if uploaded_file is not None:
        try:
            # 1. Leer el CSV completo
            df_original = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')

            # --- Limpieza y Preparación Inicial (Común a todos los análisis) ---
            df = df_original.copy() # Trabajar con una copia
            df.columns = df.columns.str.strip()

            # Definir nombres originales
            importe_original_col = 'IMPORTE'
            tipo_column_name = 'TIPO'
            categoria_column_name = 'CATEGORÍA'
            subcategoria_column_name = 'SUBCATEGORIA'
            anio_column_name = 'AÑO'
            mes_column_name = 'MES'
            dia_column_name = 'DIA'
            descripcion_column_name = 'CONCEPTO'
            comercio_column_name = 'COMERCIO'
            cuenta_column_name = 'CUENTA'

            # Nombre estandarizado para cálculos
            importe_calculo_col = 'Importe'

            # Validar columnas originales
            required_columns_original = [
                importe_original_col, tipo_column_name, categoria_column_name,
                subcategoria_column_name, anio_column_name, mes_column_name,
                dia_column_name, descripcion_column_name, comercio_column_name,
                cuenta_column_name
            ]
            missing_columns = [col for col in required_columns_original if col not in df.columns]
            if missing_columns:
                st.error(f"Error: Faltan columnas esenciales: {', '.join(missing_columns)}")
                return

            # Renombrar y convertir 'IMPORTE'
            df.rename(columns={importe_original_col: importe_calculo_col}, inplace=True)
            df[importe_calculo_col] = df[importe_calculo_col].astype(str).str.replace(',', '.').astype(float)

            # Crear columna 'Fecha'
            try:
                df['Fecha'] = pd.to_datetime(
                    df[anio_column_name].astype(str) + '-' +
                    df[mes_column_name].astype(str) + '-' +
                    df[dia_column_name].astype(str),
                    format='%Y-%m-%d', errors='coerce'
                )
                if df['Fecha'].isnull().any():
                    st.warning("Advertencia: Algunas fechas no pudieron ser convertidas.")
                    df.dropna(subset=['Fecha'], inplace=True) # Eliminar filas sin fecha válida
            except (ValueError, KeyError) as e:
                st.error(f"Error crítico al procesar fechas: {e}.")
                return

            # Extraer año y mes (para todo el dataframe ahora)
            df['Año'] = df['Fecha'].dt.year
            df['Mes'] = df['Fecha'].dt.month

            # Rellenar NaNs en columnas clave (después de extraer año/mes)
            fill_na_cols = [tipo_column_name, categoria_column_name, subcategoria_column_name, comercio_column_name, descripcion_column_name, cuenta_column_name]
            for col in fill_na_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).fillna(f'SIN {col.upper()}')

            # --- SECCIÓN 1: Análisis de Gastos (como antes) ---
            st.header("Análisis Detallado de Gastos")

            # Filtrar solo gastos para esta sección
            valores_gasto = ["GASTO"]
            df_gastos = df[df[tipo_column_name].isin(valores_gasto)].copy()

            if not df_gastos.empty:

                st.sidebar.header("Filtros de Gastos")
                # Selección de Año para Gastos
                años_gastos_disponibles = sorted([int(a) for a in df_gastos['Año'].dropna().unique()])
                año_gastos_seleccionado = st.sidebar.selectbox("Año (Gastos):", años_gastos_disponibles, key='sel_año_gastos')

                df_gastos_año = df_gastos[df_gastos['Año'] == año_gastos_seleccionado]

                if not df_gastos_año.empty:
                    # Filtro Multiselección por CUENTA para Gastos
                    cuentas_gastos_disponibles = sorted(df_gastos_año[cuenta_column_name].unique())
                    cuentas_gastos_seleccionadas = st.sidebar.multiselect(
                        "Cuentas (Gastos):",
                        options=cuentas_gastos_disponibles,
                        default=cuentas_gastos_disponibles,
                        key='sel_cuenta_gastos'
                    )

                    if cuentas_gastos_seleccionadas:
                        df_gastos_año_filtrado = df_gastos_año[df_gastos_año[cuenta_column_name].isin(cuentas_gastos_seleccionadas)].copy()

                        if not df_gastos_año_filtrado.empty:
                            # Mostrar Resumen y Detalle de Gastos (usando df_gastos_año_filtrado)
                            st.subheader(f"Resumen ({año_gastos_seleccionado} - Cuentas: {', '.join(cuentas_gastos_seleccionadas)})")
                            # (Código de tabla pivote y detalle de gastos aquí, usando df_gastos_año_filtrado)
                            # ... (tabla pivote formateada) ...
                            try:
                                tabla_gastos_pivot = df_gastos_año_filtrado.pivot_table(
                                    values=importe_calculo_col, index=categoria_column_name, columns='Mes',
                                    aggfunc='sum', fill_value=0, margins=True, margins_name='Total' )

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

                            # Detalle interactivo de gastos
                            st.subheader("Detalle Interactivo de Gastos")
                            categorias_gastos_filtradas = sorted(df_gastos_año_filtrado[categoria_column_name].unique())
                            meses_gastos_filtrados = sorted(df_gastos_año_filtrado['Mes'].unique())

                            if categorias_gastos_filtradas and meses_gastos_filtrados:
                                col1_gasto_det, col2_gasto_det = st.columns(2)
                                with col1_gasto_det:
                                     categoria_gasto_sel = st.selectbox("Categoría Gasto:", categorias_gastos_filtradas, key='cat_gasto_det_sel')
                                with col2_gasto_det:
                                     mes_gasto_sel = st.selectbox("Mes Gasto:", meses_gastos_filtrados, key='mes_gasto_det_sel')

                                filtro_gasto_detalle = (df_gastos_año_filtrado[categoria_column_name] == categoria_gasto_sel) & (df_gastos_año_filtrado['Mes'] == mes_gasto_sel)
                                df_gasto_detalle = df_gastos_año_filtrado[filtro_gasto_detalle]

                                if not df_gasto_detalle.empty:
                                     st.write(f"**Detalle Gasto para {categoria_gasto_sel}, Mes {mes_gasto_sel}, Año {año_gastos_seleccionado}**")
                                     tabla_gasto_desglose = df_gasto_detalle.groupby([
                                         subcategoria_column_name, descripcion_column_name, comercio_column_name, cuenta_column_name, 'Fecha'
                                     ])[importe_calculo_col].sum().reset_index()
                                     tabla_gasto_desglose = tabla_gasto_desglose.sort_values(by=importe_calculo_col, ascending=True) # Gastos son negativos, ascendente = más negativo primero
                                     tabla_gasto_desglose['Fecha'] = pd.to_datetime(tabla_gasto_desglose['Fecha']).dt.strftime('%Y-%m-%d')
                                     tabla_gasto_desglose[importe_calculo_col] = tabla_gasto_desglose[importe_calculo_col].map('{:,.2f} €'.format)
                                     st.dataframe(tabla_gasto_desglose, use_container_width=True)
                                else:
                                     st.info("No hay detalles para la selección de gasto actual.")
                            else:
                                st.info("No hay categorías o meses suficientes para el detalle de gastos con los filtros aplicados.")
                        else:
                            st.info("No hay gastos para las cuentas seleccionadas en este año.")
                    else:
                        st.warning("Selecciona al menos una cuenta en el filtro de gastos.")
                else:
                    st.info(f"No hay gastos registrados para el año {año_gastos_seleccionado}.")
            else:
                st.info("No se encontraron registros de tipo 'GASTO' en el archivo.")


            # --- SECCIÓN 2: Análisis P&L Cuenta Familiar (EVO) ---
            st.header("Análisis P&L - Cuenta Familiar (EVO)")

            # Filtrar solo transacciones de la cuenta EVO
            df_evo = df[df[cuenta_column_name] == 'EVO'].copy()

            if df_evo.empty:
                st.warning("No se encontraron transacciones para la cuenta 'EVO'.")
            else:
                st.sidebar.header("Filtro P&L (EVO)")
                # Selección de Año para P&L (independiente del de gastos)
                años_evo_disponibles = sorted([int(a) for a in df_evo['Año'].dropna().unique()])
                if not años_evo_disponibles:
                    st.warning("No hay años con transacciones para la cuenta 'EVO'.")
                else:
                    año_pl_seleccionado = st.sidebar.selectbox("Año (P&L):", años_evo_disponibles, key='sel_año_pl')

                    # Filtrar df_evo por el año seleccionado para P&L
                    df_evo_año = df_evo[df_evo['Año'] == año_pl_seleccionado]

                    if df_evo_año.empty:
                         st.info(f"No hay transacciones en la cuenta 'EVO' para el año {año_pl_seleccionado}.")
                    else:
                         # Calcular Ingresos Mensuales
                         tipos_ingreso = ['TRASPASO', 'INGRESO', 'REEMBOLSO', 'INGRESO'] # Añadir otros tipos si aplican como ingreso
                         df_ingresos = df_evo_año[df_evo_año[tipo_column_name].isin(tipos_ingreso)]
                         ingresos_mensuales = df_ingresos.groupby('Mes')[importe_calculo_col].sum()

                         # Calcular Egresos Mensuales (Gastos)
                         tipos_egreso = ['GASTO']
                         df_egresos = df_evo_año[df_evo_año[tipo_column_name].isin(tipos_egreso)]
                         # Sumar los importes (que son negativos) y luego tomar el valor absoluto o multiplicar por -1 para P&L
                         egresos_mensuales_sum = df_egresos.groupby('Mes')[importe_calculo_col].sum()
                         egresos_mensuales_abs = egresos_mensuales_sum.abs() # Usar valor absoluto para mostrar/graficar egresos como positivos
                         # O egresos_mensuales_abs = egresos_mensuales_sum * -1

                         # Crear DataFrame de P&L
                         df_pl = pd.DataFrame({
                             'Ingresos': ingresos_mensuales,
                             'Egresos': egresos_mensuales_abs # Usar el valor absoluto aquí
                         })
                         df_pl = df_pl.fillna(0) # Rellenar meses sin ingresos o egresos con 0

                         # Calcular Resultado (Ingresos - Egresos)
                         df_pl['Resultado'] = df_pl['Ingresos'] - df_pl['Egresos']

                         # Añadir fila de Totales
                         total_pl = df_pl.sum()
                         total_pl.name = 'Total'
                         df_pl = pd.concat([df_pl, total_pl.to_frame().T])

                         # Formatear para la tabla
                         # Renombrar índice (número de mes) a nombre de mes
                         df_pl.index = df_pl.index.map(obtener_nombre_mes)
                         # Formato Euros
                         formato_euro_pl = '{:,.2f} €'.format # 2 decimales para P&L
                         df_pl_formateado = df_pl.style.format(formato_euro_pl) \
                                               .applymap(lambda x: 'color: green' if x > 0 else ('color: red' if x < 0 else 'color: black'), subset=['Resultado']) \
                                               .set_properties(**{'text-align': 'right'})

                         st.subheader(f"Tabla P&L Mensual ({año_pl_seleccionado}) - Cuenta EVO")
                         st.dataframe(df_pl_formateado, use_container_width=True)

                         # Preparar datos para el gráfico (sin la fila Total y con índice numérico para ordenar)
                         df_pl_chart = df_pl.drop('Total')
                         try:
                              # Intentar convertir índice (nombres de mes) de nuevo a número para ordenar el gráfico
                              mes_num_map = {v: k for k, v in meses_es.items()} # Invertir el mapeo manual
                              df_pl_chart.index = df_pl_chart.index.map(mes_num_map.get)
                              df_pl_chart = df_pl_chart.sort_index()
                         except:
                              # Si falla la conversión o el sort, al menos mostrar el gráfico
                              st.warning("No se pudo ordenar el gráfico por mes.")
                              pass # Continuar sin ordenar

                         st.subheader(f"Gráfico P&L Mensual ({año_pl_seleccionado}) - Cuenta EVO")
                         # Usar solo Ingresos y Egresos para el gráfico
                         st.line_chart(df_pl_chart[['Ingresos', 'Egresos']])


        # (Manejo de errores como antes)
        except FileNotFoundError:
             st.error("Error: No se pudo encontrar el archivo subido.")
        except pd.errors.EmptyDataError:
             st.error("Error: El archivo CSV está vacío.")
        except pd.errors.ParserError:
             st.error("Error: No se pudo parsear el archivo CSV. Verifica el formato y el separador (';').")
        except KeyError as e:
             st.error(f"Error de columna: No se encontró la columna '{e}'. Verifica los nombres en tu archivo CSV.")
             try: st.info(f"Columnas detectadas: {df.columns.tolist()}")
             except NameError: pass
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            import traceback
            st.error("Detalle del error:")
            st.code(traceback.format_exc())

    else:
        st.info("Por favor, sube tu archivo CSV para comenzar el análisis.")

if __name__ == "__main__":
    main()
