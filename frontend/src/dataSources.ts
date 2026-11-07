// Where every fixed number in SolarOpt comes from, grouped like the app's steps. Shown in "Nguồn lấy số liệu"
// (components/DataSources.tsx); the raw price tables and quotes are in docs/bang_chung/. To update a number: change it
// in the file named in `used`, then change `value`, `sources` and `checked` here in the same commit.

/** verified: read on the issuer's or seller's own page · secondary: press or third-party page · assumption: no public source yet. */
export type SourceStatus='verified'|'secondary'|'assumption'
export type Source={label:string;url?:string}
export type DataItem={name:string;value:string;used:string;status:SourceStatus;sources:Source[];checked:string;note?:string}
export type DataSection={id:string;title:string;where:string;items:DataItem[]}

export const SOURCES_CHECKED='07/11/2026'
export const EVIDENCE_DOC='docs/bang_chung/README.md'

const solarSaigon={label:'Solar Saigon — bảng giá tấm pin (cập nhật 26/05/2026)',url:'https://solarsaigon.vn/gia-pin-nang-luong-mat-troi'}
const dhcPanels={label:'DHC Solar — giá tấm pin',url:'https://www.dhcsolar.com/gia-tam-pin-nang-luong-mat-troi-moi-nhat/'}
const tcPanels={label:'TC Energy — tấm pin (11/2026)',url:'https://tcenergy.vn/danh-muc/tam-pin-nang-luong-mat-troi/'}
const kitawa={label:'Kitawa — bảng giá tấm pin 6/2026',url:'https://kitawa.com.vn/tam-pin-nang-luong-mat-troi'}
const dhcHuawei={label:'DHC Solar — inverter Huawei',url:'https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-huawei/'}
const dhcGrowatt={label:'DHC Solar — inverter Growatt',url:'https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-growatt/'}
const dhcSungrow={label:'DHC Solar — inverter Sungrow',url:'https://www.dhcsolar.com/danh-muc-san-pham/bien-tan-nang-luong-mat-troi/inverter-sungrow/'}
const megasolar={label:'Megasolar — Huawei 5 kW 1 pha',url:'https://megasolar.vn/san-pham/inverter-huawei-5kw-1-pha/'}
const dhcAcc={label:'DHC Solar — phụ kiện',url:'https://www.dhcsolar.com/danh-muc-san-pham/phu-kien-dien-mat-troi/'}
const tcAcc={label:'TC Energy — phụ kiện',url:'https://tcenergy.vn/danh-muc/phu-kien-nang-luong-mat-troi/'}
const qd2892={label:'QĐ 2892/QĐ-BCT (31/10/2026, hiệu lực 01/11/2026) — Cổng PBGDPL Cần Thơ',url:'https://pbgdpl.cantho.gov.vn/quy-dinh-ve-gia-ban-dien'}
const nd243={label:'NĐ 243/2026/NĐ-CP sửa NĐ 58/2025 — Báo Đấu thầu',url:'https://baodauthau.vn/dien-mat-troi-mai-nha-noi-tran-ban-dien-du-thoat-canh-chay-bam-tai-post201837.html'}
const pccc207={label:'207/C07-P4 thay 3288/C07-P4 — Diễn đàn Doanh nghiệp',url:'https://diendandoanhnghiep.vn/dien-mat-troi-mai-nha-cho-doanh-nghiep-dieu-kien-an-toan-pccc-ra-sao-10140597.html'}

export const DATA_SECTIONS:DataSection[]=[
 {id:'input',title:'Dữ liệu đầu vào và ảnh mái',where:'Bước Dữ liệu đầu vào, Xác nhận bản vẽ',items:[
  {name:'Ảnh vệ tinh Google Maps / Google Earth',value:'Chỉ để tham khảo; không dùng để vẽ lại biên mái khi bán thương mại',used:'Gợi ý trong App.tsx, ImageTracer.tsx',status:'verified',checked:'07/11/2026',
   sources:[{label:'Google — hướng dẫn dùng ảnh Google Earth/Maps',url:'https://about.google/brand-resource-center/products-and-services/geo-guidelines/'}],note:'Điều khoản Google cấm dùng ảnh vệ tinh cho mục đích thương mại và cấm vẽ lại biên công trình. Thay bằng Esri World Imagery hoặc ảnh drone.'},
  {name:'Esri World Imagery (thay thế)',value:'2.000.000 ô ảnh miễn phí/tháng, sau đó 0,15 USD/1.000 ô',used:'Mô hình chi phí (build_cost_model.py)',status:'verified',checked:'07/11/2026',sources:[{label:'ArcGIS Location Platform',url:'https://location.arcgis.com/help/deployment/'}]},
 ]},
 {id:'sun',title:'Nắng, thời tiết và tổn thất',where:'Bước Nắng và bóng che',items:[
  {name:'Thời tiết năm điển hình',value:'PVGIS TMY (ERA5 2005–2023), tải theo tọa độ công trình',used:'backend services/weather.py',status:'verified',checked:'04/11/2026',sources:[{label:'PVGIS API (EU JRC)',url:'https://re.jrc.ec.europa.eu/pvg_tools/en/'}]},
  {name:'Sản lượng/kWp tại TP.HCM (đối chiếu)',value:'SolarOpt ≈ 1.416 · PVGIS PVcalc 1.385 · Global Solar Atlas 1.446 kWh/kWp',used:'docs/SO_LIEU_CHUAN.md',status:'verified',checked:'04/11/2026',sources:[{label:'PVGIS PVcalc',url:'https://re.jrc.ec.europa.eu/pvg_tools/en/'},{label:'Global Solar Atlas',url:'https://globalsolaratlas.info'}]},
  {name:'Bảng tổn thất mặc định',value:'bụi 4% · phản xạ 2,5% · tấm 2% · lệch 1,5% · cáp DC 1,5% · inverter 2,5% · cáp AC 1% · ngừng 2%',used:'frontend yieldLosses.ts, backend schemas.py',status:'assumption',checked:'07/11/2026',sources:[],note:'Mức thông dụng khi mô phỏng (kiểu PVsyst); chưa đo tại công trình Việt Nam. Hệ số nhiệt −0,32%/°C; LONGi Hi-MO 6 ghi −0,29%/°C.'},
 ]},
 {id:'panels',title:'Tấm pin và bố trí',where:'Bước Bố trí tấm pin',items:[
  {name:'LONGi Hi-MO 6 580 W (tấm mặc định)',value:'2.650.000 đ/tấm (4.569 đ/Wp)',used:'frontend panelLibrary.ts, App.tsx; backend schemas.py',status:'verified',checked:'07/11/2026',sources:[solarSaigon,dhcPanels]},
  {name:'LONGi LR5-72HTH-580M thông số điện',value:'Voc 52,21 V · Vmp 44,06 V · Imp 13,17 A · Isc 14,20 A · 1134 × 2278 mm',used:'frontend panelLibrary.ts, App.tsx',status:'secondary',checked:'07/11/2026',sources:[{label:'Solar Proof (chép datasheet LONGi)',url:'https://solarproof.com.au/products/LR5-72HTH-580MHi-MOX6Explorer.php'}],note:'Trang longi.com chặn đọc tự động; đối chiếu datasheet bản giấy khi mua.'},
  {name:'JA Solar JAM72S30 550 W',value:'2.200.000 đ/tấm (4.000 đ/Wp)',used:'frontend panelLibrary.ts',status:'verified',checked:'07/11/2026',sources:[dhcPanels]},
  {name:'Canadian HiKu6 410 W',value:'1.650.000 đ/tấm (≈ 4.000 đ/Wp)',used:'frontend panelLibrary.ts',status:'secondary',checked:'07/11/2026',sources:[solarSaigon],note:'Không có niêm yết riêng 410 W; theo đ/Wp của Canadian HiKu6 550 W (4.127 đ/Wp).'},
  {name:'Khoảng giá tấm để cảnh báo',value:'3.100–4.600 đ/Wp (tấm 540–720 W; trung vị ≈ 3.946)',used:'frontend panelLibrary.ts',status:'verified',checked:'07/11/2026',sources:[solarSaigon,dhcPanels,tcPanels,kitawa]},
  {name:'Bố trí theo PCCC',value:'nhóm ≤ 40 × 40 m, cách nhau 1,5 m · cách lối ra mái 3 m · cách lan can 2,5 m',used:'backend services/geometry.py',status:'secondary',checked:'07/11/2026',sources:[pccc207,{label:'3288/C07-P4 (2020) — Thư viện pháp luật',url:'https://thuvienphapluat.vn/cong-van/Xay-dung-Do-thi/Cong-van-3288-C07-P4-2020-tham-duyet-thiet-ke-phong-chay-chua-chay-nha-may-dien-mat-troi-453461.aspx'}],note:'3288 đã được thay bằng 207/C07-P4 (09/8/2024). Nhóm 40 × 40 m và khe 1,5 m được xác nhận; 3 m và 2,5 m lấy từ 3288 — cần đối chiếu toàn văn 207.'},
 ]},
 {id:'electrical',title:'Thiết kế điện và vật tư',where:'Bước Kiểm tra & bàn giao → Thiết kế điện',items:[
  {name:'Giá inverter Huawei',value:'3 kW 15,5 tr · 5 kW 17 tr · 10 kW 27 tr · 15 kW 38,2 tr · 20 kW 46,2 tr · 30 kW 55,5 tr · 40 kW 59,2 tr · 100 kW 107 tr',used:'backend services/electrical.py CATALOG',status:'verified',checked:'07/11/2026',sources:[dhcHuawei,megasolar],note:'5 kW và 10 kW lấy trung bình hai nhà bán (DHC 19,2 / 31,9 tr; Megasolar 15 / 22 tr). Huawei 6, 8, 12 kW chưa có niêm yết, giữ giá lập kế hoạch.'},
  {name:'Giá inverter Growatt, Sungrow, Solis',value:'Growatt 6 kW 12,6 tr · Growatt 10 kW 3 pha 21 tr · Sungrow 50 kW 67 tr · Sungrow 110 kW 106 tr · Solis 5 kW 12,5 tr',used:'backend services/electrical.py CATALOG',status:'verified',checked:'07/11/2026',sources:[dhcGrowatt,dhcSungrow],note:'Sungrow 110 kW nội suy từ SG125CX-P2 121 tr; Solis 5 kW chưa có niêm yết (Solis 6 kW 14 tr).'},
  {name:'Cáp DC solar',value:'4 mm² 18.000 đ/m · 6 mm² 24.000 đ/m · 10 mm² 42.000 đ/m',used:'backend electrical.py DC_SIZES',status:'verified',checked:'07/11/2026',sources:[dhcAcc,tcAcc],note:'10 mm² chưa có giá công khai.'},
  {name:'Phụ kiện DC/AC',value:'MC4 25.000 đ/cặp · SPD DC 350.000 · SPD AC 250.000 · tủ DC/AC 700.000',used:'backend electrical.py PRICES',status:'verified',checked:'07/11/2026',sources:[dhcAcc,tcAcc]},
  {name:'Khung và tiếp địa',value:'ray nhôm 93.000 đ/m · kẹp giữa/biên 12.000 · chân đỡ 45.000 · dây tiếp địa 25.000 đ/m · 3 cọc mạ đồng 840.000',used:'backend electrical.py PRICES',status:'verified',checked:'07/11/2026',sources:[dhcAcc,tcAcc],note:'Chân đỡ: kẹp xà gồ inox 26–36 nghìn (mái tôn), chân L mái ngói 95–97 nghìn.'},
  {name:'Công tơ / thiết bị chống phát ngược',value:'1 pha 2.700.000 · 3 pha 4.500.000',used:'backend electrical.py PRICES',status:'verified',checked:'07/11/2026',sources:[dhcAcc]},
  {name:'CB DC, cầu dao cách ly, nút dừng khẩn, cáp AC nhiều lõi, kết nối điều độ',value:'450.000 · 1.200.000 · 800.000 · theo bảng AC_CABLE · 60.000.000',used:'backend electrical.py',status:'assumption',checked:'07/11/2026',sources:[],note:'Chưa tìm thấy giá công khai; thay bằng báo giá.'},
  {name:'Ngưỡng điện áp lưới',value:'inverter ngắt 253 V (110% × 230 V); cảnh báo 241,5 V',used:'backend electrical.py',status:'assumption',checked:'07/11/2026',sources:[],note:'Theo cài đặt bảo vệ phổ biến của inverter; kiểm tra cài đặt của hãng và yêu cầu đấu nối của điện lực.'},
 ]},
 {id:'site',title:'Kết cấu, gió, an toàn, pháp lý',where:'Bước Kiểm tra & bàn giao → Khảo sát hiện trường',items:[
  {name:'Áp lực gió cơ sở W0',value:'vùng I 65 · II 95 · III 125 · IV 155 · V 185 daN/m²',used:'backend services/site.py',status:'verified',checked:'07/11/2026',sources:[{label:'TCVN 2737:2023 — Thư viện pháp luật',url:'https://thuvienphapluat.vn/TCVN/Xay-dung/TCVN-2737-2023-Tai-trong-va-tac-dong-920293.aspx'},{label:'Tạp chí Xây dựng — tải gió theo TCVN 2737:2023',url:'https://vjol.info.vn/tcxd/article/view/107280'}]},
  {name:'Hoạt tải mái',value:'mái tôn/ngói 30 daN/m² · mái bằng bê tông 75 daN/m²',used:'backend services/site.py',status:'secondary',checked:'07/11/2026',sources:[{label:'TCVN 2737:2023 — bảng hoạt tải',url:'https://thuvienphapluat.vn/TCVN/Xay-dung/TCVN-2737-2023-Tai-trong-va-tac-dong-920293.aspx'}],note:'Đối chiếu bảng hoạt tải trong bản gốc TCVN.'},
  {name:'Tải thử mặt sau tấm pin',value:'2.400 Pa',used:'backend services/site.py',status:'verified',checked:'07/11/2026',sources:[{label:'Datasheet JA Solar JAM72S30 (Solar Proof)',url:'https://solarproof.com.au/product_brands/panels/ShanghaiJASolarTechnologyCoLtd.php'}],note:'Mặt trước 5.400 Pa, mặt sau 2.400 Pa.'},
  {name:'PCCC hệ thống trên mái',value:'ngắt khẩn cấp tại inverter và tủ đóng cắt; không lắp trên mái vật liệu cháy',used:'backend services/site.py, electrical.py',status:'secondary',checked:'07/11/2026',sources:[pccc207,{label:'EVN — hướng dẫn của Cục Cảnh sát PCCC',url:'https://www.evn.com.vn/d6/news/Cuc-Canh-sat-phong-chay-chua-chay-huong-dan-dam-bao-an-toan-cho-cong-trinh-dien-mat-troi-550-18-26521.aspx'}]},
  {name:'Bán điện dư và thủ tục',value:'tối đa 50% sản lượng; NĐ 58/2025 sửa bởi NĐ 243/2026 (hiệu lực 26/6/2026)',used:'backend services/site.py, advisor/scenarios.py; frontend economics.ts',status:'secondary',checked:'07/11/2026',sources:[nd243,{label:'Thanh Niên 27/06/2026',url:'https://thanhnien.vn/dien-mat-troi-du-duoc-ban-len-luoi-voi-gia-bao-nhieu-dong-mot-kwh-185260627160423229.htm'}]},
 ]},
 {id:'economics',title:'Giá điện và kinh tế dự án',where:'Bước Kiểm tra & bàn giao → Kinh tế, Trợ lý tư vấn',items:[
  {name:'Biểu giá điện sinh hoạt',value:'1.901 · 2.289 · 2.894 · 3.456 · 3.844 đ/kWh (5 bậc, chưa VAT)',used:'frontend tariff.ts; backend advisor/tariff.py',status:'verified',checked:'07/11/2026',sources:[qd2892]},
  {name:'Giá kinh doanh, sản xuất theo giờ',value:'KD hạ áp 3.089/1.880/5.313 · KD trung áp 2.829/1.577/4.924 · SX hạ áp 1.966/1.274/3.586 · SX trung áp 1.814/1.166/3.348 (bình thường/thấp điểm/cao điểm)',used:'frontend tariff.ts; backend advisor/tariff.py',status:'verified',checked:'07/11/2026',sources:[qd2892]},
  {name:'Khung giờ cao điểm',value:'17h30–22h30 thứ Hai–thứ Bảy; thấp điểm 0h–6h',used:'frontend tariff.ts; backend advisor/tariff.py',status:'secondary',checked:'07/11/2026',sources:[{label:'QĐ 963/QĐ-BCT (22/4/2026) — Bộ Công Thương',url:'https://moit.gov.vn/tin-tuc/quy-dinh-moi-ve-gio-cao-diem-thap-diem-cua-he-thong-dien-quoc-gia.html'},{label:'Tạp chí Công Thương — điều kiện áp dụng theo TT 60/2025',url:'https://tapchicongthuong.vn/bo-cong-thuong-sua-thong-tu-ve-gia-ban-dien-de-som-ap-dung-khung-gio-cao-diem--thap-diem-moi-521358.htm'}],note:'TT 60/2025 cho áp khung giờ mới từ lần điều chỉnh giá bình quân gần nhất; QĐ 2892 (01/11/2026) là lần điều chỉnh đó. Xác nhận lại với hóa đơn EVN tháng 11/2026.'},
  {name:'VAT trên hóa đơn điện',value:'8%',used:'frontend tariff.ts; backend advisor/tariff.py',status:'assumption',checked:'07/11/2026',sources:[],note:'Mức giảm thuế GTGT áp dụng đến hết 2026; từ 2027 có thể về 10% — kiểm tra trước 01/01/2027.'},
  {name:'Giá mua điện dư năm 2026',value:'845 đ/kWh (844,8 — giá thị trường bình quân 2025)',used:'frontend economics.ts SURPLUS_PRICE',status:'secondary',checked:'07/11/2026',sources:[{label:'Thanh Niên — NSMO công văn 205 (16/01/2026)',url:'https://thanhnien.vn/dien-mat-troi-du-duoc-ban-len-luoi-voi-gia-bao-nhieu-dong-mot-kwh-185260627160423229.htm'},{label:'Tuổi Trẻ — 844 đ/kWh',url:'https://tuoitre.vn/dau-tu-tram-trieu-ban-dien-844-dong-kwh-khien-nguoi-dan-chi-lap-dien-mat-troi-du-dung-100260825093613263.htm'}],note:'Trước đây app dùng 670 đ (đề xuất năm 2024). Cập nhật mỗi tháng 1 khi NSMO công bố giá năm trước.'},
  {name:'Suất đầu tư trọn gói',value:'hộ gia đình 11–13,5 tr/kWp · kinh doanh 7,5–10 · sản xuất 7,5–8',used:'frontend economics.ts marketCapex; backend advisor/scenarios.py',status:'secondary',checked:'07/11/2026',sources:[{label:'Tinh tế — giá lắp 2026 (Bộ Công Thương: hộ 12–15 tr/kWp; DN 7,5–13)',url:'https://tinhte.vn/thread/cap-nhat-gia-lap-dien-nang-luong-mat-troi-moi-nhat-2026.4175422/'},{label:'Vietnam Solar — trọn gói 10 kWp 125–140 tr',url:'https://vietnamsolar.vn/chi-phi-lap-dien-mat-troi-hoa-luoi-10kwp-inverter-huawei-10kw-3-pha/'}]},
  {name:'Thay inverter năm 12',value:'hộ 2,2 · kinh doanh 1,5 · sản xuất 1,0 triệu đ/kWp',used:'frontend economics.ts',status:'verified',checked:'07/11/2026',sources:[dhcHuawei,dhcGrowatt],note:'Giá inverter/kW AC hiện nay chia hệ số DC/AC ≈ 1,15.'},
  {name:'Bảo trì, suy giảm, tăng giá điện, chiết khấu',value:'150.000 đ/kWp/năm · 0,55%/năm · 3%/năm · 8%/năm',used:'frontend economics.ts (trợ lý tư vấn: 100.000 đ và 0,5%)',status:'assumption',checked:'07/11/2026',sources:[],note:'Chưa có nguồn công khai cho Việt Nam; xin báo giá O&M và dùng bảo hành suy giảm trong datasheet tấm thực mua.'},
 ]},
 {id:'business',title:'Gói dịch vụ và chi phí vận hành SolarOpt',where:'Gói dự án, Lưu trữ',items:[
  {name:'Giá đối thủ, giá mô hình AI, tỷ giá',value:'Xem bảng chi tiết',used:'docs/GIA_VA_CHI_PHI_THUONG_MAI.md; output/report/SolarOpt_Mo_hinh_tai_chinh_v2.xlsx',status:'verified',checked:'07/11/2026',sources:[{label:'Bảng giá đối thủ và chi phí (tài liệu dự án)'},{label:'Tỷ giá Vietcombank — webgia',url:'https://webgia.com/ty-gia/vietcombank/'}]},
 ]},
]

export function sourceCounts(sections=DATA_SECTIONS){
 const all=sections.flatMap(s=>s.items)
 return {total:all.length,verified:all.filter(i=>i.status==='verified').length,secondary:all.filter(i=>i.status==='secondary').length,assumption:all.filter(i=>i.status==='assumption').length}
}
