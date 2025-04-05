        # --- PESTAÑA 3: Categorizar ---
        with tab_categorizar:
            st.header("Revisión y Categorización")

            # Asegurarse de que las variables de columna estén definidas en este scope también
            # (Aunque ya están definidas fuera, redefinirlas aquí soluciona el UnboundLocalError en los callbacks de botón)
            tipo = 'TIPO'; cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; ano = 'Año'; mes = 'Mes'; desc = 'CONCEPTO'; com = 'COMERCIO'; cta = 'CUENTA'; imp_calc = 'importe'; imp_orig = 'IMPORTE'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

            # Recalcular máscara y número basado en el df actual de sesión
            current_uncategorized_mask = (df[cat] == ph_cat)
            current_num_uncategorized = df[current_uncategorized_mask].shape[0]


            if current_num_uncategorized > 0:
                st.info(f"Hay {current_num_uncategorized} transacciones sin CATEGORÍA principal.")
                # --- Botón para Sugerir (CON CORRECCIÓN DE SCOPE) ---
                if st.button("🤖 Sugerir CATEGORÍAS Faltantes", key="suggest_cats"):
                    # *** Redefinir variables necesarias DENTRO del callback ***
                    cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; desc = 'CONCEPTO'; imp_calc = 'importe'; imp_orig = 'IMPORTE'; ph_cat = 'SIN CATEGORÍA'; ph_sub = 'SIN SUBCATEGORÍA'

                    suggestions_applied = 0
                    df_suggest = st.session_state.edited_df.copy() # Trabajar sobre copia de sesión

                    # Asegurar que 'importe' existe y es numérico en la copia
                    if imp_orig in df_suggest.columns:
                        df_suggest.rename(columns={imp_orig: imp_calc}, inplace=True)
                    elif imp_calc not in df_suggest.columns:
                        st.error(f"Error crítico: Falta columna '{imp_calc}' para sugerir.")
                        st.stop()
                    if not pd.api.types.is_numeric_dtype(df_suggest[imp_calc]):
                         df_suggest[imp_calc] = pd.to_numeric(df_suggest[imp_calc].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                    # Identificar índices a actualizar en la copia
                    suggest_mask = (df_suggest[cat] == ph_cat) # Usar ph_cat redefinido localmente
                    indices_to_update = df_suggest[suggest_mask].index

                    # Iterar y aplicar sugerencias a la copia
                    for index in indices_to_update:
                        row = df_suggest.loc[index]
                        # Usar variables redefinidas localmente
                        sugg_cat, sugg_sub = suggest_category(row, desc, imp_calc, cat, subcat)
                        applied_c = False
                        # Usar ph_cat y ph_sub redefinidos localmente
                        if sugg_cat and df_suggest.loc[index, cat] == ph_cat:
                            df_suggest.loc[index, cat] = sugg_cat
                            applied_c = True
                        if sugg_sub and df_suggest.loc[index, subcat] == ph_sub:
                            if applied_c or (sugg_cat is None and df_suggest.loc[index, cat] != ph_cat):
                                df_suggest.loc[index, subcat] = sugg_sub
                                applied_c = True
                        if applied_c: suggestions_applied += 1

                    # Actualizar sesión si hubo cambios
                    if suggestions_applied > 0:
                        st.session_state.edited_df = df_suggest.copy()
                        st.success(f"Se aplicaron {suggestions_applied} sugerencias.")
                        convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se encontraron sugerencias.")
            else:
                st.success("¡Todo categorizado!")

            # --- Filtros y Editor ---
            st.subheader("Editar Transacciones")
            col_f1, col_f2, col_f3 = st.columns([1,1,2]);
            with col_f1:
                 # Usar el número recalculado
                 show_uncat_edit = st.checkbox("Solo sin CATEGORÍA", value=(current_num_uncategorized > 0), key='chk_uncat_edit', disabled=(current_num_uncategorized == 0))
            with col_f2: year_opts = ["Todos"] + sorted([int(a) for a in df[ano].dropna().unique()]); year_sel = st.selectbox("Año:", year_opts, key='sel_a_edit') # ano definido fuera
            with col_f3: txt_filter = st.text_input("Buscar Desc:", key='txt_edit_filter')

            # Aplicar filtros para mostrar en editor (usando df de sesión)
            df_display_edit = st.session_state.edited_df.copy()
            # Recalcular máscara sobre este df display
            display_mask = (df_display_edit[cat] == ph_cat) # cat y ph_cat definidos al inicio de la pestaña
            if show_uncat_edit: df_display_edit = df_display_edit[display_mask]
            if year_sel != "Todos":
                 if ano in df_display_edit.columns: df_display_edit = df_display_edit[df_display_edit[ano] == year_sel] # ano definido fuera
                 else: st.error(f"Columna '{ano}' no encontrada.") # ano definido fuera
            if txt_filter: df_display_edit = df_display_edit[df_display_edit[desc].str.contains(txt_filter, case=False, na=False)] # desc definido fuera
            df_display_edit['original_index'] = df_display_edit.index

            # Opciones Selectbox Editor
            cats_opts = sorted([str(c) for c in st.session_state.edited_df[cat].unique() if pd.notna(c) and c != ph_cat]) # cat y ph_cat definidos al inicio de la pestaña
            subcats_opts = sorted([str(s) for s in st.session_state.edited_df[subcat].unique() if pd.notna(s) and s != ph_sub]) # subcat y ph_sub definidos al inicio de la pestaña

            col_cfg = { cat: st.column_config.SelectboxColumn(cat, options=cats_opts, required=False), subcat: st.column_config.SelectboxColumn(subcat, options=subcats_opts, required=False), imp_calc: st.column_config.NumberColumn("Importe", format="%.2f €"), 'Fecha': st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"), 'original_index': None, ano: None, mes: None, } # cat, subcat, imp_calc, ano, mes definidos fuera o al inicio pestaña
            edited_data = st.data_editor( df_display_edit, column_config=col_cfg, use_container_width=True, num_rows="dynamic", key='data_editor_main', hide_index=True, height=400 )

            # Botón Aplicar Cambios Manuales
            if st.button("💾 Aplicar Cambios Editados", key="apply_manual_changes"):
                # *** Redefinir variables necesarias DENTRO del callback ***
                cat = 'CATEGORÍA'; subcat = 'SUBCATEGORIA'; # Redefinir las que se usan aquí

                changes_manual = 0; df_session = st.session_state.edited_df; edit_cols = [cat, subcat]
                indices_edited = edited_data['original_index']
                if indices_edited.is_unique:
                    # Actualización más eficiente usando .loc y .values
                    df_session.loc[indices_edited, edit_cols] = edited_data[edit_cols].values
                    # Para contar cambios reales, necesitaríamos comparar antes y después
                    changes_manual = len(indices_edited) # Simplificación: asumir que todas las filas mostradas cambiaron
                    st.session_state.edited_df = df_session.copy()
                    st.success(f"{changes_manual} filas actualizadas en sesión.")
                    convert_df_to_csv.clear(); st.experimental_rerun()
                else:
                    # Fallback si hay índices duplicados (menos probable con el índice original)
                    st.warning("Detectados índices no únicos, aplicando cambios fila por fila.")
                    for _, edited_row in edited_data.iterrows():
                        orig_idx = edited_row['original_index']
                        if orig_idx in df_session.index:
                            for c in edit_cols:
                                 if c in edited_row and edited_row[c] != df_session.loc[orig_idx, c]:
                                      df_session.loc[orig_idx, c] = edited_row[c]; changes_manual += 1
                    if changes_manual > 0:
                        st.session_state.edited_df = df_session.copy()
                        st.success(f"{changes_manual} cambios manuales aplicados."); convert_df_to_csv.clear(); st.experimental_rerun()
                    else: st.info("No se detectaron cambios manuales.")


            # Descargar Datos
            st.subheader("Descargar Datos"); st.caption("Descarga el CSV con las últimas categorías.")
            # Usar variable definida fuera o al inicio de pestaña
            csv_dl = convert_df_to_csv(st.session_state.edited_df)
            st.download_button( label="📥 Descargar CSV Actualizado", data=csv_dl, file_name=f"Gastos_Cat_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', key='dl_cat')

        # --- Fin Pestaña 3 ---
