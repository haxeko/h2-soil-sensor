"""Single source of truth for the H2 soil sensor schematic (v3: compact soil-only board).

v3 = ESP32-H2 + CR123A power stage + one connector for the popular capacitive soil moisture
module "Capacitive Soil Moisture Sensor v1.2" (analog AOUT, JST-PH 2.0 3P: GND VCC AOUT).
The battery (CR123A holder with leads) is soldered to two round pads (+ / -); programming is
done through 8 round SMD pads (pogo pins or soldered wires) instead of a pin header.

Every component lists: sheet, reference, library symbol, value, footprint,
LCSC part number, schematic position (mm, A3 sheet) / rotation and the
pin -> net mapping.  'NC' marks an intentionally unconnected pin.

Net naming
  power nets (drawn with power symbols): GND, +3V3, VBAT, VSENS
  everything else is drawn with labels (global if used on several sheets).
"""

PROJECT = "h2-soil-sensor"

POWER_NETS = {
    "GND": ("power", "GND", "gnd"),
    "+3V3": ("power", "+3V3", "supply"),
    "VBAT": ("h2soil", "VBAT", "supply"),
    "VSENS": ("h2soil", "VSENS", "supply"),
}

SHEETS = [
    dict(name="Power", file="power.kicad_sch", page="2",
         title="Power: CR123A, RPP, TPS63900 3V3, VBAT sense, VSENS"),
    dict(name="MCU", file="mcu.kicad_sch", page="3",
         title="MCU: ESP32-H2-WROOM-02C (Thread ICD)"),
    dict(name="Sensors", file="sensors.kicad_sch", page="4",
         title="Soil module connector: J4 PH2.0-3P, ESD, ADC filter"),
    dict(name="UI", file="ui.kicad_sch", page="5",
         title="UI: button, LED, programming pads"),
]

# Common footprints / parts --------------------------------------------------
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"

RES = {  # value -> (LCSC, MPN)
    "0R": ("C21189", "0603WAF0000T5E"),
    "1k": ("C21190", "0603WAF1001T5E"),
    "4.7k": ("C23162", "0603WAF4701T5E"),
    "10k": ("C25804", "0603WAF1002T5E"),
    "16.2k 1%": ("C22885", "0603WAF1622T5E"),
    "36.5k 1%": ("C23029", "0603WAF3652T5E"),
    "47k": ("C25819", "0603WAF4702T5E"),
    "100k": ("C25803", "0603WAF1003T5E"),
    "470k": ("C23178", "0603WAF4703T5E"),
    "1M": ("C22935", "0603WAF1004T5E"),
}
CAP = {  # value -> (LCSC, MPN, footprint)
    "18pF C0G": ("C1647", "CL10C180JB8NNNC", C0603),
    "100pF C0G": ("C14858", "CL10C101JB8NNNC", C0603),
    "10nF": ("C1589", "CL10B103KB8NNNC", C0603),
    "100nF": ("C14663", "CC0603KRX7R9BB104", C0603),
    "1uF": ("C15849", "CL10A105KB8NNNC", C0603),
    "10uF 10V": ("C19702", "CL10A106KP8NNNC", C0603),
    "10uF 25V": ("C15850", "CL21A106KAYNNNE", C0805),
    "22uF 25V": ("C45783", "CL21A226MAQNNNE", C0805),
    "47uF 6.3V": ("C16780", "CL21A476MQYNNNE", C0805),
}


def R(sheet, ref, value, x, y, rot, n1, n2, dnp=False, note=""):
    lcsc, mpn = RES[value]
    return dict(sheet=sheet, ref=ref, lib="Device", sym="R", value=value.replace(" 1%", ""), fp=R0603,
                lcsc=lcsc, mpn=mpn, mfr="UNI-ROYAL", dnp=dnp, x=x, y=y, rot=rot,
                pins={"1": n1, "2": n2}, note=note, tol="1%")


def C(sheet, ref, value, x, y, rot, n1, n2, dnp=False, note=""):
    lcsc, mpn, fp = CAP[value]
    mfr = "Samsung" if mpn.startswith("CL") else "YAGEO"
    return dict(sheet=sheet, ref=ref, lib="Device", sym="C", value=value, fp=fp, lcsc=lcsc, mpn=mpn, mfr=mfr,
                dnp=dnp, x=x, y=y, rot=rot, pins={"1": n1, "2": n2}, note=note)


def P(sheet, ref, lib, sym, value, fp, lcsc, mpn, mfr, x, y, rot, pins, dnp=False, note=""):
    return dict(sheet=sheet, ref=ref, lib=lib, sym=sym, value=value, fp=fp, lcsc=lcsc, mpn=mpn, mfr=mfr,
                dnp=dnp, x=x, y=y, rot=rot, pins=pins, note=note)


def FLAG(sheet, ref, x, y, net):
    return dict(sheet=sheet, ref=ref, lib="power", sym="PWR_FLAG", value="PWR_FLAG", fp="", lcsc="", mpn="",
                mfr="", dnp=False, x=x, y=y, rot=0, pins={"1": net}, note="", virtual=True)


PW, MC, SE, UI = "Power", "MCU", "Sensors", "UI"

PH2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
PH3 = "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical"

COMPONENTS = [
    # ===================================================================== POWER
    # --- battery terminals: two solder pads for the leads of the CR123A holder
    P(PW, "J3", "Connector", "Conn_01x02_Pin", "BAT (pads)", "Connector_Wire:SolderWire-0.5sqmm_1x02_P4.6mm_D0.9mm_OD2.1mm",
      "", "", "", 22.86, 83.82, 0, {"1": "VBAT_RAW", "2": "GND"}, note="2 pad han day pin (+ vuong / - tron)"),
    P(PW, "Q1", "Transistor_FET", "AO3401A", "AO3415A", SOT23, "C133233", "AO3415A", "AOS",
      66.04, 63.5, 90, {"1": "Q1_G", "2": "VBAT", "3": "VBAT_RAW"},
      note="P-MOSFET chong nguoc cuc, Vgs(th)<=1V, Rds(on) thap o Vgs=-1.8V"),
    R(PW, "R1", "100k", 66.04, 88.9, 0, "Q1_G", "GND", note="Gate Q1 ve GND"),
    C(PW, "C1", "47uF 6.3V", 91.44, 76.2, 0, "VBAT", "GND", note="Tu dem xung TX (pin lanh, day pin dai)"),
    R(PW, "R10", "0R", 111.76, 63.5, 90, "VBAT", "VIN_BB", note="Cau do dong (thao ra de gan ampe ke/PPK2)"),

    # --- TPS63900 buck-boost, VOUT = 3.3 V (SEL = low -> VO(1) = RCFG3 = 16.2k)
    P(PW, "U1", "Regulator_Switching", "TPS63900", "TPS63900DSKR",
      "h2soil:WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias_0.3mm", "C1518762", "TPS63900DSKR",
      "Texas Instruments", 195.58, 78.74, 0,
      {"1": "VIN_BB", "2": "GND", "3": "CFG1", "4": "CFG2", "5": "CFG3", "6": "+3V3", "7": "LX2", "8": "GND",
       "9": "LX1", "10": "VIN_BB", "11": "GND"},
      note="Buck-boost 75nA Iq; EN=VIN; SEL=GND"),
    C(PW, "C2", "10uF 25V", 134.62, 78.74, 0, "VIN_BB", "GND", note="CIN sat VIN/GND"),
    C(PW, "C3", "100nF", 149.86, 78.74, 0, "VIN_BB", "GND"),
    P(PW, "L1", "Device", "L", "2.2uH", "Inductor_SMD:L_1008_2520Metric", "C404804", "TFM252012ALMA2R2MTAA",
      "TDK", 195.58, 116.84, 90, {"1": "LX1", "2": "LX2"}, note="Isat >= 2A (cau hinh unlimited)"),
    R(PW, "R2", "36.5k 1%", 241.3, 93.98, 0, "CFG1", "GND", note="CFG1: VO(2)=3.3V"),
    R(PW, "R3", "0R", 256.54, 93.98, 0, "CFG2", "GND", note="CFG2: gioi han dong vao = unlimited (511R=100mA)"),
    R(PW, "R4", "16.2k 1%", 271.78, 93.98, 0, "CFG3", "GND", note="CFG3: VO(1)=3.3V (SEL=low)"),
    C(PW, "C4", "22uF 25V", 241.3, 63.5, 0, "+3V3", "GND", note="COUT sat VOUT/GND"),
    C(PW, "C5", "22uF 25V", 256.54, 63.5, 0, "+3V3", "GND"),

    # --- battery voltage measurement: high-side P-FET + N-FET level shifter, zero leakage when off
    P(PW, "Q2", "Transistor_FET", "AO3401A", "AO3401A", SOT23, "C15127", "AO3401A", "AOS",
      309.88, 63.5, 90, {"1": "QB_G", "2": "VBAT", "3": "VBAT_SW"}, note="Cong tac cau chia pin"),
    R(PW, "R5", "1M", 294.64, 88.9, 0, "VBAT", "QB_G", note="Keo gate Q2 len nguon -> OFF mac dinh"),
    P(PW, "Q3", "Transistor_FET", "2N7002", "2N7002", SOT23, "C8545", "2N7002", "CJ",
      337.82, 96.52, 0, {"1": "VBAT_MEAS_EN", "2": "GND", "3": "QB_G"}, note="Dich muc 3.3V -> gate Q2"),
    R(PW, "R6", "100k", 317.5, 121.92, 0, "VBAT_MEAS_EN", "GND", note="Keo xuong: Q3 OFF khi MCU ngu"),
    R(PW, "R7", "100k", 350.52, 63.5, 90, "VBAT_SW", "VBAT_ADC", note="Cau chia 1/2"),
    R(PW, "R8", "100k", 368.3, 78.74, 0, "VBAT_ADC", "GND"),
    C(PW, "C6", "10nF", 383.54, 78.74, 0, "VBAT_ADC", "GND"),

    # --- switched sensor rail VSENS (soil module only powered while measuring)
    P(PW, "Q4", "Transistor_FET", "AO3401A", "AO3401A", SOT23, "C15127", "AO3401A", "AOS",
      309.88, 170.18, 90, {"1": "SENS_PWR_EN_N", "2": "+3V3", "3": "VSENS"}, note="Load switch VSENS (active-low)"),
    R(PW, "R9", "100k", 294.64, 195.58, 0, "+3V3", "SENS_PWR_EN_N", note="Keo gate len 3V3 -> VSENS OFF mac dinh"),
    C(PW, "C7", "1uF", 337.82, 182.88, 0, "VSENS", "GND"),

    FLAG(PW, "#FLG01", 40.64, 220.98, "GND"),
    FLAG(PW, "#FLG02", 55.88, 220.98, "VBAT"),
    FLAG(PW, "#FLG03", 71.12, 220.98, "VSENS"),
    FLAG(PW, "#FLG04", 86.36, 220.98, "VIN_BB"),

    # ======================================================================= MCU
    P(MC, "U2", "h2soil", "ESP32-H2-WROOM-02C", "ESP32-H2-WROOM-02C-H4S", "h2soil:ESP32-H2-WROOM-02C",
      "", "ESP32-H2-WROOM-02C-H4S", "Espressif", 210.82, 129.54, 0,
      {"1": "+3V3", "2": "EN", "14": "NC", "7": "IO8", "8": "BOOT_BTN", "20": "NC",
       "21": "U0RXD", "22": "U0TXD", "23": "USB_DN", "24": "USB_DP", "11": "NC", "12": "NC",
       "28": "LED", "27": "SOIL_ADC", "26": "VBAT_ADC", "25": "NC", "3": "NC", "4": "NC",
       "5": "SENS_PWR_EN_N", "6": "VBAT_MEAS_EN", "10": "NC", "15": "NC",
       "16": "NC", "17": "NC", "18": "NC", "19": "NC", "9": "GND", "13": "GND", "29": "GND"},
      note="Module 4MB flash (H4S) de co OTA Matter. Khong co trong BOM lap rap"),
    C(MC, "C8", "10uF 10V", 50.8, 78.74, 0, "+3V3", "GND", note="Sat chan 3V3 module"),
    C(MC, "C9", "100nF", 66.04, 78.74, 0, "+3V3", "GND"),
    R(MC, "R11", "10k", 50.8, 114.3, 0, "+3V3", "IO8", note="GPIO8 strapping = 1 (cho phep download mode)"),

    # =========================================================== SENSOR CONNECTORS
    # --- capacitive soil moisture module v1.2 / v2.0 (TLC555 + PCB probe), PH2.0-3P: GND, VCC, AOUT
    P(SE, "J4", "Connector", "Conn_01x03_Pin", "SOIL (PH2.0)", PH3, "C131339", "B3B-PH-K-S(LF)(SN)", "JST",
      50.8, 76.2, 0, {"1": "GND", "2": "VSENS", "3": "SOIL_AOUT"},
      note="Module do am dat dien dung v1.2/v2.0 (3.3-5.5V, AOUT 0-3V). Kiem tra thu tu day!"),
    R(SE, "R12", "1k", 121.92, 81.28, 90, "SOIL_AOUT", "SOIL_ADC", note="Han dong ESD/qua ap vao chan ADC"),
    C(SE, "C13", "10nF", 139.7, 93.98, 0, "SOIL_ADC", "GND", note="Loc + nguon cho ADC sample"),
    C(SE, "C14", "1uF", 317.5, 93.98, 0, "VSENS", "GND", note="Dem VSENS (nho de han dong khoi dong, module co tu rieng)"),
    # --- ESD protection of the analog line that leaves the enclosure
    P(SE, "D3", "Device", "D_Zener", "ESD 3.3V", "Diode_SMD:D_SOD-523", "C136161", "LESD5Z3.3T1G", "LRC",
      106.68, 93.98, 90, {"1": "SOIL_AOUT", "2": "GND"}, note="TVS ESD 3.3V (SOD-523) cho day AOUT ra ngoai hop"),

    # ======================================================================== UI
    P(UI, "SW1", "Switch", "SW_Push", "BOOT/USER", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "C318884",
      "TS-1187A-B-A-B", "XKB", 71.12, 81.28, 0, {"1": "BOOT_BTN", "2": "GND"},
      note="IO9: nhan=commissioning/do ngay, 2 lan=hieu chuan kho, 3 lan=uot, giu 10s=factory reset"),
    R(UI, "R21", "10k", 50.8, 63.5, 0, "+3V3", "BOOT_BTN", note="Keo len (strapping IO9 = 1 -> SPI boot)"),
    C(UI, "C21", "100nF", 101.6, 93.98, 0, "BOOT_BTN", "GND", note="Chong doi phim"),
    P(UI, "D2", "Device", "LED", "RED", "LED_SMD:LED_0603_1608Metric", "C2286", "KT-0603R", "Hubei KENTO",
      195.58, 81.28, 180, {"2": "LED_A", "1": "GND"}, note="LED trang thai (chi nhay khi can)"),
    R(UI, "R22", "1k", 172.72, 81.28, 90, "LED", "LED_A", note="~1.5 mA"),
    P(UI, "J1", "Connector_Generic", "Conn_02x04_Odd_Even", "PROG", "h2soil:ProgPads_2x04_P2.54mm_D1.5mm",
      "", "", "", 180.34, 160.02, 0,
      {"1": "+3V3", "2": "GND", "3": "U0TXD", "4": "U0RXD", "5": "EN", "6": "BOOT_BTN", "7": "USB_DN", "8": "USB_DP"},
      note="8 pad tron SMD (pogo 2.54mm / han day): UART0 + USB Serial/JTAG"),
]

# Text blocks per sheet: (x, y, text)
NOTES = {
    "Power": [
        (20.32, 27.94, "1) PIN + CHONG NGUOC CUC\n"
                       "Day cua de pin CR123A han vao 2 pad J3 (+ vuong, - tron).\n"
                       "Q1 P-MOSFET: D->pin(+), S->tai, G->GND qua R1.\n"
                       "Lap nguoc pin: Vgs=0 -> khong co dong. R10 0R: cau do dong."),
        (124.46, 27.94, "2) TPS63900 BUCK-BOOST -> 3.3V (Iq 75nA)\n"
                        "SEL=GND -> VO(1) theo CFG3=16.2k = 3.3V\n"
                        "CFG1=36.5k (VO(2)=3.3V), CFG2=0R: Iin khong gioi han\n"
                        "R CFG 1%/100ppm, khong dat tu tren chan CFG.\n"
                        "L1 2.2uH Isat>=2A; COUT 2x22uF; CIN 10uF."),
        (284.48, 27.94, "3) DO DIEN AP PIN (khong ro khi ngu)\n"
                        "VBAT_MEAS_EN=1 -> Q3 ON -> Q2 ON -> VBAT/2 -> IO2.\n"
                        "Khi ngu: R6 giu Q3 OFF, R5 giu Q2 OFF."),
        (284.48, 144.78, "4) CONG TAC NGUON MODULE DO AM DAT (VSENS)\n"
                         "SENS_PWR_EN_N=0 -> Q4 ON: cap 3.3V cho module.\n"
                         "Firmware bat mem (pull-down noi ~1ms) de han dong nap tu.\n"
                         "R9 giu Q4 OFF khi GPIO Hi-Z (sleep/reset)."),
        (20.32, 205.74, "PWR_FLAG (cho ERC)"),
    ],
    "MCU": [
        (20.32, 27.94, "ESP32-H2-WROOM-02C (4MB: -H4S de co OTA). Vdd 3.0-3.6V.\n"
                       "Module da co RC tren EN (10k/1uF).\n"
                       "Strapping: IO9=1 (R21, sheet UI) -> SPI boot; IO8=1 (R11).\n"
                       "IO10/IO11 la LP GPIO: giu muc khi light-sleep tat mien TOP.\n"
                       "ADC1: IO1=SOIL (module), IO2=VBAT. Chan khac de trong."),
        (20.32, 233.68, "Anten PCB: module o mep tren, vung anten (6mm) nho ra ngoai PCB;\n"
                        "khong dong/GND/linh kien duoi va quanh anten; vo hop cach anten >=15mm."),
    ],
    "Sensors": [
        (20.32, 27.94, "MODULE DO AM DAT DIEN DUNG 'Capacitive Soil Moisture Sensor v1.2'\n"
                       "J4 PH2.0-3P (cung loai cong tren module): 1=GND 2=VCC 3=AOUT.\n"
                       "Nuoi tu VSENS 3.3V, chi bat khi do. Chon module dung TLC555 (NE555 khong chay o 3.3V).\n"
                       "AOUT 0-3V (kho = cao) -> R12 1k -> IO1 (ADC1, ATTEN 12dB); C13 loc; D3 TVS chong ESD."),
    ],
    "UI": [
        (20.32, 27.94, "SW1 (IO9/BOOT): 1 lan = do & bao cao ngay / mo commissioning;\n"
                       "2 lan = hieu chuan KHO; 3 lan = hieu chuan UOT; giu >=10s = factory\n"
                       "reset. Giu SW1 khi cap nguon/reset = che do nap (download)."),
        (124.46, 190.5, "J1: 8 pad tron SMD 2x4 buoc 2.54mm (pogo / han day)\n"
                        "1=3V3 2=GND 3=TXD0 4=RXD0 5=EN 6=IO9 7=USB_D- 8=USB_D+\n"
                        "USB-Serial/JTAG: lap pin + noi D+/D-/GND (khong noi 3V3).\n"
                        "UART: thao pin, cap 3V3 tu adapter USB-UART 3.3V."),
    ],
}
