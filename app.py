import streamlit as st
import folium
from streamlit_folium import st_folium
import os
import json
import streamlit.components.v1 as components
from branca.element import MacroElement
from jinja2 import Template

# إعداد الصفحة لتكون واسعة ومتوافقة مع الجوال
st.set_page_config(page_title="خريطة المسيلة الصحية", page_icon="🗺️", layout="wide", initial_sidebar_state="auto")

# ==========================================
# إعدادات الـ CSS والطباعة الاحترافية (إخفاء كل شيء ما عدا الخريطة)
# ==========================================
st.markdown("""
    <style>
    /* خلفية بيضاء نقية للخريطة */
    .leaflet-container { background-color: #ffffff !important; }
    
    /* تحسين شكل التبويبات (Tabs) لتبدو كأزرار تطبيقات الجوال */
    div[data-testid="stTabs"] button {
        font-size: 16px;
        font-weight: bold;
    }
    
    /* =========================================
       إعدادات الطباعة الصارمة (PDF Mode)
    ========================================= */
    @media print {
        @page {
            margin: 0 !important; 
            size: landscape; 
        }
        body, html {
            margin: 0 !important;
            padding: 0 !important;
            background-color: #ffffff !important;
            overflow: hidden !important;
        }
        
        /* 1. إخفاء واجهة Streamlit بالكامل */
        section[data-testid="stSidebar"], header, footer, .stApp > header { display: none !important; }
        div[data-testid="stMarkdownContainer"] { display: none !important; }
        iframe[title="streamlit_components.v1.components.html"] { display: none !important; }
        div[data-testid="stTabs"] { display: none !important; }
        
        /* 2. تجهيز حاوية الخريطة لتملأ الورقة */
        .block-container { 
            padding: 0 !important; 
            margin: 0 !important; 
            max-width: 100% !important; 
        }
        
        /* 3. جعل الخريطة عائمة فوق كل شيء وتملأ الشاشة */
        iframe[title="streamlit_folium.st_folium"] {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: 9999 !important;
            border: none !important;
        }
        
        /* 4. (هام جداً) إخفاء أزرار التحكم في الخريطة (Zoom +/-) وحقوق النشر */
        .leaflet-control-container, .leaflet-top, .leaflet-bottom { display: none !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ الخريطة الصحية لولاية المسيلة")

# ==========================================
# قاموس الألوان والنظام
# ==========================================
FACILITY_COLORS = {
    "مستشفى": "#b71c1c", 
    "عيادة H24": "#d32f2f", 
    "عيادة H12": "#f57c00", 
    "عيادة H8": "#1976d2", 
    "قاعة علاج": "#388e3c"
}

DATA_FILE = "saved_data.json"

def load_data():
    default_data = {
        "markers": [], 
        "commune_styles": {}, 
        "global_settings": {
            "lang": "العربية", 
            "show_names": True,
            "show_hospital_names": True,
            "hospital_font_size": 14,
            "map_zoom": 9,
            "map_center": [35.3, 4.5]
        }
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "global_settings" not in data:
                    data["global_settings"] = default_data["global_settings"]
                if "map_zoom" not in data["global_settings"]:
                    data["global_settings"]["map_zoom"] = 9
                    data["global_settings"]["map_center"] = [35.3, 4.5]
                return data
        except json.decoder.JSONDecodeError:
            return default_data
    return default_data

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "markers": st.session_state.markers,
            "commune_styles": st.session_state.commune_styles,
            "global_settings": st.session_state.global_settings
        }, f, ensure_ascii=False, indent=4)

if 'data_loaded' not in st.session_state:
    saved_info = load_data()
    st.session_state.markers = saved_info.get("markers", [])
    st.session_state.commune_styles = saved_info.get("commune_styles", {})
    st.session_state.global_settings = saved_info.get("global_settings")
    st.session_state.data_loaded = True

geojson_file = "msila_communes.geojson"
geojson_data = None
if os.path.exists(geojson_file):
    with open(geojson_file, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    geojson_data['features'] = [f for f in geojson_data.get('features', []) if f.get('geometry', {}).get('type') in ['Polygon', 'MultiPolygon']]

# ==========================================
# القائمة الجانبية (بنظام التبويبات العصري للموبايل)
# ==========================================
st.sidebar.markdown("### لوحة التحكم")
# تقسيم القائمة الجانبية إلى 4 تبويبات مرتبة
tab_general, tab_add, tab_manage, tab_export = st.sidebar.tabs(["⚙️ إعدادات", "➕ إضافة", "🛠️ تعديل", "📤 تصدير"])

# ------------------------------------------
# 1. تبويب الإعدادات العامة وتلوين البلديات
# ------------------------------------------
with tab_general:
    st.markdown("#### الإعدادات العامة")
    current_lang = st.session_state.global_settings["lang"]
    current_show_names = st.session_state.global_settings["show_names"]
    
    new_lang = st.radio("🌐 لغة الخريطة:", ["العربية", "Français"], index=0 if current_lang == "العربية" else 1)
    new_show_names = st.checkbox("👁️ إظهار أسماء البلديات", value=current_show_names)
    
    current_show_hosp = st.session_state.global_settings["show_hospital_names"]
    current_font_size = st.session_state.global_settings.get("hospital_font_size", 14)
    
    new_show_hosp = st.checkbox("👁️ إظهار جميع أسماء المرافق", value=current_show_hosp)
    new_font_size = st.slider("🔠 الحجم الافتراضي لخط المرافق:", 8, 35, current_font_size, 1)

    if (new_lang != current_lang or new_show_names != current_show_names or 
        new_show_hosp != current_show_hosp or new_font_size != current_font_size):
        st.session_state.global_settings.update({
            "lang": new_lang, "show_names": new_show_names,
            "show_hospital_names": new_show_hosp, "hospital_font_size": new_font_size
        })
        save_data()
        st.rerun()

    lang = st.session_state.global_settings["lang"]
    show_names = st.session_state.global_settings["show_names"]
    show_hospital_names = st.session_state.global_settings["show_hospital_names"]
    global_font_size = st.session_state.global_settings["hospital_font_size"]

    st.markdown("---")
    st.markdown("#### 🎨 تلوين البلديات")
    if geojson_data:
        commune_list = sorted([f['properties'].get('name:ar', f['properties'].get('name', '')) for f in geojson_data['features']])
        selected_commune = st.selectbox("اختر بلدية لتعديلها:", commune_list)
        current_style = st.session_state.commune_styles.get(selected_commune, {"color": "#e3f2fd", "show_name": show_names, "lang": lang})
        
        new_color = st.color_picker("🎨 لون الخلفية:", current_style["color"])
        new_show = st.checkbox(f"👁️ إظهار اسم '{selected_commune}'", value=current_style["show_name"], key="show_ind")
        new_lang_ind = st.radio("🌐 لغة هذه البلدية:", ["العربية", "Français"], index=0 if current_style["lang"] == "العربية" else 1, key="lang_ind")
        
        col_a, col_b = st.columns(2)
        if col_a.button("💾 حفظ البلدية", use_container_width=True):
            st.session_state.commune_styles[selected_commune] = {"color": new_color, "show_name": new_show, "lang": new_lang_ind}
            save_data()
            st.rerun()
        if col_b.button("🔄 إرجاع", use_container_width=True):
            if selected_commune in st.session_state.commune_styles:
                del st.session_state.commune_styles[selected_commune]
                save_data()
                st.rerun()

# ------------------------------------------
# 2. تبويب إضافة مرفق جديد
# ------------------------------------------
with tab_add:
    st.markdown("#### 📍 إضافة مرفق صحي")
    facility_types = list(FACILITY_COLORS.keys())
    fac_type = st.selectbox("🏥 نوع المرفق:", facility_types)
    place_name_ar = st.text_input("الاسم (عربي):")
    place_name_fr = st.text_input("الاسم (فرنسي):")
    lat = st.number_input("خط العرض:", value=35.7056, format="%.6f")
    lon = st.number_input("خط الطول:", value=4.5419, format="%.6f")

    if st.button("➕ إضافة للخريطة", use_container_width=True, type="primary"):
        if place_name_ar or place_name_fr:
            default_color = FACILITY_COLORS.get(fac_type, "#b71c1c")
            st.session_state.markers.append({
                "type": fac_type, "name_ar": place_name_ar, "name_fr": place_name_fr, 
                "lat": lat, "lon": lon, "text_x": 0, "text_y": 35,      
                "font_size": global_font_size, "name_color": default_color,  
                "label_size": 15, "label_color": default_color  
            })
            save_data()
            st.success("✅ تم الإضافة بنجاح!")
            st.rerun()

# ------------------------------------------
# 3. تبويب تعديل وإدارة المرافق
# ------------------------------------------
with tab_manage:
    st.markdown("#### 🛠️ تحريك وتعديل المرافق")
    if len(st.session_state.markers) == 0:
        st.info("لم يتم إضافة أي مرافق بعد.")
    else:
        for i, marker in enumerate(st.session_state.markers):
            display_title = marker.get('name_ar', marker.get('name_fr', ''))
            current_type = marker.get('type', 'مستشفى')
            
            with st.expander(f"📍 {display_title} ({current_type})"):
                new_type = st.selectbox("النوع:", facility_types, index=facility_types.index(current_type), key=f"type_{i}")
                new_name_ar = st.text_input("الاسم (عربي):", marker.get('name_ar', ''), key=f"name_ar_{i}")
                new_name_fr = st.text_input("الاسم (فرنسي):", marker.get('name_fr', ''), key=f"name_fr_{i}")
                
                def_col = FACILITY_COLORS.get(current_type, "#b71c1c")
                curr_name_color = marker.get('name_color', def_col)
                curr_lbl_size = marker.get('label_size', 15)
                curr_lbl_color = marker.get('label_color', def_col)
                
                st.markdown("**🎨 تخصيص اسم المرفق:**")
                col_n1, col_n2 = st.columns(2)
                new_font = col_n1.slider("الحجم:", 8, 45, marker.get('font_size', global_font_size), key=f"font_{i}")
                new_name_color = col_n2.color_picker("اللون:", curr_name_color, key=f"ncolor_{i}")
                
                new_lbl_size = curr_lbl_size
                new_lbl_color = curr_lbl_color
                if new_type in ["عيادة H24", "عيادة H12", "عيادة H8"]:
                    lbl_name = new_type.split()[1]
                    st.markdown(f"**🎨 تخصيص الرمز {lbl_name}:**")
                    col_l1, col_l2 = st.columns(2)
                    new_lbl_size = col_l1.slider("حجم الرمز:", 8, 45, curr_lbl_size, key=f"lsize_{i}")
                    new_lbl_color = col_l2.color_picker("لون الرمز:", curr_lbl_color, key=f"lcolor_{i}")

                st.markdown("**موضع النص (تحريك حر):**")
                col_x, col_y = st.columns(2)
                new_text_x = col_x.number_input("يمين/يسار:", value=marker.get('text_x', 0), step=5, key=f"tx_{i}")
                new_text_y = col_y.number_input("أعلى/أسفل:", value=marker.get('text_y', 35), step=5, key=f"ty_{i}")
                
                st.markdown("**الإحداثيات الجغرافية:**")
                new_lat = st.number_input("خط العرض:", value=marker['lat'], format="%.6f", key=f"lat_{i}")
                new_lon = st.number_input("خط الطول:", value=marker['lon'], format="%.6f", key=f"lon_{i}")
                
                # الحفظ التلقائي عند التعديل
                marker.update({
                    "type": new_type, "name_ar": new_name_ar, "name_fr": new_name_fr,
                    "lat": new_lat, "lon": new_lon, "text_x": new_text_x, "text_y": new_text_y,
                    "font_size": new_font, "name_color": new_name_color,
                    "label_size": new_lbl_size, "label_color": new_lbl_color
                })
                save_data()

                if st.button("🗑️ حذف المرفق", key=f"del_{i}", use_container_width=True):
                    st.session_state.markers.pop(i)
                    save_data()
                    st.rerun()

# ------------------------------------------
# 4. تبويب تصدير وطباعة الخريطة (تم التحديث: PDF فقط)
# ------------------------------------------
with tab_export:
    st.markdown("#### 📤 تصدير الخريطة")
    # تم حذف خيار PNG، والإبقاء فقط على خيار الطباعة PDF مع العنوان
    components.html("""
        <script>
            function printWithTitle() {
                var title = window.prompt("✍️ أدخل عنوان الخريطة (سيظهر في أعلى الورقة):\\n\\n(اتركه فارغاً إذا كنت لا تريد طباعة عنوان)", "الخريطة الصحية لولاية المسيلة");
                
                if (title !== null) { 
                    var parentDoc = window.parent.document;
                    var titleDiv = parentDoc.getElementById('print-custom-title');
                    
                    if (!titleDiv) {
                        titleDiv = parentDoc.createElement('div');
                        titleDiv.id = 'print-custom-title';
                        parentDoc.body.appendChild(titleDiv);
                        
                        var style = parentDoc.createElement('style');
                        style.innerHTML = `
                            @media screen { 
                                #print-custom-title { display: none !important; } 
                            }
                            @media print {
                                #print-custom-title {
                                    display: block !important;
                                    position: fixed;
                                    top: 20px;
                                    left: 0;
                                    width: 100vw;
                                    text-align: center;
                                    font-size: 34px;
                                    font-weight: 900;
                                    font-family: Arial, sans-serif;
                                    z-index: 999999 !important;
                                    color: #1a237e;
                                    text-shadow: 2px 2px 0px #fff, -2px -2px 0px #fff, 2px -2px 0px #fff, -2px 2px 0px #fff, 0px 4px 8px rgba(0,0,0,0.3);
                                    direction: rtl;
                                }
                            }
                        `;
                        parentDoc.head.appendChild(style);
                    }
                    
                    if(title.trim() === "") {
                        titleDiv.style.display = 'none';
                    } else {
                        titleDiv.style.display = '';
                        titleDiv.innerText = title;
                    }
                    
                    setTimeout(() => {
                        window.parent.print();
                    }, 300);
                }
            }
        </script>

        <button onclick="printWithTitle()" style="width: 100%; padding: 15px; background-color: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; font-family: Arial; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            🖨️ طباعة أو حفظ كـ PDF
        </button>
        
        <div style="margin-top: 15px; font-family: Arial; font-size: 13px; color: #555; text-align: center; direction: rtl;">
            💡 <b>نصيحة هامة:</b> للحصول على خريطة نقية تماماً بدون أي حواف، في نافذة الطباعة اختر "Save as PDF" وتأكد من جعل الهوامش (Margins) <b>"بدون" (None)</b>.
        </div>
    """, height=150)

# ==========================================
# 3. إعداد الخريطة ورسم البيانات
# ==========================================
# استرجاع إحداثيات وتكبير الخريطة من الذاكرة 
saved_zoom = st.session_state.global_settings.get("map_zoom", 9)
saved_center = st.session_state.global_settings.get("map_center", [35.3, 4.5])

m = folium.Map(
    location=saved_center, 
    zoom_start=saved_zoom, 
    tiles=None, 
    control_scale=True,
    zoom_snap=0.25,  
    zoom_delta=0.25
)

# نظام التكبير السلس الاحترافي (MacroElement)
class DynamicScalePlugin(MacroElement):
    _template = Template("""
    {% macro script(this, kwargs) %}
    var map_instance = {{ this._parent.get_name() }};
    
    function updateMarkerScale() {
        var current_zoom = map_instance.getZoom();
        var base_zoom = 9; 
        var scale = Math.pow(1.25, current_zoom - base_zoom);
        scale = Math.max(0.3, Math.min(scale, 3.5));
        document.documentElement.style.setProperty('--marker-scale', scale);
    }

    map_instance.on('zoomend', updateMarkerScale);
    updateMarkerScale(); 
    {% endmacro %}
    """)

m.add_child(DynamicScalePlugin())

if geojson_data:
    def style_function(feature):
        name_ar_key = feature['properties'].get('name:ar', feature['properties'].get('name', ''))
        style = st.session_state.commune_styles.get(name_ar_key, {"color": "#e3f2fd"})
        opacity = 0.7 if style["color"] != "#e3f2fd" else 0.4
        return {'fillColor': style["color"], 'color': '#0d47a1', 'weight': 1.5, 'fillOpacity': opacity}

    folium.GeoJson(
        geojson_data, name="بلديات المسيلة", style_function=style_function,
        highlight_function=lambda feature: {'weight': 3, 'color': '#b71c1c', 'fillOpacity': 0.8}
    ).add_to(m)

    for feature in geojson_data['features']:
        props = feature['properties']
        geom = feature['geometry']
        name_ar_key = props.get('name:ar', props.get('name', ''))
        c_style = st.session_state.commune_styles.get(name_ar_key, {"show_name": show_names, "lang": lang})
        
        if c_style["show_name"]:
            lang_key_to_use = 'name:ar' if c_style["lang"] == "العربية" else 'name:fr'
            name_to_display = props.get(lang_key_to_use, props.get('name', ''))
            coords = []
            if geom['type'] == 'Polygon': coords = geom['coordinates'][0]
            elif geom['type'] == 'MultiPolygon': coords = geom['coordinates'][0][0]
            
            if coords:
                lats = [p[1] for p in coords]
                lons = [p[0] for p in coords]
                folium.Marker(
                    location=[sum(lats)/len(lats), sum(lons)/len(lons)],
                    icon=folium.DivIcon(html=f"""<div style="font-size: 13px; font-weight: bold; color: #1a237e; background: transparent; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff; transform: translate(-50%, -50%) scale(var(--marker-scale, 1)); transition: transform 0.2s ease-out; transform-origin: center center; white-space: nowrap; direction: {"rtl" if c_style["lang"] == "العربية" else "ltr"}; pointer-events: none;">{name_to_display}</div>""")
                ).add_to(m)

for marker in st.session_state.markers:
    m_type = marker.get('type', 'مستشفى')
    
    def_col = FACILITY_COLORS.get(m_type, "#b71c1c")
    t_x = marker.get('text_x', 0)
    t_y = marker.get('text_y', 35)
    f_size = marker.get('font_size', global_font_size)
    n_color = marker.get('name_color', def_col)
    
    lbl_size = marker.get('label_size', 15)
    lbl_color = marker.get('label_color', def_col)
    
    if m_type in ["عيادة H24", "عيادة H12", "عيادة H8"]:
        label_text = m_type.split(" ")[1]
        top_lbl = f"<div style='color: {lbl_color}; font-weight: 900; font-size: {lbl_size}px; background: transparent; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff;'>{label_text}</div>"
        emoji = "🏥"
    elif m_type == "قاعة علاج":
        top_lbl = ""
        emoji = "🩺"
    else: 
        top_lbl = ""
        emoji = f"<div style='color: #b71c1c; font-weight: 900; font-size: 24px; font-family: Arial, sans-serif;'>H</div>"

    name_ar = marker.get('name_ar', '')
    name_fr = marker.get('name_fr', '')
    display_name = name_ar if lang == "العربية" and name_ar else name_fr if name_fr else name_ar
    
    text_html = ""
    if show_hospital_names:
        text_html = f"""
        <div style='
            position: absolute;
            top: {t_y}px;
            left: {t_x}px;
            transform: translateX(-50%);
            direction: {"rtl" if lang == "العربية" else "ltr"}; 
            font-family: Arial, sans-serif; 
            font-weight: 900; 
            font-size: {f_size}px; 
            color: {n_color}; 
            background: transparent;
            white-space: nowrap; 
            text-align: center; 
            text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff;
            pointer-events: none;
        '>
            {display_name}
        </div>
        """

    icon_html = f"""
    <div style="position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; transform: translate(-50%, -50%) scale(var(--marker-scale, 1)); transform-origin: center center; transition: transform 0.2s ease-out; width: 40px; height: 40px;">
        <div style="display: flex; flex-direction: column; align-items: center;">
            {top_lbl}
            <div style="font-size: 18px; filter: drop-shadow(2px 3px 3px rgba(0,0,0,0.4));">{emoji}</div>
        </div>
        {text_html}
    </div>
    """

    folium.Marker(
        location=[marker["lat"], marker["lon"]],
        icon=folium.DivIcon(html=icon_html) 
    ).add_to(m)

# ==========================================
# استشعار حركة الخريطة وحفظها التلقائي، وعرض متجاوب للشاشات
# ==========================================
# السر الأهم للجوال: use_container_width=True يجعل الخريطة تتمدد وتتقلص حسب الشاشة بدلاً من عرض ثابت
map_data = st_folium(m, use_container_width=True, height=700, returned_objects=["zoom", "center"])

if map_data and map_data.get("zoom") is not None and map_data.get("center") is not None:
    current_zoom = map_data["zoom"]
    current_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
    
    if current_zoom != saved_zoom or current_center != saved_center:
        st.session_state.global_settings["map_zoom"] = current_zoom
        st.session_state.global_settings["map_center"] = current_center
        save_data()