"""
PDF Export Modülü - Resmi Kurum Formatlarında Rapor Oluşturma
Yaklaşık Maliyet Pro için Keşif Özeti, Birim Fiyat Analizi ve Poz Listesi PDF çıktıları
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from pathlib import Path
import os


class PDFExporter:
    """Resmi kurum formatlarında PDF rapor oluşturucu"""

    def __init__(self):
        self.setup_fonts()
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()

    def setup_fonts(self):
        """Türkçe karakter desteği için font ayarları"""
        # Windows'ta mevcut Türkçe destekli fontları dene
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/times.ttf",
        ]

        self.font_name = "Helvetica"  # Varsayılan
        self.font_name_bold = "Helvetica-Bold"  # Varsayılan bold

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_name = Path(font_path).stem.capitalize()
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    self.font_name = font_name

                    # Bold font'u kaydetmeye çalış
                    bold_path = font_path.replace(".ttf", "bd.ttf").replace(".TTF", "BD.TTF")
                    if os.path.exists(bold_path):
                        bold_name = font_name + "-Bold"
                        pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                        self.font_name_bold = bold_name
                    else:
                        self.font_name_bold = self.font_name  # Bold yoksa normal font kullan
                    break
                except:
                    continue

    def create_custom_styles(self):
        """Özel stil tanımlamaları"""
        self.styles.add(ParagraphStyle(
            name='TitleCenter',
            fontName=self.font_name,
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=6,
            leading=18
        ))

        self.styles.add(ParagraphStyle(
            name='SubTitle',
            fontName=self.font_name,
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=8,
            textColor=colors.darkblue
        ))

        self.styles.add(ParagraphStyle(
            name='HeaderInfo',
            fontName=self.font_name,
            fontSize=9,
            alignment=TA_LEFT,
            spaceAfter=4
        ))

        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName=self.font_name,
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.white
        ))

        self.styles.add(ParagraphStyle(
            name='TableCell',
            fontName=self.font_name,
            fontSize=8,
            alignment=TA_LEFT
        ))

        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName=self.font_name,
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.gray
        ))

    def format_currency(self, value):
        """Para birimini Türk formatında göster"""
        try:
            return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "0,00"

    def _format_signatory(self, sig_data):
        """İmza sahibi bilgisini formatla"""
        if not sig_data:
            return ""
        # Sadece ad soyad göster (ünvan kaldırıldı)
        return sig_data.get('full_name', '')

    def _create_signature_table(self, signatories=None):
        """İmza tablosu oluştur - 1 Hazırlayan, 3 Kontrol, 1 Onaylayan"""
        elements = []

        if signatories:
            # Hazırlayan ve Kontrol Edenler Satırı (4 sütun)
            hazirlayan = signatories.get('hazirlayan', {})
            kontrol1 = signatories.get('kontrol1', {})
            kontrol2 = signatories.get('kontrol2', {})
            kontrol3 = signatories.get('kontrol3', {})
            onaylayan = signatories.get('onaylayan', {})

            # Özel stil - İmza tablosu için ortalanmış (Türkçe karakter desteği)
            sig_style = ParagraphStyle(
                name='SigCell',
                parent=self.styles['Normal'],
                fontSize=8,
                alignment=TA_CENTER,
                leading=10,
                fontName=self.font_name
            )

            # İsimleri ve Ünvanları Paragraph ile sarmala (Türkçe karakter desteği için)
            hazirlayan_name = Paragraph(hazirlayan.get('full_name', ''), sig_style)
            kontrol1_name = Paragraph(kontrol1.get('full_name', ''), sig_style)
            kontrol2_name = Paragraph(kontrol2.get('full_name', ''), sig_style)
            kontrol3_name = Paragraph(kontrol3.get('full_name', ''), sig_style)

            hazirlayan_title = Paragraph(hazirlayan.get('title', ''), sig_style)
            kontrol1_title = Paragraph(kontrol1.get('title', ''), sig_style)
            kontrol2_title = Paragraph(kontrol2.get('title', ''), sig_style)
            kontrol3_title = Paragraph(kontrol3.get('title', ''), sig_style)

            hazirlayan_date = Paragraph(hazirlayan.get('date_text', ''), sig_style)
            kontrol1_date = Paragraph(kontrol1.get('date_text', ''), sig_style)
            kontrol2_date = Paragraph(kontrol2.get('date_text', ''), sig_style)
            kontrol3_date = Paragraph(kontrol3.get('date_text', ''), sig_style)

            # Üst tablo: Hazırlayan + 3 Kontrol Eden - 5 satır
            top_data = [
                ['HAZIRLAYAN', 'KONTROL EDEN', 'KONTROL EDEN', 'KONTROL EDEN'],  # 1. Header
                [hazirlayan_name, kontrol1_name, kontrol2_name, kontrol3_name],   # 2. Ad Soyad
                [hazirlayan_title, kontrol1_title, kontrol2_title, kontrol3_title], # 3. Ünvan
                ['', '', '', ''],  # 4. İmza alanı (Boşluk)
                [hazirlayan_date, kontrol1_date, kontrol2_date, kontrol3_date]    # 5. Tarih
            ]

            # Satır yükseklikleri (Header, Name, Title, SigSpace, Date)
            row_heights = [None, None, None, 1.2*cm, None]

            top_table = Table(top_data, colWidths=[4.5*cm, 4.5*cm, 4.5*cm, 4.5*cm], rowHeights=row_heights)
            top_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Header stili
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                
                # Çerçeve
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(top_table)
            elements.append(Spacer(1, 0.3*cm))

            # Alt tablo: Onaylayan Amir (tam genişlik) - 5 satır
            onaylayan_name = Paragraph(onaylayan.get('full_name', ''), sig_style)
            onaylayan_title = Paragraph(onaylayan.get('title', ''), sig_style)
            onaylayan_date = Paragraph(onaylayan.get('date_text', ''), sig_style)
            
            bottom_data = [
                ['ONAYLAYAN'],           # 1. Header
                [onaylayan_name],        # 2. Ad Soyad
                [onaylayan_title],       # 3. Ünvan
                [''],                    # 4. İmza alanı
                [onaylayan_date]         # 5. Tarih
            ]
            
            # Alt tablo satır yükseklikleri
            bottom_row_heights = [None, None, None, 1.2*cm, None]

            bottom_table = Table(bottom_data, colWidths=[18*cm], rowHeights=bottom_row_heights)
            bottom_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.15, 0.4, 0.2)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(bottom_table)
        else:
            # Signatories yoksa basit tablo
            signature_data = [
                ['HAZIRLAYAN', 'KONTROL EDEN', 'ONAYLAYAN'],
                ['', '', ''],
                ['', '', ''], # Boşluk
                ['', '', ''], # Tarih yeri
            ]

            sig_table = Table(signature_data, colWidths=[6*cm, 6*cm, 6*cm], rowHeights=[None, 1*cm, 1.5*cm, None])
            sig_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(sig_table)

        return elements

    def export_kesif_ozeti(self, filepath, project_info, items, totals=None, signatories=None):
        """
        Keşif Özeti (Yaklaşık Maliyet) PDF'i oluştur
        Resmi ihale formatına uygun

        signatories: {
            'hazirlayan': {'title': '', 'full_name': '', 'position': ''},
            'kontrol1': {...}, 'kontrol2': {...}, 'kontrol3': {...},
            'onaylayan': {...}
        }
        """
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        elements = []

        # Başlık - Kullanıcı isteği: Keşif özeti yerine İşin Adı
        title_text = project_info.get('name', 'KESİF ÖZETİ')
        if not title_text or title_text == '-':
            title_text = "KESİF ÖZETİ"

        elements.append(Paragraph(title_text, self.styles['TitleCenter']))
        elements.append(Paragraph("(YAKLAŞIK MALİYET HESAP CETVELİ)", self.styles['SubTitle']))
        elements.append(Spacer(1, 0.5*cm))

        # Toplam tablo genişliği (A4: 21cm - 1.5cm sol - 1.5cm sağ = 18cm)
        TOTAL_WIDTH = 18*cm

        # Proje Bilgileri Tablosu
        project_data = [
            ["İŞİN ADI", project_info.get('name', '-')],
            ["İŞVEREN", project_info.get('employer', '-')],
            ["YÜKLENİCİ", project_info.get('contractor', '-')],
            ["YER", project_info.get('location', '-')],
            ["TARİH", project_info.get('date', datetime.now().strftime("%d.%m.%Y"))],
        ]

        info_table = Table(project_data, colWidths=[3.5*cm, 14.5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
            ('FONTNAME', (0, 0), (0, -1), self.font_name),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.7*cm))

        # Keşif Özeti Tablosu
        header = ['S.No', 'Poz No', 'İmalatın Cinsi', 'Birim', 'Miktar', 'Birim Fiyat\n(TL)', 'Tutar\n(TL)']

        table_data = [header]
        for i, item in enumerate(items, 1):
            row = [
                str(i),
                str(item.get('poz_no', '')),
                str(item.get('description', ''))[:50],  # Uzun açıklamaları kısalt
                str(item.get('unit', '')),
                self.format_currency(item.get('quantity', 0)),
                self.format_currency(item.get('unit_price', 0)),
                self.format_currency(item.get('total_price', 0))
            ]
            table_data.append(row)

        # Toplam satırı
        total_amount = totals.get('total', 0) if totals else sum(float(item.get('total_price', 0)) for item in items)
        table_data.append(['', '', '', '', '', 'TOPLAM:', self.format_currency(total_amount)])

        # KDV ve Genel Toplam (opsiyonel)
        if totals and totals.get('kdv'):
            kdv = totals.get('kdv', 0)
            genel_toplam = totals.get('genel_toplam', total_amount * 1.20)
            table_data.append(['', '', '', '', '', 'KDV (%20):', self.format_currency(kdv)])
            table_data.append(['', '', '', '', '', 'GENEL TOPLAM:', self.format_currency(genel_toplam)])

        # Sütun genişlikleri (toplam 18cm)
        col_widths = [1*cm, 2.5*cm, 7*cm, 1.5*cm, 2*cm, 2*cm, 2*cm]
        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        main_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

            # Body
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # S.No
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Poz No
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Açıklama
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Birim
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Sayısal değerler

            # Grid
            ('GRID', (0, 0), (-1, -2 if not totals else -4), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),

            # Toplam satırı
            ('FONTNAME', (5, -1), (-1, -1), self.font_name),
            ('BACKGROUND', (5, -1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
            ('LINEABOVE', (5, -1), (-1, -1), 1, colors.black),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),

            # Alternatif satır renklendirme
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
        ]))

        elements.append(main_table)
        elements.append(Spacer(1, 0.8*cm))

        # İmza Alanları - Dinamik (signatories varsa kullan)
        sig_elements = self._create_signature_table(signatories)
        for elem in sig_elements:
            elements.append(elem)

        # Footer
        elements.append(Spacer(1, 0.5*cm))
        footer_text = f"Bu belge Yaklaşık Maliyet Pro tarafından {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluşturulmuştur."
        elements.append(Paragraph(footer_text, self.styles['Footer']))

        doc.build(elements)
        return True

    def export_birim_fiyat_analizi(self, filepath, analysis_info, components):
        """
        Birim Fiyat Analizi PDF'i oluştur
        Resmi Kurum Formatına Uygun
        """
        from datetime import datetime
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )

        elements = []
        TOTAL_WIDTH = 19*cm

        # Tarih - Sağ üst
        date_style = ParagraphStyle(
            name='DateRight',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            fontName=self.font_name
        )
        elements.append(Paragraph(datetime.now().strftime('%d.%m.%Y'), date_style))
        elements.append(Spacer(1, 0.2*cm))

        # Üst Başlık Tablosu (Poz No | Analizin Adı | Ölçü Birimi)
        poz_no = analysis_info.get('poz_no', '-')
        description = analysis_info.get('description', '-')
        unit = analysis_info.get('unit', '-')

        header_data = [
            ['Poz No', 'Analizin Adı', 'Ölçü Birimi'],
            [poz_no, description, unit]
        ]
        
        header_table = Table(header_data, colWidths=[3*cm, 13*cm, 3*cm])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.1*cm))

        # Detay Tablosu Başlığı
        detail_header = ['Poz No', 'Tanımı', 'Ölçü Birimi', 'Miktarı', 'Birim Fiyatı', 'Tutarı (TL)']
        detail_data = [detail_header]

        # Bileşenleri türlerine göre grupla
        known_types = ['malzeme', 'işçilik', 'iscilik', 'makine', 'nakliye']
        malzeme_items = [c for c in components if c.get('type', '').lower() == 'malzeme']
        iscilik_items = [c for c in components if c.get('type', '').lower() in ['işçilik', 'iscilik']]
        makine_items = [c for c in components if c.get('type', '').lower() == 'makine']
        nakliye_items = [c for c in components if c.get('type', '').lower() == 'nakliye']
        diger_items = [c for c in components if c.get('type', '').lower() not in known_types]
        
        # Malzeme satırları
        malzeme_total = 0
        if malzeme_items:
            detail_data.append(['Malzeme', '', '', '', '', ''])
            for comp in malzeme_items:
                qty = float(comp.get('quantity', 0))
                price = float(comp.get('unit_price', 0))
                total = qty * price
                malzeme_total += total
                detail_data.append([
                    str(comp.get('code', '')),
                    str(comp.get('name', ''))[:45],
                    str(comp.get('unit', '')),
                    f"{qty:.2f}",
                    f"{price:,.2f}",
                    f"{total:,.2f}"
                ])

        # İşçilik satırları
        iscilik_total = 0
        if iscilik_items:
            detail_data.append(['İşçilik', '', '', '', '', ''])
            for comp in iscilik_items:
                qty = float(comp.get('quantity', 0))
                price = float(comp.get('unit_price', 0))
                total = qty * price
                iscilik_total += total
                detail_data.append([
                    str(comp.get('code', '')),
                    str(comp.get('name', ''))[:45],
                    str(comp.get('unit', '')),
                    f"{qty:.2f}",
                    f"{price:,.2f}",
                    f"{total:,.2f}"
                ])

        # Makine satırları
        makine_total = 0
        if makine_items:
            detail_data.append(['Makine', '', '', '', '', ''])
            for comp in makine_items:
                qty = float(comp.get('quantity', 0))
                price = float(comp.get('unit_price', 0))
                total = qty * price
                makine_total += total
                detail_data.append([
                    str(comp.get('code', '')),
                    str(comp.get('name', ''))[:45],
                    str(comp.get('unit', '')),
                    f"{qty:.2f}",
                    f"{price:,.2f}",
                    f"{total:,.2f}"
                ])

        # Nakliye satırları
        nakliye_total = 0
        if nakliye_items:
            detail_data.append(['Nakliye', '', '', '', '', ''])
            for comp in nakliye_items:
                qty = float(comp.get('quantity', 0))
                price = float(comp.get('unit_price', 0))
                total = qty * price
                nakliye_total += total
                detail_data.append([
                    str(comp.get('code', '')),
                    str(comp.get('name', ''))[:45],
                    str(comp.get('unit', '')),
                    f"{qty:.2f}",
                    f"{price:,.2f}",
                    f"{total:,.2f}"
                ])

        # Diğer satırları (tanınmayan türler)
        diger_total = 0
        if diger_items:
            detail_data.append(['Diğer', '', '', '', '', ''])
            for comp in diger_items:
                qty = float(comp.get('quantity', 0))
                price = float(comp.get('unit_price', 0))
                total = qty * price
                diger_total += total
                detail_data.append([
                    str(comp.get('code', '')),
                    str(comp.get('name', ''))[:45],
                    str(comp.get('unit', '')),
                    f"{qty:.2f}",
                    f"{price:,.2f}",
                    f"{total:,.2f}"
                ])

        # Toplamlar
        ara_toplam = malzeme_total + iscilik_total + makine_total + nakliye_total + diger_total
        kar_orani = 0.25
        kar = ara_toplam * kar_orani
        birim_fiyat = ara_toplam + kar

        # Toplam satırları - son 2 sütunu birleştirmek için format değişikliği
        detail_data.append(['', '', '', 'Malzeme + İşçilik Tutarı', '', f"{ara_toplam:,.2f}"])
        detail_data.append(['', '', '', '%25 Yüklenici Kârı', '', f"{kar:,.2f}"])
        detail_data.append(['', '', '', f'1 {unit} Fiyatı', '', f"{birim_fiyat:,.2f}"])

        # Detay tablosu oluştur - sütun genişlikleri ayarlandı
        col_widths = [2*cm, 6.5*cm, 1.8*cm, 4*cm, 2*cm, 2.7*cm]
        detail_table = Table(detail_data, colWidths=col_widths, repeatRows=1)
        
        # Stil uygula
        styles_list = [
            # Header
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Sayısal sütunlar sağa hizalı
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            
            # Box ve grid
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            
            # Son 3 satır (toplamlar) - arka plan ve sütun birleştirme
            ('BACKGROUND', (3, -3), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
            ('FONTNAME', (3, -3), (-1, -1), self.font_name),
            ('SPAN', (3, -3), (4, -3)),  # Malzeme + İşçilik Tutarı
            ('SPAN', (3, -2), (4, -2)),  # %25 Yüklenici Kârı
            ('SPAN', (3, -1), (4, -1)),  # 1 m² Fiyatı
        ]

        # Grup başlıkları için stil ekle (Malzeme, İşçilik, vb.)
        row_idx = 1
        for i, row in enumerate(detail_data[1:], 1):
            if row[0] in ['Malzeme', 'İşçilik', 'Makine', 'Nakliye', 'Diğer']:
                styles_list.append(('FONTNAME', (0, i), (0, i), self.font_name))
                styles_list.append(('TEXTCOLOR', (0, i), (0, i), colors.red))
                styles_list.append(('SPAN', (0, i), (1, i)))

        detail_table.setStyle(TableStyle(styles_list))
        elements.append(detail_table)
        elements.append(Spacer(1, 0.5*cm))

        # Açıklama Metni (Footer)
        footer_style = ParagraphStyle(
            name='AnalysisFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName=self.font_name,
            leading=10
        )
        
        explanation_text = f"""Her boyutta {description.lower()} mevcut kalıbın üzerine projesine uygun olarak döşenmesi için, 
inşaat yerindeki yükleme, yatay ve düşey taşıma, boşaltma, her türlü malzeme ve zayiatı, işçilik, araç ve gereç giderleri, yüklenici genel giderleri ve kârı 
dâhil, 1 {unit} fiyatı:

Ölçü: Projesindeki boyutlar üzerinden hesaplanır."""

        elements.append(Paragraph(explanation_text, footer_style))

        doc.build(elements)
        return True

    def export_poz_listesi(self, filepath, title, poz_items):
        """
        Poz Listesi PDF'i oluştur
        """
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        elements = []

        # Başlık
        elements.append(Paragraph(title or "POZ LİSTESİ", self.styles['TitleCenter']))
        elements.append(Paragraph(f"Tarih: {datetime.now().strftime('%d.%m.%Y')}", self.styles['SubTitle']))
        elements.append(Spacer(1, 0.5*cm))

        # Tablo
        header = ['S.No', 'Poz No', 'Açıklama', 'Birim', 'Birim Fiyat (TL)']
        table_data = [header]

        for i, poz in enumerate(poz_items, 1):
            row = [
                str(i),
                str(poz.get('poz_no', poz.get('code', ''))),
                str(poz.get('description', poz.get('name', '')))[:60],
                str(poz.get('unit', '')),
                self.format_currency(poz.get('unit_price', poz.get('price', 0)))
            ]
            table_data.append(row)

        col_widths = [1*cm, 3*cm, 10*cm, 1.5*cm, 2.5*cm]
        poz_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        poz_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.3)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Body
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),

            # Alternatif satır renklendirme
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.97, 0.95)]),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(poz_table)
        elements.append(Spacer(1, 0.5*cm))

        # Özet
        elements.append(Paragraph(f"Toplam {len(poz_items)} adet poz listelenmiştir.", self.styles['HeaderInfo']))

        # Footer
        elements.append(Spacer(1, 0.5*cm))
        footer_text = f"Bu liste Yaklaşık Maliyet Pro tarafından {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluşturulmuştur."
        elements.append(Paragraph(footer_text, self.styles['Footer']))

        doc.build(elements)
        return True

    def export_metraj_listesi(self, filepath, project_info, groups_with_items, signatories=None):
        """
        Metraj Listesi (İmalat Grupları ve Detayları) PDF'i oluştur
        Maliyet Hesabı sekmesindeki PDF formatıyla aynı stil kullanır
        """
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        elements = []

        # Başlık - Yaklaşık maliyet formatı
        title_text = project_info.get('name', 'METRAJ LİSTESİ')
        if not title_text or title_text == '-':
            title_text = "METRAJ LİSTESİ"

        elements.append(Paragraph(title_text, self.styles['TitleCenter']))
        elements.append(Paragraph("(METRAJ LİSTESİ)", self.styles['SubTitle']))
        elements.append(Spacer(1, 0.5*cm))

        # Proje Bilgileri Tablosu - Yaklaşık maliyet formatı
        project_data = [
            ["İŞİN ADI", project_info.get('name', '-')],
            ["İŞVEREN", project_info.get('employer', project_info.get('institution', '-'))],
            ["YÜKLENİCİ", project_info.get('contractor', '-')],
            ["YER", project_info.get('location', '-')],
            ["TARİH", project_info.get('date', datetime.now().strftime("%d.%m.%Y"))],
        ]

        info_table = Table(project_data, colWidths=[3.5*cm, 14.5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.7*cm))

        for group in groups_with_items:
            # Grup başlığı
            group_title = f"📁 {group.get('name', 'Grup')} ({group.get('unit', '')})"
            elements.append(Paragraph(group_title, self.styles['SubTitle']))
            elements.append(Spacer(1, 0.2*cm))

            items = group.get('items', [])
            if not items:
                elements.append(Paragraph("Bu grupta kayıt yok.", self.styles['HeaderInfo']))
                elements.append(Spacer(1, 0.3*cm))
                continue

            # Metraj tablosu
            header = ['S.No', 'Tanım', 'Adet', 'Boy', 'En', 'Yük.', 'Miktar', 'Birim', 'Notlar']
            table_data = [header]

            for i, item in enumerate(items, 1):
                row = [
                    str(i),
                    str(item.get('description', ''))[:30],
                    str(item.get('similar_count', 1)),
                    f"{item.get('length', 0):.2f}",
                    f"{item.get('width', 0):.2f}",
                    f"{item.get('height', 0):.2f}",
                    f"{item.get('quantity', 0):.3f}",
                    str(item.get('unit', '')),
                    str(item.get('notes', ''))[:20]
                ]
                table_data.append(row)

            col_widths = [0.8*cm, 4*cm, 1*cm, 1.3*cm, 1.3*cm, 1.3*cm, 1.8*cm, 1.2*cm, 4*cm]
            metraj_table = Table(table_data, colWidths=col_widths, repeatRows=1)

            metraj_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.3, 0.3, 0.5)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (2, 1), (6, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))

            elements.append(metraj_table)
            elements.append(Spacer(1, 0.5*cm))

        elements.append(Spacer(1, 0.8*cm))

        # İmza Alanları - Yaklaşık maliyet formatı ile aynı
        sig_elements = self._create_signature_table(signatories)
        for elem in sig_elements:
            elements.append(elem)

        # Footer
        elements.append(Spacer(1, 0.5*cm))
        footer_text = f"Bu belge Yaklaşık Maliyet Pro tarafından {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluşturulmuştur."
        elements.append(Paragraph(footer_text, self.styles['Footer']))

        doc.build(elements)
        return True

    def export_imalat_metraj_cetveli(self, filepath: str, project_info: dict,
                                      imalat_group: dict, signatories=None) -> bool:
        """
        Tek bir imalat grubu için kamu formatında metraj cetveli oluşturur.
        Yaklaşık maliyet PDF formatıyla aynı stil kullanır.

        Args:
            filepath: PDF dosya yolu
            project_info: Proje bilgileri
            imalat_group: İmalat grubu bilgileri (name, unit, items, total_quantity, ai_explanation)
            signatories: İmzalayan dict (hazirlayan, kontrol1, kontrol2, kontrol3, onaylayan)
        """
        try:
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=1.5*cm,
                bottomMargin=1.5*cm
            )

            elements = []

            # Başlık - İşin adı (proje adı)
            title_text = project_info.get('name', 'İMALAT METRAJ CETVELİ')
            if not title_text or title_text == '-':
                title_text = "İMALAT METRAJ CETVELİ"
            
            elements.append(Paragraph(title_text, self.styles['TitleCenter']))
            elements.append(Paragraph("(İMALAT METRAJ CETVELİ)", self.styles['SubTitle']))
            elements.append(Spacer(1, 0.5*cm))

            # Proje Bilgileri Tablosu - Yaklaşık maliyet formatı
            project_data = [
                ["İŞİN ADI", project_info.get('name', '-')],
                ["İŞVEREN", project_info.get('employer', project_info.get('institution', '-'))],
                ["YÜKLENİCİ", project_info.get('contractor', '-')],
                ["YER", project_info.get('location', '-')],
                ["BİRİM", imalat_group.get('unit', '-')],
                ["TARİH", project_info.get('date', datetime.now().strftime("%d.%m.%Y"))],
            ]

            info_table = Table(project_data, colWidths=[3.5*cm, 14.5*cm])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.7*cm))

            # Metraj Tablosu
            items = imalat_group.get('items', [])
            imalat_unit = imalat_group.get('unit', '')

            if items:
                header = ['S.No', 'Tanım', 'Adet', 'Boy', 'En', 'Yük.', 'Miktar', 'Birim']
                table_data = [header]

                for i, item in enumerate(items, 1):
                    miktar = item.get('quantity', 0)
                    row = [
                        str(i),
                        str(item.get('description', ''))[:40],
                        str(item.get('similar_count', 1)),
                        f"{item.get('length', 0):.2f}",
                        f"{item.get('width', 0):.2f}",
                        f"{item.get('height', 0):.2f}",
                        f"{miktar:.3f}",
                        str(item.get('unit', imalat_unit))
                    ]
                    table_data.append(row)

                # Sütun genişlikleri (toplam 18cm) - Poz sütunu kaldırıldı
                col_widths = [1*cm, 7.5*cm, 1.2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm, 1.8*cm]
                metraj_table = Table(table_data, colWidths=col_widths, repeatRows=1)

                metraj_table.setStyle(TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), self.font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                    # Body
                    ('FONTNAME', (0, 1), (-1, -1), self.font_name),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 1), (0, -1), 'CENTER'),   # S.No
                    ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Tanım
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),   # Sayısal değerler

                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),

                    # Padding
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),

                    # Alternatif satır renklendirme
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
                ]))

                elements.append(metraj_table)
            else:
                elements.append(Paragraph("Bu imalat için metraj kaydı bulunmamaktadır.", self.styles['HeaderInfo']))

            elements.append(Spacer(1, 0.8*cm))

            # AI açıklaması varsa ekle
            ai_explanation = imalat_group.get('ai_explanation', '')
            if ai_explanation:
                elements.append(Paragraph("<b>Açıklama:</b>", self.styles['HeaderInfo']))
                elements.append(Paragraph(ai_explanation, self.styles['Normal']))
                elements.append(Spacer(1, 0.5*cm))

            # İmza Alanları - Yaklaşık maliyet formatı ile aynı
            sig_elements = self._create_signature_table(signatories)
            for elem in sig_elements:
                elements.append(elem)

            # Footer
            elements.append(Spacer(1, 0.5*cm))
            footer_text = f"Bu belge Yaklaşık Maliyet Pro tarafından {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluşturulmuştur."
            elements.append(Paragraph(footer_text, self.styles['Footer']))

            doc.build(elements)
            return True

        except Exception as e:
            print(f"PDF oluşturma hatası: {e}")
            return False

    def export_tum_imalat_metrajlari(self, filepath: str, project_info: dict,
                                      imalat_groups: list, signatories=None) -> bool:
        """
        Tüm imalat grupları için tek bir PDF'te metraj cetvelleri oluşturur.
        Her imalat grubu ayrı sayfada gösterilir.
        Yaklaşık maliyet PDF formatıyla aynı stil kullanır.

        Args:
            filepath: PDF dosya yolu
            project_info: Proje bilgileri
            imalat_groups: İmalat grupları listesi
            signatories: İmzalayan dict (hazirlayan, kontrol1, kontrol2, kontrol3, onaylayan)
        """
        try:
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=1.5*cm,
                bottomMargin=1.5*cm
            )

            elements = []

            # İlk sayfa için başlık - İşin adı (proje adı)
            title_text = project_info.get('name', 'İMALAT METRAJ CETVELİ')
            if not title_text or title_text == '-':
                title_text = "İMALAT METRAJ CETVELİ"
            
            elements.append(Paragraph(title_text, self.styles['TitleCenter']))
            elements.append(Paragraph("(TÜM İMALAT METRAJ CETVELLERİ)", self.styles['SubTitle']))
            elements.append(Spacer(1, 0.5*cm))

            for idx, imalat_group in enumerate(imalat_groups):
                if idx > 0:
                    elements.append(PageBreak())
                    # Her sayfada başlık tekrar göster
                    elements.append(Paragraph(title_text, self.styles['TitleCenter']))
                    elements.append(Paragraph(f"(İMALAT METRAJ CETVELİ - Sayfa {idx + 1}/{len(imalat_groups)})", self.styles['SubTitle']))
                    elements.append(Spacer(1, 0.5*cm))

                # Proje Bilgileri Tablosu - Yaklaşık maliyet formatı (her sayfada)
                imalat_unit = imalat_group.get('unit', '')
                project_data = [
                    ["İŞİN ADI", project_info.get('name', '-')],
                    ["İŞVEREN", project_info.get('employer', project_info.get('institution', '-'))],
                    ["YÜKLENİCİ", project_info.get('contractor', '-')],
                    ["YER", project_info.get('location', '-')],
                    ["BİRİM", imalat_unit],
                    ["TARİH", project_info.get('date', datetime.now().strftime("%d.%m.%Y"))],
                ]

                info_table = Table(project_data, colWidths=[3.5*cm, 14.5*cm])
                info_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), self.font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(info_table)
                elements.append(Spacer(1, 0.7*cm))

                # İmalat grubu başlığı ekle
                imalat_group_name = imalat_group.get('name', 'İmalat Grubu')
                group_title_style = ParagraphStyle(
                    name='GroupTitle',
                    parent=self.styles['Normal'],
                    fontSize=11,
                    alignment=TA_LEFT,
                    fontName=self.font_name,
                    textColor=colors.darkblue,
                    spaceAfter=6
                )
                elements.append(Paragraph(f"<b>İmalat Grubu: {imalat_group_name}</b>", group_title_style))
                elements.append(Spacer(1, 0.3*cm))

                # Metraj Tablosu
                items = imalat_group.get('items', [])

                if items:
                    header = ['S.No', 'Tanım', 'Adet', 'Boy', 'En', 'Yük.', 'Miktar', 'Birim']
                    table_data = [header]

                    for i, item in enumerate(items, 1):
                        miktar = item.get('quantity', 0)
                        row = [
                            str(i),
                            str(item.get('description', ''))[:40],
                            str(item.get('similar_count', 1)),
                            f"{item.get('length', 0):.2f}",
                            f"{item.get('width', 0):.2f}",
                            f"{item.get('height', 0):.2f}",
                            f"{miktar:.3f}",
                            str(item.get('unit', imalat_unit))
                        ]
                        table_data.append(row)

                    # Sütun genişlikleri (toplam 18cm) - Poz sütunu kaldırıldı
                    col_widths = [1*cm, 7.5*cm, 1.2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm, 1.8*cm]
                    metraj_table = Table(table_data, colWidths=col_widths, repeatRows=1)

                    metraj_table.setStyle(TableStyle([
                        # Header
                        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), self.font_name),
                        ('FONTSIZE', (0, 0), (-1, 0), 8),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

                        # Body
                        ('FONTNAME', (0, 1), (-1, -1), self.font_name),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('ALIGN', (0, 1), (0, -1), 'CENTER'),   # S.No
                        ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Tanım
                        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),   # Sayısal değerler

                        # Grid
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('BOX', (0, 0), (-1, -1), 1, colors.black),

                        # Padding
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),

                        # Alternatif satır renklendirme
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
                    ]))

                    elements.append(metraj_table)
                else:
                    elements.append(Paragraph("Bu imalat için metraj kaydı bulunmamaktadır.", self.styles['HeaderInfo']))

                elements.append(Spacer(1, 0.8*cm))

                # AI açıklaması varsa ekle
                ai_explanation = imalat_group.get('ai_explanation', '')
                if ai_explanation:
                    elements.append(Paragraph("<b>Açıklama:</b>", self.styles['HeaderInfo']))
                    elements.append(Paragraph(ai_explanation, self.styles['Normal']))
                    elements.append(Spacer(1, 0.5*cm))

                # İmza Alanları - Yaklaşık maliyet formatı ile aynı
                sig_elements = self._create_signature_table(signatories)
                for elem in sig_elements:
                    elements.append(elem)

            # Footer
            elements.append(Spacer(1, 0.5*cm))
            footer_text = f"Bu belge Yaklaşık Maliyet Pro tarafından {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluşturulmuştur."
            elements.append(Paragraph(footer_text, self.styles['Footer']))

            doc.build(elements)
            return True

        except Exception as e:
            print(f"PDF oluşturma hatası: {e}")
            return False
