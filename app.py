import streamlit as st
import pandas as pd
import io
import traceback
from datetime import datetime
from fpdf import FPDF
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURACIÓN CSS Y DISEÑO MODERNO CORPORATIVO ---
st.set_page_config(page_title="Comisiones | Taller", layout="wide")
st.markdown("""
<style>
    [data-testid="stHeader"] { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .stApp { background-color: #F4F5F7; color: #333333; font-family: 'Segoe UI', Roboto, sans-serif; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulseSoft { 0% { transform: scale(1); } 50% { transform: scale(1.02); color: #C00500; } 100% { transform: scale(1); } }
    .racing-header { background: linear-gradient(135deg, #001A35 0%, #002C5F 100%); color: white; padding: 25px; text-align: center; border-radius: 12px; margin-bottom: 25px; border-bottom: 5px solid #E10600; box-shadow: 0 10px 20px rgba(0,0,0,0.08); animation: fadeIn 0.6s ease-out; }
    .racing-header h2 { margin: 0; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }
    .metric-card { background: #FFFFFF; border-left: 6px solid #E10600; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; margin-top: 15px; transition: all 0.3s ease; animation: fadeIn 0.8s ease-out; }
    .metric-card:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
    .metric-card h3 { color: #001A35; font-size: 1.1rem; margin-bottom: 5px; font-weight: 600; }
    .metric-card h1 { color: #E10600; font-size: 2.5rem; margin: 0; font-weight: 900; animation: pulseSoft 2.5s infinite; }
    .historial-box { background-color: #FFFFFF; border-left: 4px solid #1A73E8; padding: 15px 20px; border-radius: 8px; margin-bottom: 5px; font-size: 0.95rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04); animation: fadeIn 0.5s ease-out; display: flex; justify-content: space-between; align-items: center;}
    .stButton > button { border-radius: 8px !important; font-weight: 600 !important; transition: all 0.3s ease !important; border: 1px solid #D1D5DB !important; background-color: #FFFFFF !important; color: #374151 !important; }
    .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important; border-color: #002C5F !important; color: #002C5F !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #E10600 0%, #B00500 100%) !important; color: white !important; border: none !important; }
    .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #C00500 0%, #800400 100%) !important; box-shadow: 0 6px 15px rgba(225, 6, 0, 0.25) !important; color: white !important; }
    .action-caption { font-size: 0.85rem; color: #6B7280; text-align: center; margin-top: 6px; line-height: 1.3; }
</style>
<div class="racing-header"><h2>Módulo de Autorización de Comisiones</h2></div>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE FIREBASE CON ALERTAS ---
try:
    if not firebase_admin._apps:
        if "firebase" not in st.secrets:
            st.error("🚨 **Error Crítico:** No se encontró la llave de Firebase en los Secretos de Streamlit.", icon="🛑")
            st.stop()
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error("🚨 **Error Crítico de Conexión:** Imposible conectar con Google Firestore.", icon="📡")
    with st.expander("🔍 Ver detalles técnicos"): st.code(traceback.format_exc())
    st.stop() 

def cargar_datos_firebase(documento, valor_por_defecto):
    try:
        doc_ref = db.collection('comisiones_app').document(documento)
        doc = doc_ref.get()
        if doc.exists: return doc.to_dict().get('datos', valor_por_defecto)
        return valor_por_defecto
    except Exception as e: return valor_por_defecto

def guardar_datos_firebase(documento, datos):
    try: db.collection('comisiones_app').document(documento).set({'datos': datos})
    except Exception as e:
        st.error(f"🚨 Error al guardar en la nube: '{documento}'.", icon="💾")

# --- CARGA DE MEMORIAS GLOBALES DESDE FIREBASE ---
lista_penalizaciones = cargar_datos_firebase('penalizaciones', [])
if isinstance(lista_penalizaciones, dict): 
    lista_penalizaciones = list(set([item for sublist in lista_penalizaciones.values() for item in sublist]))
conceptos_guardados = cargar_datos_firebase('conceptos_autorizados', [])
asesores_config = cargar_datos_firebase('asesores_config', {})
historial_auditorias = cargar_datos_firebase('historial_auditorias', {})
datos_caratula = cargar_datos_firebase('datos_caratula', {})
kpi_config = cargar_datos_firebase('kpi_config', {}) 
kpi_data = cargar_datos_firebase('kpi_data', {}) 

# Variables de Sesión
if 'df_procesado' not in st.session_state: st.session_state.df_procesado = pd.DataFrame()
if 'df_crudo_ajustado' not in st.session_state: st.session_state.df_crudo_ajustado = pd.DataFrame()
if 'asesor_detectado' not in st.session_state: st.session_state.asesor_detectado = ""
if 'nombre_archivo' not in st.session_state: st.session_state.nombre_archivo = ""
if 'tabla_id' not in st.session_state: st.session_state.tabla_id = 0

# --- GENERADOR DE PDF ---
def crear_pdf(datos, mes, anio):
    try:
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 14)
        pdf.cell(0, 8, 'CRUFER 2000 S. DE R.L. DE C.V.', ln=True, align='C')
        pdf.cell(0, 8, 'COMISIONES VALORES AGREGADOS', ln=True, align='C')
        pdf.cell(0, 8, f'MES DE {mes.upper()} {anio}', ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font('helvetica', 'B', 9)
        headers = ['No.', 'PUESTO', 'EMPLEADO', 'OBJETIVO', 'VENTA', 'UTILIDAD', '% CUMP.', 'COMISION 20%']
        widths = [10, 40, 75, 30, 30, 30, 25, 35]
        for i, h in enumerate(headers): pdf.cell(widths[i], 10, h, border=1, align='C')
        pdf.ln()
        
        pdf.set_font('helvetica', '', 9)
        t_obj = t_ven = t_util = t_comis = 0
        
        for idx, (clave, data) in enumerate(datos.items(), 1):
            pdf.cell(widths[0], 10, str(idx), border=1, align='C')
            pdf.cell(widths[1], 10, 'ASESOR DE SERVICIO', border=1, align='C')
            nombre_limpio = data.get('nombre_completo', 'DESCONOCIDO').encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(widths[2], 10, nombre_limpio, border=1, align='C')
            pdf.cell(widths[3], 10, f"${data.get('objetivo', 0):,.2f}", border=1, align='C')
            pdf.cell(widths[4], 10, f"${data.get('venta', 0):,.2f}", border=1, align='C')
            pdf.cell(widths[5], 10, f"${data.get('utilidad', 0):,.2f}", border=1, align='C')
            
            cump = (data.get('venta', 0) / data.get('objetivo', 1)) * 100 if data.get('objetivo', 0) > 0 else 0
            if cump >= 90: pdf.set_text_color(0, 128, 0)
            else: pdf.set_text_color(255, 0, 0)
            pdf.cell(widths[6], 10, f"{cump:.2f}%", border=1, align='C')
            pdf.set_text_color(0, 0, 0)
            
            pdf.cell(widths[7], 10, f"${data.get('comision', 0):,.2f}", border=1, align='C')
            pdf.ln()
            t_obj += data.get('objetivo', 0); t_ven += data.get('venta', 0)
            t_util += data.get('utilidad', 0); t_comis += data.get('comision', 0)
            
        pdf.set_font('helvetica', 'B', 9)
        pdf.cell(widths[0]+widths[1], 10, '', border=0)
        pdf.cell(widths[2], 10, 'TOTAL ASESORES DE VENTAS', border=1, align='R')
        pdf.cell(widths[3], 10, f"${t_obj:,.2f}", border=1, align='C')
        pdf.cell(widths[4], 10, f"${t_ven:,.2f}", border=1, align='C')
        pdf.cell(widths[5], 10, f"${t_util:,.2f}", border=1, align='C')
        
        t_cump = (t_ven / t_obj) * 100 if t_obj > 0 else 0
        pdf.cell(widths[6], 10, f"{t_cump:.2f}%", border=1, align='C')
        pdf.cell(widths[7], 10, f"${t_comis:,.2f}", border=1, align='C')
        pdf.ln(25)
        
        pdf.set_font('helvetica', 'B', 8)
        y_firma = pdf.get_y()
        pdf.set_xy(30, y_firma)
        pdf.cell(60, 5, 'ELABORO', align='C')
        pdf.set_xy(30, y_firma + 25)
        pdf.cell(60, 5, '___________________________________', align='C')
        pdf.set_xy(30, y_firma + 30)
        pdf.cell(60, 5, 'ADMINISTRADOR DE POSTVENTA', align='C')
        pdf.set_xy(30, y_firma + 55)
        pdf.cell(60, 5, '___________________________________', align='C')
        pdf.set_xy(30, y_firma + 60)
        pdf.cell(60, 5, 'GERENTE POST VENTA', align='C')
        
        pdf.set_xy(160, y_firma)
        pdf.cell(90, 5, 'VALIDA Y AUTORIZA', align='C')
        pdf.set_xy(160, y_firma + 25)
        pdf.cell(90, 5, '___________________________________', align='C')
        pdf.set_xy(160, y_firma + 30)
        pdf.cell(90, 5, 'LIC. FREDDY ALBERTO REYES GONZALEZ', align='C')
        pdf.set_xy(160, y_firma + 35)
        pdf.cell(90, 5, 'GERENTE DE COMPRAS E INVENTARIOS', align='C')
        pdf.set_xy(160, y_firma + 50)
        pdf.cell(90, 5, 'AUTORIZA', align='C')
        pdf.set_xy(160, y_firma + 75)
        pdf.cell(90, 5, '___________________________________', align='C')
        pdf.set_xy(160, y_firma + 80)
        pdf.cell(90, 5, 'LIC. SERGIO CRUCES FERNANDEZ', align='C')
        pdf.set_xy(160, y_firma + 85)
        pdf.cell(90, 5, 'DIRECTOR COMERCIAL', align='C')
        
        return pdf.output(dest='S').encode('latin1')
    except Exception as e: return None

# --- GENERADOR DE EXCEL DEPURADO ORDENADO ---
def generar_excel_depurado(df_completo, conceptos_aprobados, lista_negra):
    try:
        df_export = df_completo.copy()
        df_export['ESTADO_PAGO'] = 'NO PAGADO'
        patron_exclusiones = '|'.join(['FILTER', 'FILTRO', 'GASKET', 'JUEGO', 'PLUG', 'COBRAND'])
        mask_pagado = ((~df_export['NO.FACTURA'].astype(str).str.endswith(tuple(lista_negra), na=False)) & (df_export['CLASIFICACION'].isin(['MO DE REPARACION', 'REFACCIONES'])) & (~df_export['DESCRIPCION'].str.upper().str.contains(patron_exclusiones, na=False)) & (df_export['DESCRIPCION'].isin(conceptos_aprobados)))
        df_export.loc[mask_pagado, 'ESTADO_PAGO'] = 'PAGADO'
        df_pagado = df_export[df_export['ESTADO_PAGO'] == 'PAGADO'].drop(columns=['ESTADO_PAGO']).sort_values(by='NO.FACTURA', ascending=True)
        df_nopagado = df_export[df_export['ESTADO_PAGO'] == 'NO PAGADO'].drop(columns=['ESTADO_PAGO']).sort_values(by='NO.FACTURA', ascending=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_pagado.to_excel(writer, index=False, sheet_name='Pagado')
            df_nopagado.to_excel(writer, index=False, sheet_name='No Pagado')
        return output.getvalue()
    except Exception as e: return None

def pintar_fila_clara(row):
    color = 'background-color: #D6E4FF; color: #001A35; font-weight: 600;' if row.get('✔ PAGAR', False) else ''
    return [color] * len(row)

# --- MENÚ DE PESTAÑAS (AHORA 4 PESTAÑAS) ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis Excel", "⚙️ Configuración y Asesores", "📄 Carátula PDF", "📈 KPI Refacciones"])

# ==========================================
# TAB 1: ANÁLISIS Y PROCESAMIENTO
# ==========================================
with tab1:
    if historial_auditorias:
        st.markdown("### 🕒 Últimos Registros Guardados en la Nube")
        for asesor, hist in historial_auditorias.items():
            col_info, col_btn = st.columns([5, 1])
            with col_info: st.markdown(f"<div class='historial-box'><span>👤 <b>{asesor}:</b> Archivo <i>{hist['archivo']}</i> procesado el {hist['fecha']} | <b>Total: ${hist.get('total', 0):,.2f}</b></span></div>", unsafe_allow_html=True)
            with col_btn:
                if st.button("✏️ Editar", key=f"recuperar_{asesor}", use_container_width=True):
                    try:
                        snapshot_procesado = cargar_datos_firebase(f"snap_proc_{asesor}", [])
                        snapshot_crudo = cargar_datos_firebase(f"snap_crudo_{asesor}", [])
                        if snapshot_procesado and snapshot_crudo:
                            df_snap = pd.DataFrame(snapshot_procesado)
                            if 'DESCRIPCION' in df_snap.columns: df_snap['✔ PAGAR'] = df_snap['DESCRIPCION'].isin(conceptos_guardados)
                            st.session_state.df_procesado = df_snap
                            st.session_state.df_crudo_ajustado = pd.DataFrame(snapshot_crudo)
                            st.session_state.asesor_detectado = asesor
                            st.session_state.nombre_archivo = hist['archivo']
                            st.session_state.tabla_id += 1 
                            st.rerun()
                        else: st.warning("⚠️ No se encontraron las fotos de respaldo en la nube de este asesor.")
                    except Exception as e: st.error("🚨 Error recuperando la tabla.")
            
    with st.form("form_datos"):
        archivo_excel = st.file_uploader("Arrastra aquí tu reporte por asesor (.xls o .xlsx):", type=["xls", "xlsx"])
        procesar = st.form_submit_button("⚡ Procesar Información", type="primary")

    if procesar and archivo_excel:
        try:
            df_crudo = pd.read_excel(archivo_excel, sheet_name=0, header=3)
            df_crudo.columns = df_crudo.columns.astype(str).str.strip().str.upper()
            columnas_req = ['ASESOR', 'NO.FACTURA', 'DESCRIPCION', 'PRECIO TOTAL', 'CLASIFICACION', 'COSTO UNI.', 'PRECIO UNI.', 'CANT./HRS.']
            if all(col in df_crudo.columns for col in columnas_req):
                nombre_crudo = df_crudo['ASESOR'].dropna().astype(str).iloc[0].upper()
                st.session_state.asesor_detectado = nombre_crudo
                st.session_state.nombre_archivo = archivo_excel.name
                
                df_base = df_crudo.copy()
                df_base['CLASIFICACION'] = df_base['CLASIFICACION'].astype(str).str.strip().str.upper()
                for col in ['COSTO UNI.', 'PRECIO UNI.', 'PRECIO TOTAL', 'COSTO TOTAL', 'UTILIDAD']:
                    if col in df_base.columns:
                        if df_base[col].dtype == object: df_base[col] = df_base[col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
                        df_base[col] = pd.to_numeric(df_base[col], errors='coerce').fillna(0.0)
                df_base['CANT./HRS.'] = pd.to_numeric(df_base['CANT./HRS.'], errors='coerce').fillna(0.0)
                
                utilidad_cobrand = 0.0
                filas_cobrand = df_base[df_base['DESCRIPCION'].str.upper().str.contains('COBRAND', na=False)]
                if not filas_cobrand.empty: utilidad_cobrand = filas_cobrand['PRECIO UNI.'].mean() - filas_cobrand['COSTO UNI.'].mean()
                
                mask_5w30_base = df_base['DESCRIPCION'].str.upper().str.contains('5W30', na=False)
                if mask_5w30_base.any() and utilidad_cobrand > 0:
                    df_base.loc[mask_5w30_base, 'UTILIDAD'] = (df_base.loc[mask_5w30_base, 'PRECIO UNI.'] - df_base.loc[mask_5w30_base, 'COSTO UNI.'] - utilidad_cobrand) * df_base.loc[mask_5w30_base, 'CANT./HRS.']
                
                st.session_state.df_crudo_ajustado = df_base
                df_pantalla = df_base.copy()
                if lista_penalizaciones: df_pantalla = df_pantalla[~df_pantalla['NO.FACTURA'].astype(str).str.endswith(tuple(lista_penalizaciones), na=False)]
                df_pantalla = df_pantalla[df_pantalla['CLASIFICACION'].isin(['MO DE REPARACION', 'REFACCIONES'])]
                patron = '|'.join(['FILTER', 'FILTRO', 'GASKET', 'JUEGO', 'PLUG', 'COBRAND'])
                df_pantalla = df_pantalla[~df_pantalla['DESCRIPCION'].str.upper().str.contains(patron, na=False)]
                
                if not df_pantalla.empty:
                    tabla_resumen = df_pantalla.groupby(['CLASIFICACION', 'DESCRIPCION']).agg(
                        LINEAS=('DESCRIPCION', 'count'), PIEZAS_LITROS=('CANT./HRS.', 'sum'), PRECIO_TOTAL=('PRECIO TOTAL', 'sum'), COSTO_TOTAL=('COSTO TOTAL', 'sum'), UTILIDAD=('UTILIDAD', 'sum')
                    ).reset_index()
                    tabla_resumen['COMISION_20'] = tabla_resumen['UTILIDAD'] * 0.20
                    tabla_resumen = tabla_resumen.sort_values(by=['CLASIFICACION', 'DESCRIPCION'], ascending=[False, True]).reset_index(drop=True)
                    tabla_resumen.insert(0, '✔ PAGAR', tabla_resumen['DESCRIPCION'].isin(conceptos_guardados))
                    st.session_state.df_procesado = tabla_resumen
                    st.session_state.tabla_id += 1 
                else: st.warning("⚠️ Sin conceptos válidos tras aplicar filtros.")
            else: st.error("🚨 Faltan columnas estructurales en el Excel.")
        except Exception as e: st.error("🚨 Error leyendo Excel.")

    if not st.session_state.df_procesado.empty:
        st.markdown(f"### 🎯 Auditando: {st.session_state.asesor_detectado}")
        
        asesor_encontrado, objetivo_detectado = None, 0
        for clave, config in asesores_config.items():
            if clave.upper() in st.session_state.asesor_detectado.upper():
                asesor_encontrado = config.get('nombre_completo', clave); objetivo_detectado = config.get('objetivo', 0); break
        
        if not asesor_encontrado: st.warning("⚠️ Asesor no registrado en Configuración.")
        
        df_pintado = st.session_state.df_procesado.style.apply(pintar_fila_clara, axis=1)
        editor_key = f"editor_{st.session_state.asesor_detectado}_{st.session_state.tabla_id}"
        
        df_editado = st.data_editor(
            df_pintado, use_container_width=True, hide_index=True, key=editor_key,
            column_config={
                "✔ PAGAR": st.column_config.CheckboxColumn("✔ PAGAR", required=True), "CLASIFICACION": st.column_config.TextColumn(disabled=True), "DESCRIPCION": st.column_config.TextColumn(disabled=True),
                "LINEAS": st.column_config.NumberColumn(disabled=True), "PIEZAS_LITROS": st.column_config.NumberColumn("CANTIDAD", disabled=True), "PRECIO_TOTAL": st.column_config.NumberColumn(format="$%.2f", disabled=True),
                "COSTO_TOTAL": st.column_config.NumberColumn(format="$%.2f", disabled=True), "UTILIDAD": st.column_config.NumberColumn(format="$%.2f", disabled=True), "COMISION_20": st.column_config.NumberColumn("COMISIÓN", format="$%.2f", disabled=True),
            }
        )
        
        st.session_state.df_procesado['✔ PAGAR'] = df_editado['✔ PAGAR']
        df_pagados = df_editado[df_editado['✔ PAGAR'] == True]
        t_venta = df_pagados['PRECIO_TOTAL'].sum() if not df_pagados.empty else 0
        t_utilidad = df_pagados['UTILIDAD'].sum() if not df_pagados.empty else 0
        t_comision = df_pagados['COMISION_20'].sum() if not df_pagados.empty else 0
        conceptos_actuales = df_pagados['DESCRIPCION'].tolist()
        
        st.markdown(f"<div class='metric-card'><h3>Total a Pagar Autorizado</h3><h1>${t_comision:,.2f}</h1></div>", unsafe_allow_html=True)
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            st.write("")
            if st.button("💾 Memorizar Selección y KPIs", use_container_width=True):
                # 1. Guardar conceptos marcados
                guardar_datos_firebase('conceptos_autorizados', conceptos_actuales)
                
                # 2. CALCULAR Y GUARDAR KPI DE REFACCIONES
                if kpi_config:
                    nombre_kpi = asesor_encontrado if asesor_encontrado else st.session_state.asesor_detectado
                    kpi_resultados = {}
                    df_crudo = st.session_state.df_crudo_ajustado
                    for concepto in kpi_config.keys():
                        mask = df_crudo['DESCRIPCION'].astype(str).str.upper().str.contains(concepto.upper(), regex=False, na=False)
                        suma_cant = df_crudo.loc[mask, 'CANT./HRS.'].sum()
                        kpi_resultados[concepto] = float(suma_cant)
                    
                    kpi_data[nombre_kpi] = kpi_resultados
                    guardar_datos_firebase('kpi_data', kpi_data)
                    
                st.success(f"¡Plantilla global y KPIs guardados en Firebase!")
            st.markdown("<div class='action-caption'>Guarda la plantilla y suma los KPIs de este asesor.</div>", unsafe_allow_html=True)
        
        with col_b2:
            st.write("")
            if asesor_encontrado and st.button("➕ Añadir / Actualizar Carátula PDF", use_container_width=True, type="primary"):
                datos_caratula[asesor_encontrado] = {"nombre_completo": asesor_encontrado, "objetivo": objetivo_detectado, "venta": t_venta, "utilidad": t_utilidad, "comision": t_comision}
                guardar_datos_firebase('datos_caratula', datos_caratula)
                historial_auditorias[asesor_encontrado] = {"archivo": st.session_state.nombre_archivo, "fecha": datetime.now().strftime("%d/%m/%Y %I:%M %p"), "total": t_comision}
                guardar_datos_firebase('historial_auditorias', historial_auditorias)
                guardar_datos_firebase(f"snap_proc_{asesor_encontrado}", st.session_state.df_procesado.to_dict('records'))
                guardar_datos_firebase(f"snap_crudo_{asesor_encontrado}", st.session_state.df_crudo_ajustado.to_dict('records'))
                st.success(f"¡Datos sobreescritos en la nube!")
                st.rerun()
            st.markdown("<div class='action-caption'>Envía el total de dinero a la Pestaña 3.</div>", unsafe_allow_html=True)

        with col_b3:
            st.write("")
            excel_bytes = generar_excel_depurado(st.session_state.df_crudo_ajustado, conceptos_actuales, lista_penalizaciones)
            if excel_bytes:
                st.download_button(label="📥 Descargar Depurado", data=excel_bytes, file_name=f"Reporte_{asesor_encontrado}_{datetime.now().strftime('%d%m%Y')}.xlsx" if asesor_encontrado else "Reporte_Depurado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            st.markdown("<div class='action-caption'>Descarga el Excel ordenado (Pagado / No Pagado).</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: CONFIGURACIÓN
# ==========================================
with tab2:
    st.markdown("### 👥 Administración de Asesores y Objetivos (Comisiones)")
    asesores_lista = []
    if asesores_config:
        for clave, config in asesores_config.items():
            asesores_lista.append({'CLAVE EXCEL': str(clave), 'NOMBRE COMPLETO': str(config.get('nombre_completo', clave)), 'OBJETIVO MENSUAL': float(config.get('objetivo', 0.0))})
        df_asesores = pd.DataFrame(asesores_lista)
    else: df_asesores = pd.DataFrame(columns=['CLAVE EXCEL', 'NOMBRE COMPLETO', 'OBJETIVO MENSUAL'])

    df_editado_asesores = st.data_editor(df_asesores, use_container_width=True, num_rows="dynamic", key="editor_asesores", column_config={"OBJETIVO MENSUAL": st.column_config.NumberColumn("OBJETIVO MENSUAL", format="$%.2f", min_value=0.0), "CLAVE EXCEL": st.column_config.TextColumn("CLAVE EXCEL", required=True), "NOMBRE COMPLETO": st.column_config.TextColumn("NOMBRE COMPLETO", required=True)})
    
    if st.button("🔄 Guardar Cambios de Asesores", type="primary"):
        nuevo_config = {}
        caratula_act = False
        for index, row in df_editado_asesores.iterrows():
            if pd.notna(row['CLAVE EXCEL']) and str(row['CLAVE EXCEL']).strip() != "" and str(row['CLAVE EXCEL']).strip() != "nan":
                clave = str(row['CLAVE EXCEL']).strip().upper()
                nombre = str(row['NOMBRE COMPLETO']).strip().upper()
                if nombre == "NAN" or not nombre: nombre = clave
                nuevo_objetivo = float(row['OBJETIVO MENSUAL']) if pd.notna(row['OBJETIVO MENSUAL']) else 0.0
                nuevo_config[clave] = {"nombre_completo": nombre, "objetivo": nuevo_objetivo}
                if nombre in datos_caratula:
                    if datos_caratula[nombre].get('objetivo') != nuevo_objetivo:
                        datos_caratula[nombre]['objetivo'] = nuevo_objetivo
                        caratula_act = True
        guardar_datos_firebase('asesores_config', nuevo_config)
        if caratula_act: guardar_datos_firebase('datos_caratula', datos_caratula)
        st.success("¡Catálogo actualizado!")
        st.rerun()
            
    st.divider()
    st.markdown("### 🎯 Configuración de KPIs (Refacciones)")
    st.info("Agrega los nombres exactos (o palabras clave) de los Kits o aceites que quieres medir y su meta mensual.")
    
    kpi_lista = []
    if kpi_config:
        for concepto, meta in kpi_config.items():
            kpi_lista.append({'CONCEPTO': str(concepto), 'OBJETIVO MENSUAL': float(meta)})
        df_kpi_conf = pd.DataFrame(kpi_lista)
    else: df_kpi_conf = pd.DataFrame(columns=['CONCEPTO', 'OBJETIVO MENSUAL'])
    
    df_editado_kpi = st.data_editor(
        df_kpi_conf, use_container_width=True, num_rows="dynamic", key="editor_kpi",
        column_config={
            "CONCEPTO": st.column_config.TextColumn("CONCEPTO (Ej. 5W30, KIT AFINACION)", required=True),
            "OBJETIVO MENSUAL": st.column_config.NumberColumn("OBJETIVO (Cantidad)", format="%.0f", min_value=0.0)
        }
    )
    
    if st.button("🔄 Guardar KPIs en Nube", type="primary"):
        nuevo_kpi = {}
        for idx, row in df_editado_kpi.iterrows():
            if pd.notna(row['CONCEPTO']) and str(row['CONCEPTO']).strip() != "" and str(row['CONCEPTO']).strip() != "nan":
                concepto = str(row['CONCEPTO']).strip().upper()
                meta = float(row['OBJETIVO MENSUAL']) if pd.notna(row['OBJETIVO MENSUAL']) else 0.0
                nuevo_kpi[concepto] = meta
        guardar_datos_firebase('kpi_config', nuevo_kpi)
        st.success("¡Configuración de KPIs guardada!")
        st.rerun()

    st.divider()
    st.markdown("### 🚫 Facturas Penalizadas (Global)")
    f_nueva = st.text_input("Ingresa los últimos 5 dígitos de la factura:", max_chars=5)
    if f_nueva and st.button("Penalizar Factura"):
        if f_nueva not in lista_penalizaciones:
            lista_penalizaciones.append(f_nueva); guardar_datos_firebase('penalizaciones', lista_penalizaciones); st.rerun()
    lista_act = st.multiselect("Quitar Penalización (Click en la X):", options=lista_penalizaciones, default=lista_penalizaciones)
    if lista_act != lista_penalizaciones: guardar_datos_firebase('penalizaciones', lista_act); st.rerun()

# ==========================================
# TAB 3: CARÁTULA Y PDF
# ==========================================
with tab3:
    st.markdown("### 📄 Opciones de Carátula Mensual")
    col_m1, col_m2 = st.columns(2)
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    with col_m1: mes_sel = st.selectbox("Mes a Reportar:", meses, index=datetime.now().month-1)
    with col_m2: anio_sel = st.number_input("Año:", min_value=2024, max_value=2050, value=datetime.now().year)

    if not datos_caratula: st.info("No hay datos cargados en la nube para la carátula.")
    else:
        try:
            df_preview = pd.DataFrame(datos_caratula).T
            df_display = df_preview.copy()
            df_display['% CUMP'] = df_display.apply(lambda r: (r['venta']/r['objetivo'])*100 if r['objetivo'] > 0 else 0, axis=1)
            df_display['% CUMP'] = df_display['% CUMP'].map("{:.2f}%".format)
            for col in ['objetivo', 'venta', 'utilidad', 'comision']: df_display[col] = df_display[col].map("${:,.2f}".format)
            st.table(df_display[['nombre_completo', 'objetivo', 'venta', 'utilidad', '% CUMP', 'comision']])
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                pdf_bytes = crear_pdf(datos_caratula, mes_sel, str(anio_sel))
                if pdf_bytes: st.download_button(label="📥 Descargar Carátula PDF", data=pdf_bytes, file_name=f"Comisiones_{mes_sel}_{anio_sel}.pdf", mime="application/pdf", type="primary", use_container_width=True)
            with col_b2:
                if st.button("🗑️ Vaciar Carátula Mensual (Borra Nube)", use_container_width=True):
                    guardar_datos_firebase('datos_caratula', {}); guardar_datos_firebase('historial_auditorias', {}); st.rerun()
        except Exception as e:
            st.error("🚨 Error al armar la tabla de resumen visual de la Carátula.", icon="📉")
            with st.expander("🔍 Detalles técnicos (Carátula)"): st.code(traceback.format_exc())

# ==========================================
# TAB 4: KPI REFACCIONES Y WURTH
# ==========================================
with tab4:
    st.markdown("### 📈 Dashboard de Objetivos Mensuales (Refacciones)")
    st.info("Este panel suma automáticamente las cantidades vendidas cada vez que procesas y 'Memorizas' el Excel de un asesor.")
    
    if not kpi_config:
        st.warning("⚠️ No has dado de alta ningún Kit/Concepto para medir. Ve a la pestaña 'Configuración y Asesores'.")
    elif not kpi_data:
        st.info("Esperando datos... Procesa el Excel de un asesor y presiona '💾 Memorizar Selección y KPIs' en la Pestaña 1.")
    else:
        try:
            rows = []
            asesores_kpi = list(kpi_data.keys())
            
            # Construcción de la tabla cruzada de KPIs
            for concepto, meta in kpi_config.items():
                row = {'Concepto': concepto}
                total_asesores = 0
                for asesor in asesores_kpi:
                    val = kpi_data[asesor].get(concepto, 0.0)
                    row[asesor] = val
                    total_asesores += val
                
                row['Total'] = total_asesores
                row['Objetivo'] = float(meta)
                row['Dif. Objetivo'] = total_asesores - float(meta)
                rows.append(row)
                
            df_kpi = pd.DataFrame(rows)
            # Reordenamos para que Total quede al inicio y Objetivo al final
            cols_kpi = ['Concepto', 'Total'] + asesores_kpi + ['Objetivo', 'Dif. Objetivo']
            df_kpi = df_kpi[cols_kpi]
            
            def pintar_kpi(val):
                if isinstance(val, (int, float)):
                    if val < 0: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
                    elif val > 0: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
                    else: return 'background-color: #E0E0E0; font-weight: bold; color: #424242;'
                return ''

            st.dataframe(
                df_kpi.style.map(pintar_kpi, subset=['Dif. Objetivo']).format(precision=1),
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            
            # --- NUEVA SECCIÓN: BONOS WURTH ---
            st.markdown("### 💰 Monto de Wurth A PAGAR")
            st.info("Se calculan $50 por cada Kit configurado en tus KPIs, excepto 'KIT ESTETICA EXTERIOR' que vale $25.")
            
            wurth_rows = []
            for asesor in asesores_kpi:
                bono_total = 0.0
                for concepto, cantidad in kpi_data[asesor].items():
                    concepto_upper = str(concepto).strip().upper()
                    # Solo aplica si el KPI empieza con "KIT"
                    if concepto_upper.startswith("KIT"):
                        if concepto_upper == "KIT ESTETICA EXTERIOR":
                            bono_total += float(cantidad) * 25.0
                        else:
                            bono_total += float(cantidad) * 50.0
                wurth_rows.append({"ASESOR": asesor, "MONTO A PAGAR": bono_total})
                
            if wurth_rows:
                df_wurth = pd.DataFrame(wurth_rows)
                
                def estilo_wurth(row):
                    # Da estilo azul para el nombre y verde para el dinero (similar a tu imagen)
                    return ['background-color: #4A90E2; color: white; font-weight: bold; font-size: 15px;', 
                            'background-color: #E8F5E9; color: #1B5E20; font-weight: bold; font-size: 15px;']
                
                st.dataframe(
                    df_wurth.style.apply(estilo_wurth, axis=1).format({"MONTO A PAGAR": "${:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
            
            st.write("")
            if st.button("🗑️ Reiniciar KPIs Mensuales (Inicia de cero)", type="primary"):
                guardar_datos_firebase('kpi_data', {})
                st.success("¡Datos de KPI y Wurth borrados!")
                st.rerun()
                
        except Exception as e:
            st.error("🚨 Error al armar el Dashboard de KPIs o Bonos Wurth.", icon="📊")
            with st.expander("🔍 Detalles técnicos"): st.code(traceback.format_exc())
