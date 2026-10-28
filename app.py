import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Mi Caja Diaria", page_icon="📦", layout="centered")

# ==========================================
# 2. CONEXIÓN A GOOGLE SHEETS (VERSIÓN NUBE)
# ==========================================
@st.cache_resource
def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Leemos las credenciales desde los secretos de Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    cliente = gspread.authorize(creds)
    # ATENCIÓN: Reemplaza 'Caja_App' si tu Google Sheet se llama diferente
    sheet = cliente.open("Caja_App").sheet1 
    return sheet

sheet = conectar_sheets()

# ==========================================
# 3. INTERFAZ: REGISTRO DE OPERACIONES
# ==========================================
st.title("📦 Sistema de Caja Diaria")
st.markdown("---")

st.header("📝 Registrar Nueva Operación")

with st.form("registro_form"):
    tipo_op = st.selectbox("Tipo de Operación", ["Ingreso (Venta)", "Retiro", "Gasto"])
    metodo = st.radio("Método", ["Efectivo", "Mercado Pago (MP)"], horizontal=True)
    monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f")
    
    subcategoria = "-"
    if tipo_op == "Retiro":
        subcategoria = st.selectbox("Destino del Retiro", ["Familia", "Propios"])
        
    observaciones = "-"
    if tipo_op in ["Retiro", "Gasto"]:
        observaciones = st.text_input("Observaciones (Opcional)")
        
    submit = st.form_submit_button("Guardar Operación")

if submit:
    if monto <= 0:
        st.error("El monto debe ser mayor a 0.")
    else:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila = [fecha_actual, tipo_op, metodo, subcategoria, monto, observaciones]
        sheet.append_row(fila)
        st.success(f"✅ Operación de {tipo_op} guardada con éxito.")

# ==========================================
# 4. DASHBOARD Y SALDOS
# ==========================================
st.markdown("---")
st.header("📊 Resumen de Saldos")

ocultar_saldos = st.toggle("👁️ Ocultar saldos", value=False)

try:
    datos = sheet.get_all_records()
    if datos:
        df = pd.DataFrame(datos)
        
        # Cálculos de saldos
        ingresos_efectivo = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        salidas_efectivo = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        saldo_efectivo = ingresos_efectivo - salidas_efectivo
        
        ingresos_mp = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        salidas_mp = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        saldo_mp = ingresos_mp - salidas_mp
        
        col1, col2, col3 = st.columns(3)
        
        def mostrar_monto(valor):
            return "***" if ocultar_saldos else f"${valor:,.2f}"
