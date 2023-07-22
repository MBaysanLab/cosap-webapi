from fpdf import FPDF

class ReportCreator:
    
    def __init__(
            self,
            metadata: dict,
            variants:dict
    ):
        pass

    def _create_pdf(self):
        pass



def create_pdf(variants_dict):
    pdf=FPDF()
    pdf.add_page()
    pdf.set_font('Times','B',16)
    pdf.set_fill_color(111,133,193)
    pdf.set_text_color(255,255,255)
    pdf.set_draw_color(111,133,193)
    pdf.set_line_width(0.5)

    pdf.x = 15

    pdf.cell(60,10,'Patient Information',1,0,'C',1)
    pdf.cell(60,10,'Sample Information',1,0,'C',1)
    pdf.cell(60,10,'Applicant',1,1,'C',1)

    pdf.set_fill_color(255,255,255)
    pdf.x = 15
    pdf.cell(60,25,' ',1,0,'C',1)
    pdf.cell(60,25,' ',1,0,'C',1)
    pdf.cell(60,25,' ',1,1,'C',1)

    pdf.x = 15
    pdf.set_fill_color(255,255,255)
    pdf.set_text_color(0,0,0)
    pdf.set_draw_color(0,0,0)
    pdf.text(15,60,'Quality Control')
    pdf.line(15,62,200,62)

    pdf.set_y(65)
    pdf.set_x(15)

    pdf.set_font('Times','B',12)
    pdf.cell(60,10,'Hizalanabilen Okumalar',0,0,'C',1)
    pdf.cell(60,10,'Ortalama Derinlik',0,0,'C',1)
    pdf.cell(60,10,'Q20 Okumalar',0,1,'C',1)

    pdf.set_font('Times','I',24)
    pdf.cell(60,10,'%99.93',0,0,'C',1)
    pdf.cell(60,10,'107X',0,0,'C',1)
    pdf.cell(60,10,'%95.27',0,1,'C',1)

    pdf.set_font('Times','',7)
    pdf.text(20,95,'*Hizalanan okumalar, referans genom uzerinde herhangi bir konuma yerlestirilebilmis okumalarin oranini belirtmektedir.')
    pdf.text(20,97.5,'*Ortalama derinlik, genomun hedeflenen bolgesindeki her bir noktaya ortalama kaç okuma hizalandigini belirtmektedir.')
    pdf.text(20,100,'*Q20 kalite skoru, %1 lik hata oranini temsil etmektedir.')

    y_axis=pdf.get_y()

    pdf.set_font('Times','B',16)
    pdf.text(15,y_axis+25,'Analiz Ozeti')
    pdf.line(15,y_axis+27,200,y_axis+27)

    pdf.set_draw_color(216,216,216)
    pdf.set_y(120)
    pdf.set_x(15)
    pdf.set_font('Times','',20)
    pdf.cell(45,12,'Result:',1,0,'C',1)
    pdf.cell(120,12, str(len(variants_dict)) + ' meaningful variant analyze listed',1,1,'C',1)
    pdf.cell(60,10,'',0,0,'C',1)
    pdf.set_draw_color(0,0,0)


    pdf.set_y(140)
    pdf.set_x(15)
    pdf.set_font('Times','B',12)
    pdf.set_fill_color(216,216,216)
    pdf.set_text_color(0,0,0)
    pdf.set_draw_color(216,216,216)
    pdf.cell(60,10,'Gen',1,0,'C',1)
    pdf.cell(60,10,'Varyant',1,0,'C',1)
    pdf.cell(60,10,'Siniflandirma',1,1,'C',1)


    variants = [
        {
            "Gen": var["gene_symbol"],
            "Varyant": var["location"],
            "Sınıflandırma": var["classification"]
        }
        for var in variants_dict
    ]

    pdf.set_y(150)
    pdf.set_x(15)
    y=1
    for items in variants:
        pdf.set_x(15)
        pdf.cell(60, 10, items['Gen'], 1, 0, 'C', 0)
        pdf.cell(60, 10, items['Varyant'], 1, 0, 'C', 0)
        pdf.cell(60, 10, items['Sınıflandırma'], 1, 1, 'C', 0)
        pdf.set_y(150 + y*10)
        y = y+1

    pdf.set_draw_color(0,0,0)
    pdf.set_font('Times','B',16)
    y_axis=pdf.get_y()
    pdf.text(15,y_axis+12,'Variant Details')
    pdf.line(15,y_axis+14,200,y_axis+14)

    y_axis=pdf.get_y()
    pdf.set_y(y_axis+25)
    pdf.set_x(15)
    y=1
    pdf.set_draw_color(216,216,216)
    pdf.set_font('Times','B',10)

    for items in variants:
        pdf.set_x(15)
        pdf.set_fill_color(216,216,216)
        pdf.cell(40, 10, 'Varyant', 1, 0, 'C', 1)
        pdf.cell(60, 10, items['Varyant'], 1, 0, 'C', 0)
        if items['Sınıflandırma'] == 'Likely Pathogenic':
            pdf.set_fill_color(238,73,73)
        else:
            pdf.set_fill_color(238,155,73)
        pdf.cell(80, 10, items['Sınıflandırma'], 1, 1, 'C', 1)
        pdf.set_x(15)
        pdf.cell(40, 10, 'Gen:'+items['Gen'], 1, 0, 'L', 0)
        pdf.cell(60, 10, 'Alel Frequency: 0.5', 1, 0, 'L', 0)
        pdf.cell(80, 10, 'Variant Type/Effect: frameshift deletion', 1, 1, 'L', 0)
        pdf.set_x(15)
        pdf.cell(180, 10, 'Fenotip:', 1, 1, 'L', 0)
        y_axis=pdf.get_y()
        pdf.set_y(y_axis+5)
        y = y+1

    y_axis=pdf.get_y()
    pdf.set_draw_color(0,0,0)
    pdf.set_font('Times','B',16)
    pdf.text(15,y_axis+5,'Yontemler')
    pdf.line(15,y_axis+7,200,y_axis+7)

    y_axis=pdf.get_y()


    pdf.set_font('Times','',12)
    pdf.text(20,y_axis+15,'* Raw sequencing data provided by ITU National High Performance Computing Center')
    pdf.text(20,y_axis+22,'  is  islenmistir.')
    pdf.text(20,y_axis+29,'* Analizlerde, BWA, Bowtie hizalama ve GATK4, Varscan varyant kesfi algoritmalari kullanilmis')
    pdf.text(20,y_axis+36,'  olup, raporlanan varyantlar tum is akislarinda ortak olarak tespit edilmistir. Bildirilen ')
    pdf.text(20,y_axis+43,'  alel frekansi her iki varyant kesfi algoritmasi tarafindan bildirilen alel frekansinin ')
    pdf.text(20,y_axis+50,'  ortalamasi alinarak hesaplanmistir.')
    pdf.text(20,y_axis+57,'* Okumalar Ensembl Grch38 referans genomuna hizalanmistir.')
    pdf.text(20,y_axis+64,'* Bu raporda yalnizca klinik olarak anlam ifade edebilecek varyantlar raporlanmistir, talep')
    pdf.text(20,y_axis+71,'  edilmesi halinde calismada kesfedilen tum varyantlar kullaniciyla paylasilabilir.')


    pdf.output('Report.pdf')
    return 'Report.pdf'
