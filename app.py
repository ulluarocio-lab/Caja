import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA (Móvil)
# ==========================================
st.set_page_config(page_title="Caja Diaria", page_icon="📦", layout="centered")
# ==========================================
# 2. CONEXIÓN A GOOGLE SHEETS
# ==========================================
@st.cache_resource
def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    cliente = gspread.authorize(creds)
    sheet = cliente.open("Caja_App").sheet1 
    return sheet

sheet = conectar_sheets()

# ==========================================
# 3. INTERFAZ: REGISTRO DE OPERACIONES
# ==========================================

# Inyectamos CSS para la fuente tipo Counter Strike (Título y Subtítulo)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');
    
    .titulo-cs {
        font-family: 'Black Ops One', sans-serif;
        font-size: 32px; 
        color: #E58D24; 
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .subtitulo-cs {
        font-family: 'Black Ops One', sans-serif;
        font-size: 22px; /* Apenas más chico para mantener jerarquía */
        color: #E58D24;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 15px; /* Da un poco de aire antes del formulario */
    }
    </style>
    <div class="titulo-cs">📦 CAJA DIARIA</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Reemplazamos el st.subheader normal por nuestro subtítulo personalizado
st.markdown('<div class="subtitulo-cs">📝 NUEVA OPERACIÓN</div>', unsafe_allow_html=True)

# SACAMOS EL TIPO DE OPERACIÓN AFUERA DEL FORMULARIO
# Así la interfaz se actualiza al instante al cambiar la opción
tipo_op = st.selectbox("Tipo de Operación", ["Ingreso (Venta)", "Retiro", "Gasto"])

with st.form("registro_form"):
    metodo = st.selectbox("Método", ["Efectivo", "Mercado Pago (MP)"])
    monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f", step=100.0)
    
    # Lógicas dinámicas (ahora reaccionan al instante)
    subcategoria = "-"
    if tipo_op == "Retiro":
        subcategoria = st.selectbox("Destino", ["Familia", "Propios"])
        
    observaciones = "-"
    if tipo_op in ["Retiro", "Gasto"]:
        observaciones = st.text_input("Observaciones (Opcional)")
        
    submit = st.form_submit_button("Guardar Operación", use_container_width=True)

if submit:
    if monto <= 0:
        st.error("El monto debe ser mayor a 0.")
    else:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila = [fecha_actual, tipo_op, metodo, subcategoria, monto, observaciones]
        sheet.append_row(fila)
        st.success(f"✅ {tipo_op} guardado.")

# ==========================================
# 4. DASHBOARD Y SALDOS
# ==========================================
st.markdown("---")
st.subheader("📊 Saldos")

ocultar_saldos = st.toggle("👁️ Ocultar saldos", value=False)

try:
    datos = sheet.get_all_records()
    if datos:
        df = pd.DataFrame(datos)
        
        # Cálculos
        ingresos_efectivo = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        salidas_efectivo = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        saldo_efectivo = ingresos_efectivo - salidas_efectivo
        
        ingresos_mp = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        salidas_mp = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        saldo_mp = ingresos_mp - salidas_mp
        
        def mostrar_monto(valor):
            return "***" if ocultar_saldos else f"${valor:,.2f}"

        col1, col2 = st.columns(2)
        col1.metric("💵 Efectivo", mostrar_monto(saldo_efectivo))
        col2.metric("📱 MP", mostrar_monto(saldo_mp))
        
        st.metric("💰 SALDO TOTAL", mostrar_monto(saldo_efectivo + saldo_mp))
        
        st.markdown("---")
        st.subheader("Historial")
        if ocultar_saldos:
            st.info("Oculto por privacidad.")
        else:
            st.dataframe(df.tail(10), use_container_width=True)

    else:
        st.info("No hay datos todavía.")
except Exception as e:
    st.warning("⚠️ Verifica los títulos en tu Google Sheet: Fecha, Tipo, Metodo, Subcategoria, Monto, Observaciones")
